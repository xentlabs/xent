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


class XegaInternalError(XegaError):
    """Raised when there is an error in the Xega codebase. This indicates an issue in Xega itself"""

    def __init__(self, message: str):
        super().__init__(f"Xega Internal Error: {message}")


class XegaTypeError(XegaError):
    """Raised when there is a type error in Xega"""

    def __init__(self, message: str):
        super().__init__(f"Xega Type Error: {message}")
