"""IBKR infrastructure module

IBKRAuthManager - OAuth LST generation and validation
IBKRConnectionManager - Connection lifecycle and keepalive
IBKRRequestClient - HTTP requests with retry logic
IBKRClientFacade - Lightweight facade replacing monolithic IBKRClient
"""

from .auth import IBKRAuthManager
from .connection import IBKRConnectionManager
from .exceptions import (
    IBKRAuthenticationError,
    IBKRClientError,
    IBKRConnectionError,
)
from .facade import (
    IBKRClient,
    IBKRClientFacade,
    install_logging_bridge,
)
from .requests import IBKRRequestClient

__all__ = [
    "IBKRAuthManager",
    "IBKRAuthenticationError",
    "IBKRConnectionManager",
    "IBKRRequestClient",
    "IBKRClient",
    "IBKRClientFacade",
    "IBKRClientError",
    "IBKRConnectionError",
    "install_logging_bridge",
]
