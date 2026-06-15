import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Force test credentials before any api import
os.environ["CU_QUIZ_SECRET"] = "testsecretkey1234567890abcdef1234"
os.environ["CU_QUIZ_ADMIN_PASSWORD"] = "testpass"

from api.main import app
from api.database import Base
from api.routes.admin import get_db as admin_get_db
from api.routes.live_files import get_db as live_files_get_db
from api.routes.face_enrollments import get_db as face_enrollments_get_db

# Patch the module-level constants that were imported before env vars were forced.
import api.auth
import api.routes.admin as _admin_mod

api.auth.ADMIN_PASSWORD = "testpass"
_admin_mod.ADMIN_PASSWORD = "testpass"


@pytest.fixture(scope="session")
def engine_and_session(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("db") / "test.db"
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(eng)
    TestingSession = sessionmaker(bind=eng)
    yield eng, TestingSession
    Base.metadata.drop_all(eng)


@pytest.fixture()
def db_session(engine_and_session):
    _, TestingSession = engine_and_session
    session = TestingSession()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def client(db_session):
    def override():
        yield db_session

    app.dependency_overrides[admin_get_db] = override
    app.dependency_overrides[live_files_get_db] = override
    app.dependency_overrides[face_enrollments_get_db] = override
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_token(client):
    r = client.post("/admin/login", json={"password": "testpass"})
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture()
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}
