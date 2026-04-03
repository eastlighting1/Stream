"""Typed Stream exceptions."""


class StreamError(Exception):
    """Base error for Stream."""


class LayoutError(StreamError):
    """Raised when layout metadata or segment state is invalid."""


class RecordValidationError(StreamError):
    """Raised when an input record is not a valid canonical record."""


class AppendError(StreamError):
    """Raised when append execution fails."""


class ReplayError(StreamError):
    """Raised when replay cannot proceed safely."""


class IntegrityError(StreamError):
    """Raised when integrity processing fails unexpectedly."""
