"""IBKR exceptions module"""


class IBKRClientError(Exception):
    """Base exception for IBKR client errors"""

    pass


class IBKRAuthenticationError(IBKRClientError):
    """Raised when OAuth authentication fails"""

    pass


class IBKRConnectionError(IBKRClientError):
    """Raised when connection fails"""

    pass
