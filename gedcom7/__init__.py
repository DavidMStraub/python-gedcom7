"""Base module for gedcom7."""

from importlib.metadata import PackageNotFoundError, version

from .parser import loads

__all__ = ["loads"]

try:
    __version__ = version("gedcom7")
except PackageNotFoundError:  # pragma: no cover - source checkout without install
    __version__ = "0.0.0.dev0"
