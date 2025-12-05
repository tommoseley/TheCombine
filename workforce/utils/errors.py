# workforce/utils/errors.py

"""Custom exception classes for The Combine."""


class CanonFileNotFoundError(Exception):
    """Canon file not found at resolved path."""
    pass


class CanonParseError(Exception):
    """Canon file parsing error."""
    pass


class CanonValidationError(Exception):
    """Canon file validation error."""
    pass


class CanonNotLoadedError(Exception):
    """Canon not loaded when required."""
    pass


class CanonLoadInProgressError(Exception):
    """Canon load already in progress."""
    pass


class CanonNotReadyError(Exception):
    """Canon buffer not ready for operation."""
    pass


class InvalidStateTransitionError(Exception):
    """Invalid state transition attempted."""
    pass


class ArtifactValidationError(Exception):
    """Artifact validation failed."""
    pass


class MentorInvocationError(Exception):
    """Error invoking mentor."""
    pass