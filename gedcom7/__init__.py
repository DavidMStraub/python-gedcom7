"""Base module for gedcom7."""

from importlib.metadata import PackageNotFoundError, version

from .exceptions import (
    GedcomError,
    GedcomParseError,
    GedcomSerializeError,
    GedcomValidationError,
)
from .format import format_value, set_value
from .parser import load, loads
from .serializer import dump, dumps, generate_schema
from .validate import Error, validate

__all__ = [
    "GedcomError",
    "GedcomParseError",
    "GedcomSerializeError",
    "GedcomValidationError",
    "Error",
    "dump",
    "dumps",
    "format_value",
    "generate_schema",
    "load",
    "loads",
    "set_value",
    "validate",
]

try:
    __version__ = version("gedcom7")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "0.0.0.dev0"
