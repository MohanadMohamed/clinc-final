from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/health", tags=["health"])


class Health(BaseModel):
    status: Literal["ok", "ready", "unavailable"]


def get_session(request: Request):
    with request.app.state.sessions() as session:
        yield session


@router.get("")
def health() -> Health:
    return Health(status="ok")


@router.get("/ready", response_model=Health)
def ready(session: Annotated[Session, Depends(get_session)]):
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return Health(status="ready")
