"""Shared fixtures and path bootstrap for the test suite (ROADMAP R8).

Ensures the repository root is importable regardless of how ``pytest tests/`` is
invoked, and provides fixtures shared across test modules. Importing the API
application is deferred to the fixture so a missing/heavy dependency cannot
break *collection* of unrelated test files.
"""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def client():
    """A FastAPI test client bound to the served application."""
    from src.api.server import app

    return TestClient(app)
