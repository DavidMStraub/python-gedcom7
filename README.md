# gedcom7

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

## Credits

Inspiration was drawn from the [Javascript parser](https://github.com/gedcom7code/js-parser).
