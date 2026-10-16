import pytest
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.db.models import UserModel

pytestmark = pytest.mark.integration


def test_registration_persists_an_argon2_hash(database_client, db_session, registration_payload):
    response = database_client.post("/api/v1/auth/register", json=registration_payload)
    assert response.status_code == 201
    record = db_session.scalars(select(UserModel)).one()
    assert record.password_hash.startswith("$argon2id$")
    assert PasswordHash.recommended().verify(registration_payload["password"], record.password_hash)
    assert response.json()["data"]["id"] == record.id
    assert "password" not in response.json()["data"]
    assert "password_hash" not in response.json()["data"]


def test_duplicate_email_and_rollback_leave_session_usable(
    database_client, db_session, registration_payload
):
    created = database_client.post("/api/v1/auth/register", json=registration_payload)
    assert created.status_code == 201
    registration_payload["email"] = " MARIA@EXAMPLE.COM "
    duplicate = database_client.post("/api/v1/auth/register", json=registration_payload)
    assert duplicate.status_code == 422
    assert "email" in duplicate.json()["errors"]
    registration_payload["email"] = "outra@example.com"
    another = database_client.post("/api/v1/auth/register", json=registration_payload)
    assert another.status_code == 201
    assert len(db_session.scalars(select(UserModel)).all()) == 2


def test_postgres_rejects_non_normalized_emails(db_session):
    db_session.add(UserModel(name="Maria", email="MARIA@example.com", password_hash="test-only"))
    with pytest.raises(IntegrityError) as caught:
        db_session.flush()
    assert caught.value.orig.diag.constraint_name == "ck_users_email_normalized"
    db_session.rollback()
