from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router
from app.core.config import Settings
from app.core.db import build_engine, build_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = settings or Settings()
        engine = build_engine(config.database_url.get_secret_value())
        app.state.sessions = build_session_factory(engine)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="Clinic development scaffold", lifespan=lifespan)
    app.include_router(router)
    return app


app = create_app()
