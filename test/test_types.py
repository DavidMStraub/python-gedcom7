"""Tests Gedcom types."""

import pytest

import gedcom7.types as T


def test_integer():
    with pytest.raises(ValueError):
        T.Integer("a")
    with pytest.raises(ValueError):
        T.Integer(" 1")
    assert T.Integer("203").parse() == 203


def test_personalname():
    assert T.PersonalName("John Doe").parse() == {
        "fullname": "John Doe",
        "surname": None,
    }
    assert T.PersonalName("John /Doe/").parse() == {
        "fullname": "John Doe",
        "surname": "Doe",
    }


def test_time():
    with pytest.raises(ValueError):
        T.Time("13.15")
    with pytest.raises(ValueError):
        T.Time("13:15.2")
    with pytest.raises(ValueError):
        T.Time("13:15A")
    with pytest.raises(ValueError):
        T.Time("25:01")
    with pytest.raises(ValueError):
        T.Time("23:01:71")
    with pytest.raises(ValueError):
        T.Time("23:61")
    assert T.Time("13:15").parse() == {
        "hour": 13,
        "minute": 15,
        "second": None,
        "fraction": None,
        "tz": None,
    }
    assert T.Time("13:15:12").parse() == {
        "hour": 13,
        "minute": 15,
        "second": 12,
        "fraction": None,
        "tz": None,
    }
    assert T.Time("13:15:12.246").parse() == {
        "hour": 13,
        "minute": 15,
        "second": 12,
        "fraction": 246,
        "tz": None,
    }
    assert T.Time("13:15Z").parse() == {
        "hour": 13,
        "minute": 15,
        "second": None,
        "fraction": None,
        "tz": "Z",
    }


def test_age():
    with pytest.raises(ValueError):
        T.Age("3Y")
    assert T.Age("3y").parse() == {"years": 3}
    assert T.Age("> 3y").parse() == {"years": 3, "agebound": ">"}
    assert T.Age("3y 6m 5d").parse() == {"years": 3, "months": 6, "days": 5}


def test_enum():
    with pytest.raises(ValueError):
        T.Enum("Foo")
    assert T.Enum("FOO").parse() == "FOO"


def test_list_enum():
    with pytest.raises(ValueError):
        T.ListEnum("Foo")
    assert T.ListEnum("FOO").parse() == ["FOO"]
    assert T.ListEnum("FOO, BAR").parse() == ["FOO", "BAR"]


def test_list_text():
    assert T.ListText("foo").parse() == ["foo"]
    assert T.ListText("foo,bar").parse() == ["foo", "bar"]


def test_media_type():
    with pytest.raises(ValueError):
        T.MediaType("image")
    assert T.MediaType("image/jpeg").parse() == "image/jpeg"


def test_dateexact():
    with pytest.raises(ValueError):
        T.DateExact("2022-10-11")
    with pytest.raises(ValueError):
        T.DateExact("11 10 2022")
    assert T.DateExact("11 JAN 2022").parse() == {
        "year": 2022,
        "month": "JAN",
        "day": 11,
    }


def test_date():
    assert T.Date("JULIAN 11 JAN 2022 BCE").parse() == {
        "calendar": "JULIAN",
        "day": 11,
        "month": "JAN",
        "year": 2022,
        "epoch": "BCE",
    }
    assert T.DateValue("JULIAN 11 JAN 2022 BCE").parse() == {
        "calendar": "JULIAN",
        "day": 11,
        "month": "JAN",
        "year": 2022,
        "epoch": "BCE",
    }
    assert T.DateValue("11 JAN 2022").parse() == {
        "calendar": None,
        "day": 11,
        "month": "JAN",
        "year": 2022,
        "epoch": None,
    }
    assert T.DateValue("JAN 2022").parse() == {
        "calendar": None,
        "day": None,
        "month": "JAN",
        "year": 2022,
        "epoch": None,
    }
    assert T.DateValue("2022").parse() == {
        "calendar": None,
        "day": None,
        "month": None,
        "year": 2022,
        "epoch": None,
    }


def test_dateperiod():
    with pytest.raises(ValueError):
        T.DatePeriod("11 JAN 2022")
    assert T.DatePeriod("FROM JULIAN 5 MAY 1755 BCE").parse() == {
        "from": {
            "calendar": "JULIAN",
            "year": 1755,
            "month": "MAY",
            "day": 5,
            "epoch": "BCE",
        },
    }
    assert T.DatePeriod("TO 11 JAN 2022").parse() == {
        "to": {
            "calendar": None,
            "year": 2022,
            "month": "JAN",
            "day": 11,
            "epoch": None,
        },
    }
    assert T.DatePeriod("FROM 2021 TO 2022").parse() == {
        "from": {
            "calendar": None,
            "year": 2021,
            "month": None,
            "day": None,
            "epoch": None,
        },
        "to": {
            "calendar": None,
            "year": 2022,
            "month": None,
            "day": None,
            "epoch": None,
        },
    }
    assert T.DatePeriod("FROM 1 JAN 2021 TO 11 JAN 2022").parse() == {
        "from": {
            "calendar": None,
            "year": 2021,
            "month": "JAN",
            "day": 1,
            "epoch": None,
        },
        "to": {
            "calendar": None,
            "year": 2022,
            "month": "JAN",
            "day": 11,
            "epoch": None,
        },
    }
    assert T.DateValue("FROM 1 JAN 2021 TO 11 JAN 2022").parse() == {
        "from": {
            "calendar": None,
            "year": 2021,
            "month": "JAN",
            "day": 1,
            "epoch": None,
        },
        "to": {
            "calendar": None,
            "year": 2022,
            "month": "JAN",
            "day": 11,
            "epoch": None,
        },
    }


def test_date_approx():
    assert T.DateApprox("ABT 5 MAY 1755 BCE").parse() == {
        "qualifier": "ABT",
        "date": {
            "calendar": None,
            "year": 1755,
            "month": "MAY",
            "day": 5,
            "epoch": "BCE",
        },
    }
    assert T.DateValue("ABT 5 MAY 1755 BCE").parse() == {
        "qualifier": "ABT",
        "date": {
            "calendar": None,
            "year": 1755,
            "month": "MAY",
            "day": 5,
            "epoch": "BCE",
        },
    }


def test_date_range_bet():
    assert T.DateRange("BET 1 JAN 2021 AND 2 FEB 2022").parse() == {
        "between": {
            "calendar": None,
            "year": 2021,
            "month": "JAN",
            "day": 1,
            "epoch": None,
        },
        "and": {
            "calendar": None,
            "year": 2022,
            "month": "FEB",
            "day": 2,
            "epoch": None,
        },
    }
    assert T.DateValue("BET 1 JAN 2021 AND 2 FEB 2022").parse() == {
        "between": {
            "calendar": None,
            "year": 2021,
            "month": "JAN",
            "day": 1,
            "epoch": None,
        },
        "and": {
            "calendar": None,
            "year": 2022,
            "month": "FEB",
            "day": 2,
            "epoch": None,
        },
    }


def test_date_range_bef():
    assert T.DateRange("BEF 1 JAN 2021").parse() == {
        "before": {
            "calendar": None,
            "year": 2021,
            "month": "JAN",
            "day": 1,
            "epoch": None,
        }
    }
    assert T.DateValue("BEF 1 JAN 2021").parse() == {
        "before": {
            "calendar": None,
            "year": 2021,
            "month": "JAN",
            "day": 1,
            "epoch": None,
        }
    }


def test_date_range_aft():
    assert T.DateRange("AFT 1 JAN 2021").parse() == {
        "after": {
            "calendar": None,
            "year": 2021,
            "month": "JAN",
            "day": 1,
            "epoch": None,
        },
    }
    assert T.DateValue("AFT 1 JAN 2021").parse() == {
        "after": {
            "calendar": None,
            "year": 2021,
            "month": "JAN",
            "day": 1,
            "epoch": None,
        },
    }


def test_boolean():
    with pytest.raises(ValueError):
        T.Integer("N")
    with pytest.raises(ValueError):
        T.Integer("y")
    with pytest.raises(ValueError):
        T.Integer("")
    assert T.Boolean("Y").parse() == True