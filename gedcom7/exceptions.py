"""Exceptions raised by gedcom7."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .validate import Error


class GedcomError(Exception):
    """Base class for all errors raised by this package."""


class GedcomSerializeError(GedcomError, ValueError):
    """Raised when structures cannot be encoded as a conforming data stream."""


class GedcomValidationError(GedcomError, ValueError):
    """Raised when a dataset fails validation, carrying every problem found."""

    def __init__(self, errors: list[Error]) -> None:
        """Record the errors and summarize them in the message."""
        self.errors = errors
        first = "; ".join(f"{e.path}: {e.message}" for e in errors[:3])
        more = f", and {len(errors) - 3} more" if len(errors) > 3 else ""
        super().__init__(f"{len(errors)} validation errors: {first}{more}")


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
