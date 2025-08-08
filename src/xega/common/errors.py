class XegaError(Exception):
    """Base class for all Xega exceptions."""

    pass


class XegaConfigurationError(XegaError):
    """Raised when there is an error in Xega configuration"""

    def __init__(self, message: str):
        super().__init__(f"Xega Validation Error: {message}")


class XegaSyntaxError(XegaError):
    """Raised when there is a syntax error in a Xega game"""

    # TODO - this should take in line + col for better error reporting
    def __init__(self, message: str):
        super().__init__(f"Xega Syntax Error: {message}")


class XegaGameError(XegaError):
    """Raised when there is an error during Xega game execution"""

    def __init__(self, message: str):
        super().__init__(f"Xega Game Error: {message}")


class XegaApiError(XegaGameError):
    """
    Raised for failures in communication with an external LLM API.
    This is a subclass of XegaGameError as it occurs during game execution.
    """

    def __init__(self, message: str, provider: str, status_code: int | None = None):
        full_message = f"Xega API Error with provider '{provider}': {message}"
        super().__init__(full_message)
        self.provider = provider
        self.status_code = status_code


class XegaRateLimitError(XegaApiError):
    """Raised when an API rate limit is exceeded (HTTP 429)."""

    pass


class XegaAuthenticationError(XegaApiError):
    """Raised for authentication failures (HTTP 401/403)."""

    pass


class XegaInvalidRequestError(XegaApiError):
    """Raised for malformed requests that the API rejected (HTTP 400)."""

    pass


class XegaInternalServerError(XegaApiError):
    """Raised for failures on the API provider's end (HTTP 5xx)."""

    pass


class XegaInternalError(XegaError):
    """Raised when there is an error in the Xega codebase. This indicates an issue in Xega itself"""

    def __init__(self, message: str):
        super().__init__(f"Xega Internal Error: {message}")


class XegaTypeError(XegaError):
    """Raised when there is a type error in Xega"""

    def __init__(self, message: str):
        super().__init__(f"Xega Type Error: {message}")
