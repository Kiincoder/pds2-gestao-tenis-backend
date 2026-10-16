import os
from pathlib import Path
from unittest.mock import Mock

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.dependencies import (
    get_create_member_handler,
    get_current_session,
    get_delete_member_handler,
    get_list_members_handler,
    get_login_handler,
    get_logout_handler,
    get_member_handler,
    get_register_handler,
    get_session,
    get_update_member_handler,
)
from app.main import create_app


@pytest.fixture
def registration_payload():
    return {
        "name": "Maria Silva",
        "email": "maria@example.com",
        "password": "SenhaSegura123",
        "password_confirmation": "SenhaSegura123",
    }


@pytest.fixture
def http_client():
    from datetime import UTC, datetime

    from app.domain.entities import User

    application = create_app(
        Settings(
            _env_file=None, registration_rate_limit=5, registration_rate_window_seconds=60
        )
    )
    handler = Mock()
    handler.handle.return_value = User(1, "Maria Silva", "maria@example.com", datetime.now(UTC))
    application.dependency_overrides[get_register_handler] = lambda: handler
    with TestClient(application) as client:
        yield client, handler


@pytest.fixture
def auth_http_client():
    from datetime import UTC, datetime, timedelta

    from app.core.tokens import TokenService
    from app.domain.entities import LoginResult, User

    application = create_app(
        Settings(_env_file=None, login_rate_limit=10, login_rate_window_seconds=60)
    )
    user = User(1, "Maria Silva", "maria@example.com", datetime.now(UTC))
    login_handler = Mock()
    logout_handler = Mock()
    login_handler.handle.return_value = LoginResult(
        user, TokenService().issue(), datetime.now(UTC) + timedelta(hours=1)
    )
    application.dependency_overrides[get_login_handler] = lambda: login_handler
    application.dependency_overrides[get_logout_handler] = lambda: logout_handler
    with TestClient(application) as client:
        yield client, login_handler, logout_handler, application


@pytest.fixture
def member_http_client():
    from datetime import UTC, datetime

    from app.domain.entities import (
        AuthenticatedSession,
        Member,
        MemberPage,
        MemberStatus,
        User,
    )

    application = create_app(Settings(_env_file=None))
    now = datetime.now(UTC)
    admin = User(1, "Admin", "admin@example.com", now, is_admin=True)
    member = Member(1, "Maria Silva", "maria@example.com", None, MemberStatus.ACTIVE, now, now)
    handlers = {name: Mock() for name in ["create", "list", "get", "update", "delete"]}
    for name in ["create", "get", "update"]:
        handlers[name].handle.return_value = member
    handlers["list"].handle.return_value = MemberPage((member,), 1, 1, 20)

    def dependency_override(handler):
        return lambda: handler

    for dependency, name in [
        (get_create_member_handler, "create"),
        (get_list_members_handler, "list"),
        (get_member_handler, "get"),
        (get_update_member_handler, "update"),
        (get_delete_member_handler, "delete"),
    ]:
        application.dependency_overrides[dependency] = dependency_override(handlers[name])
    context = AuthenticatedSession(admin, "hash")
    application.dependency_overrides[get_current_session] = lambda: context
    application.dependency_overrides[get_session] = lambda: None
    with TestClient(application) as client:
        yield client, handlers, application


@pytest.fixture
def member_admin_client(database_client, db_session, registration_payload):
    from app.handlers.administrator import PromoteAdministratorHandler
    from app.repositories.sqlalchemy_users import SqlAlchemyUserRepository

    created = database_client.post("/api/v1/auth/register", json=registration_payload)
    assert created.status_code == 201
    PromoteAdministratorHandler(SqlAlchemyUserRepository(db_session)).handle(
        registration_payload["email"]
    )
    login = database_client.post(
        "/api/v1/auth/login",
        json={"email": registration_payload["email"], "password": registration_payload["password"]},
    )
    assert login.status_code == 200
    return database_client, {"Authorization": f"Bearer {login.json()['access_token']}"}


@pytest.fixture(scope="session")
def postgres_engine():
    raw_url = os.environ.get("TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Defina TEST_DATABASE_URL para executar os testes de integração PostgreSQL.")
    url = make_url(raw_url)
    if url.drivername != "postgresql+psycopg" or not (url.database or "").endswith("_test"):
        pytest.fail("TEST_DATABASE_URL deve apontar para PostgreSQL e banco terminado em _test.")
    engine = create_engine(url, pool_pre_ping=True)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(postgres_engine):
    with postgres_engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
        )
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()


@pytest.fixture
def database_client(db_session):
    application = create_app(
        Settings(
            _env_file=None, registration_rate_limit=5, registration_rate_window_seconds=60
        )
    )

    def override_session():
        yield db_session

    application.dependency_overrides[get_session] = override_session
    with TestClient(application) as client:
        yield client
