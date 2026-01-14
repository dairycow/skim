"""Consolidated exceptions for Skim trading bot.

All custom exceptions are defined here to provide a single source of truth
for error handling across the application.
"""


class SkimError(Exception):
    """Base exception for Skim errors"""

    pass


class IBKRClientError(SkimError):
    """Base exception for IBKR client errors"""

    pass


class IBKRAuthenticationError(IBKRClientError):
    """Raised when OAuth authentication fails"""

    pass


class IBKRConnectionError(IBKRClientError):
    """Raised when connection fails"""

    pass


class IBKRRequestError(IBKRClientError):
    """Raised when an HTTP request to IBKR fails"""

    pass


class ScannerError(SkimError):
    """Base scanner error"""

    pass


class ScannerValidationError(ScannerError):
    """Raised when scanner validation fails"""

    pass


class GapCalculationError(ScannerError):
    """Raised when gap calculation fails"""

    pass


class TradingError(SkimError):
    """Base trading error"""

    pass


class OrderError(TradingError):
    """Raised when order placement or execution fails"""

    pass


class PositionError(TradingError):
    """Raised when position operation fails"""

    pass


class DatabaseError(SkimError):
    """Base database error"""

    pass


class RepositoryError(SkimError):
    """Base repository error"""

    pass


class CandidateRepositoryError(RepositoryError):
    """Raised when candidate repository operation fails"""

    pass


class PositionRepositoryError(RepositoryError):
    """Raised when position repository operation fails"""

    pass


class ConfigurationError(SkimError):
    """Raised when configuration is invalid or missing"""

    pass


class NotificationError(SkimError):
    """Base notification error"""

    pass


class DiscordNotificationError(NotificationError):
    """Raised when Discord notification fails"""

    pass
