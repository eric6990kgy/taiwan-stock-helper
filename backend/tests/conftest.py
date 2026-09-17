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


@pytest.fixture(autouse=True)
def _no_real_gemini_calls(monkeypatch):
    """Applies to every test in the suite (unit AND api -- this file is
    tests/conftest.py, above both subdirectories), not just ones that go
    through the API's dependency-injected get_gemini_client(). Discovered
    live 2026-09-17: once a real GEMINI_API_KEY sits in the developer's
    local .env (now a permanent fixture of this dev machine), any test
    that calls MarketDataIngestionService.update_all() without explicitly
    overriding its agent_research_service would otherwise construct a
    real, ENABLED GeminiClient() and make actual billed network calls --
    exactly the "no live external calls in tests" rule already enforced
    for FinMind via stub providers. Patches the name as imported into
    gemini_client.py's own namespace (not app.config's), since `from
    app.config import GEMINI_API_KEY` copies the reference at import time."""
    monkeypatch.setattr("app.services.gemini_client.GEMINI_API_KEY", None)


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
