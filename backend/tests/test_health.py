from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.api.health import get_session
from app.core.config import Settings
from app.main import create_app


def test_liveness_does_not_require_database():
    settings = Settings(
        _env_file=None, database_url="postgresql+psycopg://localhost:1/unused"
    )
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        response = client.get("/api/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}


def test_readiness_executes_query_and_sanitizes_failure():
    settings = Settings(
        _env_file=None, database_url="postgresql+psycopg://localhost:1/unused"
    )
    app = create_app(settings)
    session = MagicMock()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        assert client.get("/api/health/ready").json() == {"status": "ready"}
        assert str(session.execute.call_args.args[0]) == "SELECT 1"
        session.execute.side_effect = OperationalError(
            "private query", {}, Exception("secret")
        )
        response = client.get("/api/health/ready")
        assert response.status_code == 503
        assert response.json() == {"status": "unavailable"}
