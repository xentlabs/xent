class XentError(Exception):
    """Base class for all Xent exceptions."""

    pass


class XentConfigurationError(XentError):
    """Raised when there is an error in Xent configuration"""

    def __init__(self, message: str):
        super().__init__(f"Xent Validation Error: {message}")


class XentSyntaxError(XentError):
    """Raised when there is a syntax error in a Xent game"""

    # TODO - this should take in line + col for better error reporting
    def __init__(self, message: str):
        super().__init__(f"Xent Syntax Error: {message}")


class XentGameError(XentError):
    """Raised when there is an error during Xent game execution"""

    def __init__(self, message: str):
        super().__init__(f"Xent Game Error: {message}")


class XentHaltMessage(Exception):
    """Raised to alert the game engine to a halting condition encountered"""

    def __init__(self, message: str):
        super().__init__(f"Xent Halt Message: {message}")


class XentApiError(XentGameError):
    """
    Raised for failures in communication with an external LLM API.
    This is a subclass of XentGameError as it occurs during game execution.
    """

    def __init__(self, message: str, provider: str, status_code: int | None = None):
        full_message = f"Xent API Error with provider '{provider}': {message}"
        super().__init__(full_message)
        self.provider = provider
        self.status_code = status_code


class XentRateLimitError(XentApiError):
    """Raised when an API rate limit is exceeded (HTTP 429)."""

    pass


class XentAuthenticationError(XentApiError):
    """Raised for authentication failures (HTTP 401/403)."""

    pass


class XentInvalidRequestError(XentApiError):
    """Raised for malformed requests that the API rejected (HTTP 400)."""

    pass


class XentInternalServerError(XentApiError):
    """Raised for failures on the API provider's end (HTTP 5xx)."""

    pass


class XentInternalError(XentError):
    """Raised when there is an error in the Xent codebase. This indicates an issue in Xent itself"""

    def __init__(self, message: str):
        super().__init__(f"Xent Internal Error: {message}")


class XentTypeError(XentError):
    """Raised when there is a type error in Xent"""

    def __init__(self, message: str):
        super().__init__(f"Xent Type Error: {message}")
