"""
Custom exceptions for OBS Backend.
Centralizes all exception types for consistent error handling.
"""


class OBSBaseException(Exception):
    """Base exception for all OBS backend errors."""
    pass


class ConfigNotFoundError(OBSBaseException):
    """Raised when the tenant config file cannot be found."""
    pass


class ConfigValidationError(OBSBaseException):
    """Raised when the tenant config fails validation (missing/invalid fields)."""
    pass


class SessionExpiredError(OBSBaseException):
    """Raised when the OBS portal session has expired (redirect to login)."""
    pass


class ScraperError(OBSBaseException):
    """Raised when a scraper encounters an unrecoverable error."""
    pass


class ParseError(OBSBaseException):
    """Raised when HTML parsing fails due to unexpected structure."""
    pass
