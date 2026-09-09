import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def client(tmp_path: Path):
    os.environ["DATABASE_PATH"] = str(tmp_path / "test.db")
    os.environ["AI_PROVIDER"] = "local"
    os.environ["ADMIN_API_KEY"] = "test-admin-key"
    from app.config import get_settings

    get_settings.cache_clear()
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
