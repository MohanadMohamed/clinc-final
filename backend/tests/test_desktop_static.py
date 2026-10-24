"""The frontend prefix cannot swallow API or documentation routes."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_spa_history_and_reserved_routes(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text(
        '<!doctype html><html lang="ar" dir="rtl"><body>synthetic shell</body></html>',
        encoding="utf-8",
    )
    (tmp_path / "assets" / "app.js").write_text("export {};", encoding="utf-8")
    settings = Settings(
        _env_file=None, database_url="postgresql+psycopg://localhost:1/unused"
    )
    with TestClient(
        create_app(settings, frontend_dir=tmp_path), base_url="https://clinic.local"
    ) as client:
        for path in ("/app/", "/app/login", "/app/patients"):
            response = client.get(path, headers={"accept": "text/html"})
            assert response.status_code == 200
            assert "synthetic shell" in response.text
        asset = client.get("/app/assets/app.js")
        assert asset.status_code == 200 and asset.text == "export {};"
        assert client.get("/api/health").json() == {"status": "ok"}
        assert (
            client.get("/api/unknown", headers={"accept": "text/html"}).status_code
            == 404
        )
        docs = client.get("/docs")
        assert docs.status_code == 200
        assert 'href="/openapi.json"' in docs.text
        assert "https://" not in docs.text
        assert client.get("/openapi.json").status_code == 200
        assert (
            client.get("/docs/unknown", headers={"accept": "text/html"}).status_code
            == 404
        )
