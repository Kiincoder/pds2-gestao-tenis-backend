from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.tokens import TokenService
from app.db.models import SessionModel

pytestmark = pytest.mark.integration


def register_and_login(client, payload):
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_login_me_logout_and_token_reuse(database_client, db_session, registration_payload):
    token = register_and_login(database_client, registration_payload)
    headers = {"Authorization": f"Bearer {token}"}
    stored = db_session.scalars(select(SessionModel)).one()
    assert stored.token_hash == TokenService().digest(token)
    assert stored.token_hash != token
    assert stored.expires_at > datetime.now(UTC)
    assert stored.revoked_at is None

    current = database_client.get("/api/v1/auth/me", headers=headers)
    assert current.status_code == 200
    assert current.json()["data"]["email"] == registration_payload["email"]
    assert database_client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    db_session.refresh(stored)
    assert stored.revoked_at is not None
    assert database_client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert database_client.post("/api/v1/auth/logout", headers=headers).status_code == 401


def test_wrong_password_and_unknown_email_are_indistinguishable(
    database_client, db_session, registration_payload
):
    created = database_client.post("/api/v1/auth/register", json=registration_payload)
    assert created.status_code == 201
    wrong = database_client.post(
        "/api/v1/auth/login", json={"email": "maria@example.com", "password": "SenhaIncorreta"}
    )
    unknown = database_client.post(
        "/api/v1/auth/login", json={"email": "ausente@example.com", "password": "SenhaIncorreta"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert db_session.scalars(select(SessionModel)).all() == []


def test_expired_token_is_rejected(database_client, db_session, registration_payload):
    token = register_and_login(database_client, registration_payload)
    stored = db_session.scalars(select(SessionModel)).one()
    stored.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()
    headers = {"Authorization": f"Bearer {token}"}
    assert database_client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert database_client.post("/api/v1/auth/logout", headers=headers).status_code == 401


def test_logout_keeps_other_sessions_active(database_client, registration_payload):
    first = register_and_login(database_client, registration_payload)
    second = database_client.post(
        "/api/v1/auth/login",
        json={"email": registration_payload["email"], "password": registration_payload["password"]},
    ).json()["access_token"]
    assert first != second
    assert database_client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {first}"}
    ).status_code == 204
    assert database_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {second}"}
    ).status_code == 200


def test_validly_formatted_unknown_token_is_rejected(database_client):
    token = TokenService().issue()
    response = database_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401
