import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.database.base import Base
from app import models  # noqa: F401  (registers tables on Base.metadata)


@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _):
    """SQLite ignores FK constraints unless explicitly turned on per-connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture()
def db_session():
    """Fresh in-memory SQLite DB per test, built straight from the models
    (not via Alembic) so schema/model drift itself would fail these tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
