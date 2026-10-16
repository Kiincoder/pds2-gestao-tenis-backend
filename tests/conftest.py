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
from app.dependencies import get_register_handler, get_session
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
