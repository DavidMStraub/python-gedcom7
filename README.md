# gedcom7

[![Tests](https://github.com/DavidMStraub/python-gedcom7/actions/workflows/test.yml/badge.svg)](https://github.com/DavidMStraub/python-gedcom7/actions/workflows/test.yml)
[![PyPI](https://img.shields.io/pypi/v/gedcom7)](https://pypi.org/project/gedcom7/)
[![Python versions](https://img.shields.io/pypi/pyversions/gedcom7)](https://pypi.org/project/gedcom7/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

A [GEDCOM 7](https://gedcom.io/) parser for Python.

## Background

The parser is based on regular expressions generated directly from the ABNF grammar via [`abnf-to-regexp`](https://github.com/aas-core-works/abnf-to-regexp). It does not attempt to parse files that are not standards compliant.

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
