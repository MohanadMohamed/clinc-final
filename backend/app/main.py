from contextlib import asynccontextmanager
from html import escape
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.appointments import router as appointments_router
from app.api.auth import router as auth_router
from app.api.billing import router as billing_router
from app.api.health import router
from app.api.patients import router as patients_router
from app.api.visits import router as visits_router
from app.core.config import Settings
from app.core.db import build_engine, build_session_factory
from app.core.request_limits import LoginBodyLimit

FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


def create_app(
    settings: Settings | None = None, frontend_dir: Path | None = None
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = settings or Settings()
        engine = build_engine(config.database_url.get_secret_value())
        app.state.settings = config
        app.state.sessions = build_session_factory(engine)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title="Clinic development scaffold",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
    )

    @app.get("/docs", include_in_schema=False, response_class=HTMLResponse)
    def local_docs():
        rows = []
        for path, operations in sorted(app.openapi()["paths"].items()):
            for method, operation in operations.items():
                if method.upper() not in {"GET", "POST", "PATCH", "PUT", "DELETE"}:
                    continue
                rows.append(
                    "<tr><td>"
                    + escape(method.upper())
                    + "</td><td>"
                    + escape(path)
                    + "</td><td>"
                    + escape(str(operation.get("summary", "")))
                    + "</td></tr>"
                )
        return (
            '<!doctype html><html lang="en"><meta charset="utf-8">'
            "<title>Clinic API</title><h1>Clinic API</h1>"
            '<p>Read-only endpoint index. <a href="/openapi.json">OpenAPI JSON</a></p>'
            "<table><thead><tr><th>Method</th><th>Path</th><th>Summary</th></tr></thead>"
            + "<tbody>"
            + "".join(rows)
            + "</tbody></table></html>"
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_unavailable(request, exc):
        return JSONResponse(
            status_code=503,
            content={"detail": "Service unavailable"},
            headers={"Cache-Control": "no-store"},
        )

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request, exc):
        return JSONResponse(status_code=422, content={"detail": "Invalid input"})

    @app.middleware("http")
    async def private_responses(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    app.add_middleware(LoginBodyLimit)
    app.include_router(auth_router)
    app.include_router(billing_router)
    app.include_router(appointments_router)
    app.include_router(patients_router)
    app.include_router(visits_router)
    app.include_router(router)
    app.frontend("/app", directory=frontend_dir or FRONTEND_DIST, check_dir=False)
    return app


app = create_app()
