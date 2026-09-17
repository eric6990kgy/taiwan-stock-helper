import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db, get_gemini_client
from app.database.base import Base
from app import models  # noqa: F401
from app.database.seed import seed
from app.main import app
from app.services.gemini_client import GeminiClient


@event.listens_for(Engine, "connect")
def _enable_sqlite_fk(dbapi_connection, _):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture()
def client():
    """A fresh in-memory SQLite DB (schema built from the models, seeded
    with the standard demo dataset) wired into the FastAPI app for each
    test via dependency override, so tests never touch the real
    investment_os.db file."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    session = TestSessionLocal()
    seed(session)
    session.close()

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # Force Gemini off for every API test by default, regardless of
    # whatever GEMINI_API_KEY is actually set to in the developer's local
    # .env -- tests must never make real, billed external calls (same
    # "no live external calls" rule already enforced for FinMind via
    # StubProvider). A test that wants to exercise the enabled path
    # overrides this again with its own fake, same pattern as stub_provider.
    app.dependency_overrides[get_gemini_client] = lambda: GeminiClient(api_key="")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    engine.dispose()
