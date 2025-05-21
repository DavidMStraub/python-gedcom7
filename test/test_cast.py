import pytest
from gedcom7 import cast, types


def test_cast_bool():
    assert cast._cast_bool("Y") is True
    assert cast._cast_bool("") is False


def test_cast_integer():
    assert cast._cast_integer("1") == 1
    assert cast._cast_integer("0") == 0
    assert cast._cast_integer("-1") == -1
    assert cast._cast_integer("12345678901234567890") == 12345678901234567890
    with pytest.raises(ValueError):
        cast._cast_integer("abc")
    with pytest.raises(ValueError):
        cast._cast_integer("")


def test_cast_list_text():
    assert cast._cast_list_text("foo") == ["foo"]
    assert cast._cast_list_text("foo,bar") == ["foo", "bar"]
    assert cast._cast_list_text("foo, bar") == ["foo", "bar"]
    assert cast._cast_list_text(" foo , bar ") == ["foo", "bar"]
    assert cast._cast_list_text("") == [""]
    assert cast._cast_list_text(",") == ["", ""]
    assert cast._cast_list_text(", foo") == ["", "foo"]
    assert cast._cast_list_text("foo, ") == ["foo", ""]


def test_cast_personal_name():
    assert cast._cast_personal_name("John Doe") == types.PersonalName(
        fullname="John Doe",
        surname=None,
    )
    assert cast._cast_personal_name("John /Doe/") == types.PersonalName(
        fullname="John Doe",
        surname="Doe",
    )
    assert cast._cast_personal_name("John /Doe/ Smith") == types.PersonalName(
        fullname="John Doe Smith",
        surname="Doe",
    )
    with pytest.raises(ValueError):
        cast._cast_personal_name("John /Doe/ Smith /Smith/")
    assert cast._cast_personal_name("José O'Malley") == types.PersonalName(
        fullname="José O'Malley",
        surname=None,
    )
    assert cast._cast_personal_name("José /O'Malley/") == types.PersonalName(
        fullname="José O'Malley",
        surname="O'Malley",
    )
    assert cast._cast_personal_name("María-José /García-López/") == types.PersonalName(
        fullname="María-José García-López",
        surname="García-López",
    )
    assert cast._cast_personal_name("Søren /Ødegård/") == types.PersonalName(
        fullname="Søren Ødegård",
        surname="Ødegård",
    )


def test_cast_time():
    assert cast._cast_time("13:15") == types.Time(
        hour=13,
        minute=15,
        second=None,
        fraction=None,
        tz=None,
    )
    assert cast._cast_time("13:15:12") == types.Time(
        hour=13,
        minute=15,
        second=12,
        fraction=None,
        tz=None,
    )
    assert cast._cast_time("13:15:12.246") == types.Time(
        hour=13,
        minute=15,
        second=12,
        fraction=246,
        tz=None,
    )
    assert cast._cast_time("13:15Z") == types.Time(
        hour=13,
        minute=15,
        second=None,
        fraction=None,
        tz="Z",
    )
    assert cast._cast_time("13:15:12.246Z") == types.Time(
        hour=13,
        minute=15,
        second=12,
        fraction=246,
        tz="Z",
    )
    with pytest.raises(ValueError):
        cast._cast_time("13:15A")  # Invalid timezone, should be Z

    def test_cast_age():
        # Testing basic combinations
        assert cast._cast_age("3y") == types.Age(
            years=3,
            months=None,
            weeks=None,
            days=None,
            agebound=None,
        )
        assert cast._cast_age("> 3y") == types.Age(
            years=3,
            months=None,
            weeks=None,
            days=None,
            agebound=">",
        )
        assert cast._cast_age("3y 6m 5d") == types.Age(
            years=3,
            months=6,
            weeks=None,
            days=5,
            agebound=None,
        )
        assert cast._cast_age("3y 6m") == types.Age(
            years=3,
            months=6,
            weeks=None,
            days=None,
            agebound=None,
        )
        assert cast._cast_age("3y 6m 5d 2w") == types.Age(
            years=3,
            months=6,
            weeks=2,
            days=5,
            agebound=None,
        )

        # Testing various partial combinations
        assert cast._cast_age("6m 2w") == types.Age(
            years=None,
            months=6,
            weeks=2,
            days=None,
            agebound=None,
        )
        assert cast._cast_age("6m 5d") == types.Age(
            years=None,
            months=6,
            weeks=None,
            days=5,
            agebound=None,
        )
        assert cast._cast_age("2w 5d") == types.Age(
            years=None,
            months=None,
            weeks=2,
            days=5,
            agebound=None,
        )
        assert cast._cast_age("5d") == types.Age(
            years=None,
            months=None,
            weeks=None,
            days=5,
            agebound=None,
        )

        # Testing with age bounds
        assert cast._cast_age("< 6m") == types.Age(
            years=None,
            months=6,
            weeks=None,
            days=None,
            agebound="<",
        )
        assert cast._cast_age("> 2w") == types.Age(
            years=None,
            months=None,
            weeks=2,
            days=None,
            agebound=">",
        )
        assert cast._cast_age("< 5d") == types.Age(
            years=None,
            months=None,
            weeks=None,
            days=5,
            agebound="<",
        )
        assert cast._cast_age("> 1y 6m") == types.Age(
            years=1,
            months=6,
            weeks=None,
            days=None,
            agebound=">",
        )
        assert cast._cast_age("< 2y 3m 1w") == types.Age(
            years=2,
            months=3,
            weeks=1,
            days=None,
            agebound="<",
        )

        # Test with zero values
        assert cast._cast_age("0y 0m 0w 0d") == types.Age(
            years=0,
            months=0,
            weeks=0,
            days=0,
            agebound=None,
        )

        # Test with invalid formats
        with pytest.raises(ValueError):
            cast._cast_age("invalid")
        with pytest.raises(ValueError):
            cast._cast_age("10")  # Missing unit


def test_cast_enum():
    assert cast._cast_enum("FOO") == "FOO"
    assert cast._cast_enum("BAR") == "BAR"
    with pytest.raises(ValueError):
        cast._cast_enum("Foo")
    with pytest.raises(ValueError):
        cast._cast_enum("")


def test_cast_list_enum():
    assert cast._cast_list_enum("FOO") == ["FOO"]
    assert cast._cast_list_enum("FOO, BAR") == ["FOO", "BAR"]
    assert cast._cast_list_enum("FOO, BAR, BAZ") == ["FOO", "BAR", "BAZ"]
    with pytest.raises(ValueError):
        cast._cast_list_enum("Foo")
    with pytest.raises(ValueError):
        cast._cast_list_enum("")


def test_cast_mediatype():
    assert cast._cast_mediatype("image/jpeg") == types.MediaType(
        media_type="image/jpeg"
    )
    assert cast._cast_mediatype("application/json") == types.MediaType(
        media_type="application/json"
    )
    with pytest.raises(ValueError):
        cast._cast_mediatype("image")
    with pytest.raises(ValueError):
        cast._cast_mediatype("")


def test_cast_date_exact():
    assert cast._cast_date_exact("11 JAN 2022") == types.DateExact(
        day=11,
        month="JAN",
        year=2022,
    )
    with pytest.raises(ValueError):
        cast._cast_date_exact("2022-10-11")
    with pytest.raises(ValueError):
        cast._cast_date_exact("11 10 2022 BCE")
    with pytest.raises(ValueError):
        cast._cast_date_exact("11 10 2022 CE")


def test_cast_date():
    assert cast._cast_date("JULIAN 11 JAN 2022 BCE") == types.Date(
        calendar="JULIAN",
        day=11,
        month="JAN",
        year=2022,
        epoch="BCE",
    )
    assert cast._cast_date("11 JAN 2022") == types.Date(
        calendar=None,
        day=11,
        month="JAN",
        year=2022,
        epoch=None,
    )
    with pytest.raises(ValueError):
        cast._cast_date("2022-10-11")
    with pytest.raises(ValueError):
        cast._cast_date("11 10 2022 BCE")
    with pytest.raises(ValueError):
        cast._cast_date("11 10 2022 CE")


def test_cast_date_period():
    assert cast._cast_date_period("FROM JULIAN 5 MAY 1755 BCE") == types.DatePeriod(
        from_=types.Date(
            calendar="JULIAN",
            day=5,
            month="MAY",
            year=1755,
            epoch="BCE",
        ),
        to=None,
    )
    assert cast._cast_date_period("TO 11 JAN 2022") == types.DatePeriod(
        from_=None,
        to=types.Date(
            calendar=None,
            day=11,
            month="JAN",
            year=2022,
            epoch=None,
        ),
    )
    assert cast._cast_date_period("FROM 1 JAN 2021 TO 11 JAN 2022") == types.DatePeriod(
        from_=types.Date(
            calendar=None,
            day=1,
            month="JAN",
            year=2021,
            epoch=None,
        ),
        to=types.Date(
            calendar=None,
            day=11,
            month="JAN",
            year=2022,
            epoch=None,
        ),
    )
    with pytest.raises(ValueError):
        cast._cast_date_period("11 JAN 2022")
