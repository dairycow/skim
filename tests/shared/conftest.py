"""Global pytest configuration and setup for Skim shared module tests"""

from pathlib import Path

import pytest
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
