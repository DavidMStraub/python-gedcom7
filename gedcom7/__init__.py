"""Base module for gedcom7."""

from importlib.metadata import PackageNotFoundError, version

from .exceptions import GedcomError, GedcomParseError, GedcomSerializeError
from .format import format_value
from .parser import load, loads
from .serializer import dump, dumps

__all__ = [
    "GedcomError",
    "GedcomParseError",
    "GedcomSerializeError",
    "dump",
    "dumps",
    "format_value",
    "load",
    "loads",
]

try:
    __version__ = version("gedcom7")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "0.0.0.dev0"
