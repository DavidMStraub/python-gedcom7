"""Tests for formatting data type values back to payload strings."""

import pathlib

import pytest

import gedcom7
from gedcom7 import GedcomSerializeError, const, formatter, types

V7 = "https://gedcom.io/terms/v7/"
LATI = "https://gedcom.io/terms/v7/LATI"
TIME = "https://gedcom.io/terms/v7/TIME"
ABBR = "https://gedcom.io/terms/v7/ABBR"
ADOP = "https://gedcom.io/terms/v7/ADOP"
BAPL = "https://gedcom.io/terms/v7/BAPL"


# --------------------------------------------------------------------------
# Coordinates: the payload has no exponent notation and no sign
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("degrees", "expected"),
    [
        (18.150944, "N18.150944"),
        (-18.150944, "S18.150944"),
        # str() would render these as "1e-05" and "1.5e-07", which no coordinate
        # payload may contain
        (1e-05, "N0.00001"),
        (-1e-05, "S0.00001"),
        (1.5e-07, "N0.00000015"),
        (51.5, "N51.5"),
        # casting returns a float even for a whole number of degrees, so the
        # spelling must not depend on which of the two the caller holds
        (0, "N0"),
        (0.0, "N0"),
        (-0.0, "N0"),
        (90, "N90"),
        (90.0, "N90"),
        (-90, "S90"),
        (-90.0, "S90"),
        (51.0, "N51"),
    ],
)
def test_format_latitude(degrees: float, expected: str) -> None:
    assert formatter._format_latitude(degrees) == expected


@pytest.mark.parametrize(
    ("degrees", "expected"),
    [
        (168.150944, "E168.150944"),
        (-168.150944, "W168.150944"),
        (-1e-05, "W0.00001"),
        (180, "E180"),
        (180.0, "E180"),
        (-180, "W180"),
        (-180.0, "W180"),
        (0.0, "E0"),
        (168.0, "E168"),
    ],
)
def test_format_longitude(degrees: float, expected: str) -> None:
    assert formatter._format_longitude(degrees) == expected


@pytest.mark.parametrize("degrees", [90.5, -90.5, 91, 1000, float("inf")])
def test_format_latitude_out_of_range(degrees: float) -> None:
    """The grammar admits "N90.5", so the range is enforced here instead."""
    with pytest.raises(GedcomSerializeError):
        formatter._format_latitude(degrees)


@pytest.mark.parametrize("degrees", [180.5, -180.5, 181])
def test_format_longitude_out_of_range(degrees: float) -> None:
    with pytest.raises(GedcomSerializeError):
        formatter._format_longitude(degrees)


@pytest.mark.parametrize("value", ["18.15", True, None])
def test_format_latitude_rejects_non_numbers(value: object) -> None:
    with pytest.raises(GedcomSerializeError):
        formatter._format_latitude(value)


# --------------------------------------------------------------------------
# Time
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("time", "expected"),
    [
        (types.Time(hour=13, minute=15), "13:15"),
        # the grammar admits a one digit hour; two is the conventional form
        (types.Time(hour=8, minute=38), "08:38"),
        (types.Time(hour=0, minute=0), "00:00"),
        (types.Time(hour=13, minute=15, second=2), "13:15:02"),
        (types.Time(hour=13, minute=15, second=12, fraction="246"), "13:15:12.246"),
        # a leading zero in the fraction survives, a trailing zero is not added
        (types.Time(hour=13, minute=15, second=12, fraction="05"), "13:15:12.05"),
        (types.Time(hour=13, minute=15, second=12, fraction="5"), "13:15:12.5"),
        (types.Time(hour=13, minute=15, second=12, fraction="500"), "13:15:12.500"),
        (types.Time(hour=13, minute=15, tz="Z"), "13:15Z"),
        (
            types.Time(hour=13, minute=15, second=12, fraction="48", tz="Z"),
            "13:15:12.48Z",
        ),
    ],
)
def test_format_time(time: types.Time, expected: str) -> None:
    assert formatter._format_time(time) == expected


def test_format_time_fraction_without_seconds() -> None:
    """The grammar hangs the fraction off the seconds, so it cannot stand alone."""
    with pytest.raises(GedcomSerializeError):
        formatter._format_time(types.Time(hour=13, minute=15, fraction="5"))


@pytest.mark.parametrize(
    "time", [types.Time(hour=24, minute=0), types.Time(hour=1, minute=60)]
)
def test_format_time_out_of_range(time: types.Time) -> None:
    with pytest.raises(GedcomSerializeError):
        formatter._format_time(time)


# --------------------------------------------------------------------------
# PersonalName: the one type whose casting formatting cannot always undo
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        # no parts at all: the name never carried slashes, so it stands as it is
        (types.PersonalName(fullname="Aka"), "Aka"),
        (types.PersonalName(fullname="Immigrant Name"), "Immigrant Name"),
        (
            types.PersonalName(fullname="John Doe", given="John", surname="Doe"),
            "John /Doe/",
        ),
        (
            types.PersonalName(
                fullname="John Doe Jr.", given="John", surname="Doe", suffix="Jr."
            ),
            "John /Doe/ Jr.",
        ),
        # each part may be absent on its own
        (types.PersonalName(fullname="Doe", surname="Doe"), "/Doe/"),
        (types.PersonalName(fullname="John", given="John"), "John //"),
        (types.PersonalName(fullname="Jr.", suffix="Jr."), "// Jr."),
    ],
)
def test_format_personal_name(name: types.PersonalName, expected: str) -> None:
    assert formatter._format_personal_name(name) == expected


def test_format_personal_name_prefers_parts_over_fullname() -> None:
    """fullname is the payload with its slashes removed, so it cannot place them."""
    name = types.PersonalName(fullname="ignored entirely", given="John", surname="Doe")
    assert formatter._format_personal_name(name) == "John /Doe/"


# --------------------------------------------------------------------------
# Age: unlike an empty DatePeriod, an empty Age has no valid payload
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("age", "expected"),
    [
        (types.Age(years=25), "25y"),
        (types.Age(days=8), "8d"),
        (types.Age(years=25, months=3, weeks=2, days=1), "25y 3m 2w 1d"),
        (types.Age(agebound=">", years=25, months=3), "> 25y 3m"),
        (types.Age(agebound="<", days=8), "< 8d"),
        (types.Age(years=0), "0y"),
    ],
)
def test_format_age(age: types.Age, expected: str) -> None:
    assert formatter._format_age(age) == expected


@pytest.mark.parametrize("age", [types.Age(), types.Age(agebound=">")])
def test_format_age_without_duration(age: types.Age) -> None:
    with pytest.raises(GedcomSerializeError):
        formatter._format_age(age)


# --------------------------------------------------------------------------
# Dates
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("date", "expected"),
    [
        (types.Date(year=2000), "2000"),
        (types.Date(month="JAN", year=2000), "JAN 2000"),
        (types.Date(day=1, month="JAN", year=2000), "1 JAN 2000"),
        (
            types.Date(calendar="JULIAN", day=1, month="JAN", year=2000),
            "JULIAN 1 JAN 2000",
        ),
        (types.Date(year=44, epoch="BCE"), "44 BCE"),
        (types.Date(day=1, month="JAN", year=44, epoch="BCE"), "1 JAN 44 BCE"),
    ],
)
def test_format_date(date: types.Date, expected: str) -> None:
    assert formatter._format_date(date) == expected


@pytest.mark.parametrize(
    "date", [types.Date(), types.Date(month="JAN"), types.Date(day=1, year=2000)]
)
def test_format_date_incomplete(date: types.Date) -> None:
    """A date needs a year, and a day is meaningless without a month."""
    with pytest.raises(GedcomSerializeError):
        formatter._format_date(date)


def test_format_date_period_empty_is_a_legal_payload() -> None:
    """The grammar makes every part of a date period optional."""
    assert formatter._format_date_period(types.DatePeriod()) == ""


@pytest.mark.parametrize(
    ("period", "expected"),
    [
        (types.DatePeriod(from_=types.Date(year=1700)), "FROM 1700"),
        (types.DatePeriod(to=types.Date(year=1800)), "TO 1800"),
        (
            types.DatePeriod(from_=types.Date(year=1700), to=types.Date(year=1800)),
            "FROM 1700 TO 1800",
        ),
    ],
)
def test_format_date_period(period: types.DatePeriod, expected: str) -> None:
    assert formatter._format_date_period(period) == expected


@pytest.mark.parametrize(
    ("date_range", "expected"),
    [
        (types.DateRange(start=types.Date(year=1700)), "AFT 1700"),
        (types.DateRange(end=types.Date(year=1800)), "BEF 1800"),
        (
            types.DateRange(start=types.Date(year=1700), end=types.Date(year=1800)),
            "BET 1700 AND 1800",
        ),
    ],
)
def test_format_date_range(date_range: types.DateRange, expected: str) -> None:
    assert formatter._format_date_range(date_range) == expected


def test_format_date_range_empty() -> None:
    with pytest.raises(GedcomSerializeError):
        formatter._format_date_range(types.DateRange())


@pytest.mark.parametrize("qualifier", ["ABT", "CAL", "EST"])
def test_format_date_approx(qualifier: str) -> None:
    approx = types.DateApprox(
        date=types.Date(day=1, month="OCT", year=2023), approx=qualifier
    )
    assert formatter._format_date_approx(approx) == f"{qualifier} 1 OCT 2023"


def test_format_date_approx_without_qualifier() -> None:
    with pytest.raises(GedcomSerializeError):
        formatter._format_date_approx(types.DateApprox(date=types.Date(year=2023)))


def test_format_date_exact() -> None:
    assert formatter._format_date_exact(
        types.DateExact(day=1, month="NOV", year=2022)
    ) == ("1 NOV 2022")


def test_format_date_value_dispatches_on_the_form() -> None:
    """A date value is whichever of the four forms the value carries."""
    assert formatter._format_date_value(types.Date(year=1998)) == "1998"
    assert (
        formatter._format_date_value(types.DatePeriod(to=types.Date(year=1800)))
        == "TO 1800"
    )
    assert (
        formatter._format_date_value(types.DateRange(end=types.Date(year=1800)))
        == "BEF 1800"
    )
    assert (
        formatter._format_date_value(
            types.DateApprox(date=types.Date(year=1800), approx="ABT")
        )
        == "ABT 1800"
    )


# --------------------------------------------------------------------------
# Scalars and lists
# --------------------------------------------------------------------------


def test_format_bool() -> None:
    """A false boolean is written by leaving the structure out altogether."""
    assert formatter._format_bool(True) == "Y"
    assert formatter._format_bool(False) is None


@pytest.mark.parametrize("value", [0, 1, "Y", None])
def test_format_bool_rejects_non_bools(value: object) -> None:
    with pytest.raises(GedcomSerializeError):
        formatter._format_bool(value)


def test_format_integer() -> None:
    assert formatter._format_integer(0) == "0"
    assert formatter._format_integer(100) == "100"


@pytest.mark.parametrize("value", [-1, True, 1.5, "1"])
def test_format_integer_rejects(value: object) -> None:
    """The payload is a non-negative integer, and a bool is not an integer here."""
    with pytest.raises(GedcomSerializeError):
        formatter._format_integer(value)


def test_format_list_text() -> None:
    assert (
        formatter._format_list_text(["City", "County", "State"])
        == "City, County, State"
    )
    assert formatter._format_list_text(["Somewhere"]) == "Somewhere"


def test_format_list_text_item_containing_a_comma() -> None:
    """A list has no escaping, so a comma in an item would split it in two."""
    with pytest.raises(GedcomSerializeError):
        formatter._format_list_text(["Paris, France", "Europe"])


def test_format_list_text_strips_space_around_items() -> None:
    """The grammar allows space either side of the separator, so it means nothing."""
    assert formatter._format_list_text(["City ", " County"]) == "City, County"
    assert formatter._format_list_text([" Somewhere "]) == "Somewhere"


def test_format_list_enum() -> None:
    assert formatter._format_list_enum(["BIRT", "DEAT"]) == "BIRT, DEAT"


def test_format_list_enum_does_not_strip_items() -> None:
    """An enum cannot contain a space, so a spaced item is outside the vocabulary.

    A list of text is stripped instead, because there the space really is only
    padding around a delimiter.
    """
    with pytest.raises(GedcomSerializeError):
        formatter._format_list_enum([" BIRT", "DEAT"])
    with pytest.raises(GedcomSerializeError):
        formatter._format_enum(" BIRT")


def test_format_enum() -> None:
    assert formatter._format_enum("ADOPTED") == "ADOPTED"
    assert formatter._format_enum("0") == "0"
    assert formatter._format_enum("_CUSTOM") == "_CUSTOM"


def test_format_enum_invalid() -> None:
    with pytest.raises(GedcomSerializeError):
        formatter._format_enum("not an enum")


def test_format_mediatype() -> None:
    assert (
        formatter._format_mediatype(types.MediaType(media_type="text/plain"))
        == "text/plain"
    )


def test_format_mediatype_invalid() -> None:
    with pytest.raises(GedcomSerializeError):
        formatter._format_mediatype(types.MediaType(media_type="nonsense"))


def test_format_tag_definition() -> None:
    definition = types.TagDefinition(
        tag="_SKYPEID", uri="http://xmlns.com/foaf/0.1/skypeID"
    )
    assert formatter._format_tag_definition(definition) == (
        "_SKYPEID http://xmlns.com/foaf/0.1/skypeID"
    )


def test_format_tag_definition_invalid_tag() -> None:
    """An extension tag begins with an underscore."""
    with pytest.raises(GedcomSerializeError):
        formatter._format_tag_definition(
            types.TagDefinition(tag="SKYPEID", uri="http://x/")
        )


# --------------------------------------------------------------------------
# format_value dispatch
# --------------------------------------------------------------------------


def test_format_value_dispatches_by_structure_type() -> None:
    assert gedcom7.format_value(18.150944, LATI) == "N18.150944"
    assert gedcom7.format_value(types.Time(hour=8, minute=38), TIME) == "08:38"
    assert gedcom7.format_value("free text", ABBR) == "free text"


def test_format_value_of_none() -> None:
    assert gedcom7.format_value(None, ABBR) is None


def test_format_value_of_false_is_none() -> None:
    """The caller drops the structure rather than writing an empty payload."""
    assert gedcom7.format_value(True, ADOP) == "Y"
    assert gedcom7.format_value(False, ADOP) is None


def test_format_value_unknown_structure_type() -> None:
    with pytest.raises(GedcomSerializeError):
        gedcom7.format_value("x", "https://example.com/not-a-structure-type")


def test_format_value_structure_taking_no_payload() -> None:
    with pytest.raises(GedcomSerializeError):
        gedcom7.format_value("x", BAPL)


@pytest.mark.parametrize("type_id", [V7 + "ALIA", V7 + "FAMS", V7 + "HUSB"])
def test_format_value_structure_pointing_at_a_record(type_id: str) -> None:
    """A pointer written as text would be escaped, turning a link into a string."""
    with pytest.raises(GedcomSerializeError):
        gedcom7.format_value("@I1@", type_id)


def test_every_pointer_structure_type_is_refused() -> None:
    """No structure type pointing at a record may fall through to plain text."""
    for type_id, payload in const.payloads.items():
        if payload.startswith("@<"):
            with pytest.raises(GedcomSerializeError):
                gedcom7.format_value("@I1@", type_id)


def test_every_payload_in_the_specification_is_accounted_for() -> None:
    """No kind of payload may reach format_value without a deliberate decision.

    The fallback treats a payload it does not recognise as plain text. That is
    right for the string-like types and was silently wrong for the pointer types,
    which reached it for as long as nothing enumerated what the specification
    actually contains. Partitioning the whole table makes a payload kind added by
    a later version of the specification fail here rather than fall through.
    """
    for payload in set(const.payloads.values()):
        accounted_for = (
            payload == ""
            or payload in formatter.FORMAT_FUNCTIONS
            or (payload.startswith("@<") and payload.endswith(">@"))
        )
        assert accounted_for, f"{payload} would fall through to plain text"


def test_format_value_empty_payload_is_not_no_payload() -> None:
    """An empty date period is a payload, and is not the same as None."""
    empty = gedcom7.format_value(types.DatePeriod(), V7 + "NO-DATE")
    assert empty == ""
    assert empty is not None


def test_format_value_wrong_type_for_the_structure() -> None:
    with pytest.raises(GedcomSerializeError):
        gedcom7.format_value("13:15", TIME)


def test_format_functions_mirror_cast_functions() -> None:
    """Both tables key off the payload type, so they must cover the same set."""
    from gedcom7 import cast

    assert formatter.FORMAT_FUNCTIONS.keys() == cast.CAST_FUNCTIONS.keys()
    for payload, cast_function in cast.CAST_FUNCTIONS.items():
        assert (cast_function is None) == (formatter.FORMAT_FUNCTIONS[payload] is None)


# --------------------------------------------------------------------------
# Value level round trip: the invariant a text level round trip cannot state
# --------------------------------------------------------------------------


# One structure type per data type, so that going through the public entry
# points covers every payload the two tables know about. Kept honest by
# test_round_trip_covers_every_data_type below.
ROUND_TRIP = [
    (V7 + "ADOP", "Y"),
    (V7 + "LANG", "en-US"),
    (V7 + "EXID-TYPE", "http://example.com/exid"),
    (V7 + "HEIGHT", "100"),
    (V7 + "HEIGHT", "0"),
    (V7 + "ABBR", "any text at all, commas and / included"),
    (V7 + "FORM", "text/plain"),
    (V7 + "AGE", "> 25y 3m 2w 1d"),
    (V7 + "AGE", "8d"),
    (V7 + "DATE", "1998"),
    (V7 + "DATE", "FROM 1700 TO 1800"),
    (V7 + "DATE", "BET 1 JAN 2000 AND 31 DEC 2000"),
    (V7 + "DATE", "ABT 1 OCT 2023"),
    (V7 + "DATE", "JULIAN 1 JAN 44 BCE"),
    (V7 + "DATE-exact", "1 NOV 2022"),
    (V7 + "NO-DATE", "FROM 1700 TO 1800"),
    (V7 + "NO-DATE", "TO 1800"),
    (V7 + "FAMC-ADOP", "BOTH"),
    (V7 + "FILE", "media/original.mp3"),
    (V7 + "LATI", "N18.150944"),
    (V7 + "LATI", "S0.00001"),
    # a whole number of degrees casts to a float, and must not come back "N90.0"
    (V7 + "LATI", "N90"),
    (V7 + "LATI", "N0"),
    (V7 + "LATI", "S51"),
    (V7 + "LONG", "E168.150944"),
    (V7 + "LONG", "W0.00001"),
    (V7 + "LONG", "E180"),
    (V7 + "DATA-EVEN", "BIRT, DEAT"),
    (V7 + "PLAC-FORM", "City, County, State"),
    (V7 + "INDI-NAME", "John /Doe/ Jr."),
    (V7 + "INDI-NAME", "/Doe/"),
    (V7 + "INDI-NAME", "Aka"),
    (V7 + "TAG", "_SKYPEID http://xmlns.com/foaf/0.1/skypeID"),
    (V7 + "TIME", "13:15:12.05Z"),
    (V7 + "TIME", "13:15:12.500"),
]


@pytest.mark.parametrize(("type_id", "text"), ROUND_TRIP)
def test_formatting_is_the_inverse_of_casting(type_id: str, text: str) -> None:
    """Formatting a cast payload gives the payload back."""
    assert gedcom7.format_value(gedcom7.cast.cast_value(text, type_id), type_id) == text


@pytest.mark.parametrize(("type_id", "text"), ROUND_TRIP)
def test_casting_is_the_inverse_of_formatting(type_id: str, text: str) -> None:
    """Casting a formatted value gives the value back.

    This is the direction that is exact for every value that came from casting a
    payload, PersonalName included: casting is what discards detail, so once a
    value has been through it the pair is a true inverse. The empty payload is
    the exception, and test_empty_payload_does_not_round_trip pins it.
    """
    value = gedcom7.cast.cast_value(text, type_id)
    formatted = gedcom7.format_value(value, type_id)
    assert formatted is not None
    assert gedcom7.cast.cast_value(formatted, type_id) == value


def test_empty_payload_does_not_round_trip() -> None:
    """Casting maps every empty payload to None, whatever data type it belongs to.

    So an empty DatePeriod, which is a legal date period, formats to "" and casts
    back to None rather than to DatePeriod(). Nothing is lost by it: a structure
    written with an empty payload and one written with no payload are the same
    line, so the two spellings are not distinguishable in a data stream to begin
    with. Preserving them instead would mean casting an empty Y|<NULL> to False,
    which would read "1 DEAT" with no payload as an assertion that the death did
    not happen, the opposite of what it means.
    """
    assert gedcom7.format_value(types.DatePeriod(), V7 + "NO-DATE") == ""
    assert gedcom7.cast.cast_value("", V7 + "NO-DATE") is None
    assert gedcom7.cast.cast_value("", V7 + "DEAT") is None


def test_round_trip_covers_every_data_type() -> None:
    """Every payload either table knows about must appear in the round trip."""
    covered = {const.payloads[type_id] for type_id, _ in ROUND_TRIP}
    assert covered == set(gedcom7.cast.CAST_FUNCTIONS)
    assert covered == set(formatter.FORMAT_FUNCTIONS)


# --------------------------------------------------------------------------
# Corpus sweep
# --------------------------------------------------------------------------

# Payloads in the corpus that formatting writes differently from how they were
# read. Each denotes the same value; the grammar simply admits more than one
# spelling, and formatting picks the conventional one.
CORPUS_NORMALIZATIONS = {
    # the grammar admits a one digit hour
    ("https://gedcom.io/terms/v7/type-Time", "8:38"): "08:38",
}


def test_every_corpus_payload_round_trips() -> None:
    """Format every text payload in maximal70.ged and compare with the original.

    Structures with no text are left out, which is not the same as leaving out
    nothing: most of them point at a record rather than carrying a value, and
    format_value refuses those by design. The rest have an empty payload, which
    casting maps to None, so there is no value to format and nothing to compare.
    """
    filename = pathlib.Path(__file__).parent / "data" / "maximal70.ged"
    records = gedcom7.loads(filename.read_text(encoding="utf-8"))

    formatted = 0
    unexpected = []

    def visit(structure: types.GedcomStructure) -> None:
        nonlocal formatted
        type_id = structure.type_id
        if type_id is not None and structure.text and const.payloads.get(type_id):
            expected = CORPUS_NORMALIZATIONS.get(
                (const.payloads[type_id], structure.text), structure.text
            )
            actual = gedcom7.format_value(structure.value, type_id)
            formatted += 1
            if actual != expected:
                unexpected.append((structure.tag, type_id, structure.text, actual))
        for child in structure.children:
            visit(child)

    for record in records:
        visit(record)

    assert not unexpected
    # a guard against the sweep quietly stopping to visit anything
    assert formatted > 600


# --------------------------------------------------------------------------
# set_value
# --------------------------------------------------------------------------


def test_set_value_uses_the_superstructure_to_find_the_data_type() -> None:
    """R2: an attached structure knows its own structure type."""
    individual = types.GedcomStructure(tag="INDI", xref="@I1@")
    birth = types.GedcomStructure(tag="BIRT")
    individual.append_child(birth)
    date = types.GedcomStructure(tag="DATE")
    birth.append_child(date)

    gedcom7.set_value(date, types.Date(day=1, month="JAN", year=2000))
    assert date.text == "1 JAN 2000"
    assert date.value == types.Date(day=1, month="JAN", year=2000)


def test_set_value_accepts_an_explicit_structure_type() -> None:
    """R1: naming the structure type works before the structure is attached."""
    date = types.GedcomStructure(tag="DATE")
    gedcom7.set_value(
        date,
        types.Date(day=1, month="JAN", year=2000),
        type_id="https://gedcom.io/terms/v7/DATE",
    )
    assert date.text == "1 JAN 2000"


def test_set_value_explicit_type_id_wins_over_the_superstructure() -> None:
    individual = types.GedcomStructure(tag="INDI", xref="@I1@")
    child = types.GedcomStructure(tag="DATE")
    individual.append_child(child)
    gedcom7.set_value(
        child, types.Time(hour=13, minute=15), type_id="https://gedcom.io/terms/v7/TIME"
    )
    assert child.text == "13:15"


def test_set_value_on_an_unattached_structure_says_so() -> None:
    """V5: the common way to get this wrong is to build the tree upwards."""
    date = types.GedcomStructure(tag="DATE")
    assert date.type_id is None
    with pytest.raises(gedcom7.GedcomSerializeError, match="superstructure"):
        gedcom7.set_value(date, types.Date(day=1, month="JAN", year=2000))


def test_set_value_of_a_string_where_no_standard_type_applies() -> None:
    """V4: an extension payload is carried as it stands, as the getter returns it."""
    structure = types.GedcomStructure(tag="_MYTAG")
    assert structure.type_id is None
    gedcom7.set_value(structure, "whatever the extension means")
    assert structure.text == "whatever the extension means"
    assert structure.value == "whatever the extension means"


def test_set_value_of_false_cannot_empty_the_payload() -> None:
    """V2: the specification writes a false Y|<NULL> by omitting the structure."""
    individual = types.GedcomStructure(tag="INDI", xref="@I1@")
    death = types.GedcomStructure(tag="DEAT")
    individual.append_child(death)

    gedcom7.set_value(death, True)
    assert death.text == "Y"
    with pytest.raises(gedcom7.GedcomSerializeError, match="leaving the structure out"):
        gedcom7.set_value(death, False)


def test_set_value_propagates_a_value_that_cannot_be_written() -> None:
    """V3: format_value does the validating, and its refusals reach the caller."""
    individual = types.GedcomStructure(tag="INDI", xref="@I1@")
    birth = types.GedcomStructure(tag="BIRT")
    individual.append_child(birth)
    date = types.GedcomStructure(tag="DATE")
    birth.append_child(date)

    with pytest.raises(gedcom7.GedcomSerializeError):
        gedcom7.set_value(date, types.Date(day=1, year=2000))


def test_set_value_round_trips_through_the_serializer() -> None:
    """A tree built with set_value alone serializes and parses back unchanged."""
    head = types.GedcomStructure(tag="HEAD")
    gedc = types.GedcomStructure(tag="GEDC")
    head.append_child(gedc)
    vers = types.GedcomStructure(tag="VERS")
    gedc.append_child(vers)
    gedcom7.set_value(vers, "7.0")

    individual = types.GedcomStructure(tag="INDI", xref="@I1@")
    name = types.GedcomStructure(tag="NAME")
    individual.append_child(name)
    gedcom7.set_value(
        name, types.PersonalName(fullname="John Doe", given="John", surname="Doe")
    )
    birth = types.GedcomStructure(tag="BIRT")
    individual.append_child(birth)
    date = types.GedcomStructure(tag="DATE")
    birth.append_child(date)
    gedcom7.set_value(date, types.Date(day=1, month="JAN", year=2000))

    trlr = types.GedcomStructure(tag="TRLR")
    text = gedcom7.dumps([head, individual, trlr], byte_order_mark=False)
    assert text == (
        "0 HEAD\n1 GEDC\n2 VERS 7.0\n0 @I1@ INDI\n1 NAME John /Doe/\n"
        "1 BIRT\n2 DATE 1 JAN 2000\n0 TRLR\n"
    )
    assert gedcom7.loads(text) == [head, individual, trlr]


def test_format_value_docstring_examples() -> None:
    """The examples in format_value's docstring have to be true."""
    assert gedcom7.format_value(types.Date(year=2000), V7 + "DATE") == "2000"
    assert gedcom7.format_value(types.DatePeriod(), V7 + "NO-DATE") == ""
    assert gedcom7.format_value(False, V7 + "ADOP") is None
