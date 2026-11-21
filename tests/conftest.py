"""
AquaSure Test Configuration
Adds project root to sys.path and provides shared fixtures.
"""

import sys
import os
import pytest

# Ensure the project root is on sys.path so both src/ and backend/ are importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(scope="session")
def flask_app():
    """Create the Flask application configured for testing."""
    from backend.app import create_app
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture(scope="session")
def client(flask_app):
    """Return a test client for the Flask application."""
    return flask_app.test_client()
