GEDCOM_MIN = """0 HEAD
1 GEDC
2 VERS 7.0
0 TRLR
"""

import pathlib

import gedcom7


def test_minimal():
    records = gedcom7.loads(GEDCOM_MIN)
    assert len(records) == 2
    record = records[0]
    assert record.tag == "HEAD"
    assert len(record.sub) == 1
    assert len(record.sub[0].sub) == 1
    assert record.sub[0].sub[0].linestr == "7.0"
    record = records[1]
    assert record.tag == "TRLR"
    assert len(record.sub) == 0

def test_maximal():
    filename = pathlib.Path(__file__).parent / "data" / "maximal70.ged"
    with open(filename, encoding="utf-8") as f:
        gedcom7.loads(f.read())
