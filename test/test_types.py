"""Tests Gedcom types."""

import pytest

import gedcom7.types as T


def test_integer():
    with pytest.raises(ValueError):
        T.Integer("a")
    with pytest.raises(ValueError):
        T.Integer(" 1")
    assert T.Integer("203").parse() == 203


def test_as_type():
    struct = T.GedcomStructure("_SOMETAG", "", "15", "")
    assert struct.as_type("Integer") == 15


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
