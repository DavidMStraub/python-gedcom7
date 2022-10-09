GEDCOM_MIN = """0 HEAD
1 GEDC
2 VERS 7.0
0 TRLR
"""

GEDCOM_EXTTAG = """0 HEAD
1 GEDC
2 VERS 7.0.0
1 SCHMA
2 TAG _FOO http://example.com/placeholder
0 @I1@ INDI
1 ALIA @I2@
1 _FOO 23
0 @I2@ INDI
1 NAME
2 PART Tom Jones
1 ASSO @I1@
2 TYPE GODP
0 TRLR
"""

import pathlib

import gedcom7


def test_minimal():
    records = gedcom7.loads(GEDCOM_MIN)
    assert len(records) == 2
    record = records[0]
    assert record.tag == "HEAD"
    assert len(record.children) == 1
    assert record.children[0].parent == record
    assert len(record.children[0].children) == 1
    assert record.children[0].children[0].text == "7.0"
    record = records[1]
    assert record.tag == "TRLR"
    assert len(record.children) == 0

def test_maximal():
    filename = pathlib.Path(__file__).parent / "data" / "maximal70.ged"
    with open(filename, encoding="utf-8") as f:
        gedcom7.loads(f.read())

def test_exttag():
    records = gedcom7.loads(GEDCOM_EXTTAG)
    assert len(records) == 4
    assert records[1].children[1].tag == "http://example.com/placeholder"