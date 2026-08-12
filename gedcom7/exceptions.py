"""Exceptions raised by gedcom7."""

from __future__ import annotations


class GedcomError(Exception):
    """Base class for all errors raised by this package."""


class GedcomParseError(GedcomError, ValueError):
    """Raised when a data stream does not conform to the GEDCOM 7 grammar.

    Inherits from :class:`ValueError` so that existing code catching
    ``ValueError`` around :func:`gedcom7.loads` keeps working.
    """

    def __init__(
        self,
        message: str,
        *,
        line_number: int | None = None,
        line: str | None = None,
    ) -> None:
        """Record the message and, where known, the offending line."""
        self.message = message
        self.line_number = line_number
        self.line = line
        if line_number is None:
            super().__init__(message)
        else:
            super().__init__(f"line {line_number}: {message}")
