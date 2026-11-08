import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("LOG_JSON", "false")
os.environ.setdefault("LOG_LEVEL", "WARNING")

import tempfile

os.environ.setdefault("STORAGE_DIR", tempfile.mkdtemp(prefix="vyapar-test-storage-"))

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import build_engine, get_db
from app.main import create_app

PASSWORD = "correct-horse-battery"


@pytest.fixture
def db_session_factory() -> Iterator[sessionmaker[Session]]:
    engine = build_engine("sqlite+pysqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture
def client(db_session_factory: sessionmaker[Session]) -> Iterator[TestClient]:
    app = create_app()

    def _get_db() -> Iterator[Session]:
        with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as c:
        yield c


AuthHeaders = dict[str, str]


@pytest.fixture
def make_user(client: TestClient) -> Callable[[str], AuthHeaders]:
    def _make(email: str, name: str = "Test User") -> AuthHeaders:
        r = client.post(
            "/api/v1/auth/register", json={"email": email, "full_name": name, "password": PASSWORD}
        )
        assert r.status_code == 201, r.text
        r = client.post("/api/v1/auth/login", data={"username": email, "password": PASSWORD})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _make
