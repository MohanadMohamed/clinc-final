from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def build_engine(url: str):
    if make_url(url).drivername != "postgresql+psycopg":
        raise ValueError("PostgreSQL with psycopg is required")
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
        connect_args={"connect_timeout": 3, "options": "-c statement_timeout=3000"},
        hide_parameters=True,
    )


def build_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)
