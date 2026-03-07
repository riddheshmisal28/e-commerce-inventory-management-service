import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

# Patch the db engine inside app.main before TestClient context starts
@pytest.fixture(scope="session", autouse=True)
def mock_db_engine():
    with patch("app.main.engine.connect"), patch("app.main.Base.metadata.create_all"):
        yield

from app.main import app
from app.core.database import get_db

def override_get_db():
    yield None

@pytest.fixture(scope="module")
def client():
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
