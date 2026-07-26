import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from backend.models.database import init_db


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    flask_app = create_app(database=db_path)
    init_db(flask_app)
    yield flask_app
    os.remove(db_path)


@pytest.fixture
def client(app):
    # The login rate limiter tracks attempts in a module-level dict keyed by
    # IP, shared across the whole test session — clear it so tests that hit
    # /login don't see failed attempts left over from earlier tests.
    from app import _login_attempts
    _login_attempts.clear()
    return app.test_client()


@pytest.fixture
def simple_graph():
    """A tiny 3-node line graph: A -- B -- C, ~100m per hop."""
    return {
        "nodes": [
            {"id": "A", "lat": 0.0, "lon": 0.0},
            {"id": "B", "lat": 0.0009, "lon": 0.0},
            {"id": "C", "lat": 0.0018, "lon": 0.0},
        ],
        "edges": [
            {
                "id": "A_B_0", "source": "A", "target": "B",
                "length": 100.0, "speed_kph": 50, "lanes": 1,
                "highway": "residential", "name": "First St", "oneway": False,
            },
            {
                "id": "B_C_0", "source": "B", "target": "C",
                "length": 100.0, "speed_kph": 50, "lanes": 1,
                "highway": "residential", "name": "First St", "oneway": False,
            },
        ],
    }
