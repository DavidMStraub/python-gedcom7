# gedcom7

[![Tests](https://github.com/DavidMStraub/python-gedcom7/actions/workflows/test.yml/badge.svg)](https://github.com/DavidMStraub/python-gedcom7/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/gedcom7)](https://pypi.org/project/gedcom7/)
[![Python versions](https://img.shields.io/pypi/pyversions/gedcom7)](https://pypi.org/project/gedcom7/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

Read and write [GEDCOM 7](https://gedcom.io/) files in Python — a format for exchanging genealogical data between family history applications.

## Background

Reading and writing are both based on regular expressions generated directly from the ABNF grammar via [`abnf-to-regexp`](https://github.com/aas-core-works/abnf-to-regexp), and on the structure and payload tables extracted from the specification. The library targets FamilySearch GEDCOM [7.0.18](https://github.com/FamilySearch/GEDCOM/blob/main/specification/): it does not attempt to parse files that are not standards compliant, and raises rather than writing malformed lines.

## Installation

```
python -m pip install gedcom7
```

## Usage

```python
import gedcom7

with open("my_gedcom.ged", "rb") as f:
    records = gedcom7.load(f)

with open("out.ged", "wb") as f:
    gedcom7.dump(records, f)
```

Each record is a `GedcomStructure` with a `tag`, an optional `xref` and `pointer`, the raw `text` payload, and `children`. Its `value` property casts the payload to the data type the specification gives that structure type.

`loads` and `dumps` are the string equivalents. Non-conforming input raises `GedcomParseError`, a `ValueError` carrying `line_number`.

## Development

```
python -m pip install --group dev --editable .
pytest && mypy && ruff check . && ruff format --check .
```

The version is derived from git tags by [setuptools-scm](https://setuptools-scm.readthedocs.io/). To release, push a `vX.Y.Z` tag and publish a GitHub release for it.

## Credits

Inspiration was drawn from the [Javascript parser](https://github.com/gedcom7code/js-parser).
