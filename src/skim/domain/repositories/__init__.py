"""Domain repositories"""

from .base import Repository
from .candidate import CandidateRepository
from .position import PositionRepository

__all__ = ["Repository", "CandidateRepository", "PositionRepository"]
