"""Exceptions for the Hermes integration."""


class HermesError(Exception):
    """Base exception for Hermes errors."""


class HermesConnectionError(HermesError):
    """Raised when connection to Hermes API fails."""


class HermesAuthenticationError(HermesError):
    """Raised when authentication fails (bad API key)."""


class HermesTimeoutError(HermesError):
    """Raised when the request times out."""
