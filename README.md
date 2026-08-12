# gedcom7

[![Tests](https://github.com/DavidMStraub/python-gedcom7/actions/workflows/test.yml/badge.svg)](https://github.com/DavidMStraub/python-gedcom7/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/gedcom7)](https://pypi.org/project/gedcom7/)
[![Python versions](https://img.shields.io/pypi/pyversions/gedcom7)](https://pypi.org/project/gedcom7/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

A [GEDCOM 7](https://gedcom.io/) parser for Python.

## Background

The parser is based on regular expressions generated directly from the ABNF
grammar via [`abnf-to-regexp`](https://github.com/aas-core-works/abnf-to-regexp),
and on the structure and payload tables extracted from the specification. It
targets FamilySearch GEDCOM
[7.0.18](https://github.com/FamilySearch/GEDCOM/blob/main/specification/).

It does not attempt to parse files that are not standards compliant: a data
stream that violates the specification raises `GedcomParseError` rather than
being partially or silently misparsed.

## Installation

```
python -m pip install gedcom7
```

## Usage

```python
import gedcom7

with open("my_gedcom.ged", "r", encoding="utf-8") as f:
    string = f.read()

records = gedcom7.loads(string)
```

Each record is a `GedcomStructure` with a `tag`, an optional `xref` and
`pointer`, the raw `text` payload, and `children`. The `value` property casts the
payload to the data type the specification gives that structure type:

```python
indi = records[1]  # 0 @I1@ INDI
birt = indi.children[0]  # 1 BIRT
date = birt.children[0]  # 2 DATE 1 JAN 2000
date.type_id  # 'https://gedcom.io/terms/v7/DATE'
date.value  # Date(calendar=None, day=1, month='JAN', ...)
```

`value` is `None` where a structure has no payload, and the payload is returned
uninterpreted where the structure type is defined by an extension rather than by
the specification.

### Errors

`loads` raises `GedcomParseError` (a subclass of `ValueError`) for any data
stream that does not conform to the specification, reporting where the problem
is:

```python
from gedcom7 import GedcomParseError

try:
    records = gedcom7.loads(string)
except GedcomParseError as exc:
    print(exc)  # line 42: malformed line: '1 NOTE @invalid'
    print(exc.line_number)  # 42
    print(exc.line)  # "1 NOTE @invalid"
```

This covers malformed lines, prohibited level sequences, banned characters,
misplaced `CONT` continuations, duplicate or misplaced cross-reference
identifiers, pointers that resolve to nothing, and a missing header or trailer.

## Development

Install the package together with the development dependencies:

```
python -m pip install --group dev --editable .
```

Then run the checks:

```
pytest          # tests
mypy            # static type check (strict)
ruff check .    # lint
ruff format .   # format
```

## Releasing

The version is derived from git tags by
[setuptools-scm](https://setuptools-scm.readthedocs.io/); there is no version
string in the source tree. To release, push a `vX.Y.Z` tag and publish a GitHub
release for it — the `PyPI deploy` workflow builds the distributions and
uploads them via PyPI trusted publishing.

## Credits

Inspiration was drawn from the [Javascript parser](https://github.com/gedcom7code/js-parser).
