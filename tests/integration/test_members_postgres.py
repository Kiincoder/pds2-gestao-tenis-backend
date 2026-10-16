from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.models import MemberModel, UserModel
from app.handlers.administrator import PromoteAdministratorHandler
from app.repositories.sqlalchemy_users import SqlAlchemyUserRepository

pytestmark = pytest.mark.integration


def test_public_account_starts_without_administrative_permission(
    database_client, db_session, registration_payload
):
    created = database_client.post("/api/v1/auth/register", json=registration_payload)
    assert created.status_code == 201
    user = db_session.scalars(select(UserModel)).one()
    assert not user.is_admin
    login = database_client.post(
        "/api/v1/auth/login",
        json={"email": registration_payload["email"], "password": registration_payload["password"]},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert database_client.get("/api/v1/members", headers=headers).status_code == 403

    # A permissão é lida do banco, inclusive para um token emitido antes da promoção.
    PromoteAdministratorHandler(SqlAlchemyUserRepository(db_session)).handle(
        registration_payload["email"]
    )
    assert database_client.get("/api/v1/members", headers=headers).status_code == 200
    user.is_admin = False
    db_session.commit()
    assert database_client.get("/api/v1/members", headers=headers).status_code == 403


def test_member_lifecycle_and_phone_removal(member_admin_client, db_session):
    client, headers = member_admin_client
    created = client.post(
        "/api/v1/members",
        headers=headers,
        json={"name": " Maria Silva ", "email": " MARIA@Example.COM ", "phone": "+55 31999991234"},
    )
    assert created.status_code == 201
    member = created.json()["data"]
    path = f"/api/v1/members/{member['id']}"
    assert member["name"] == "Maria Silva"
    assert member["email"] == "maria@example.com"
    assert member["status"] == "active"
    assert client.get(path, headers=headers).json()["data"]["id"] == member["id"]

    changed = client.patch(path, headers=headers, json={"name": "Maria Atualizada"})
    assert changed.status_code == 200
    assert changed.json()["data"]["phone"] == "+55 31999991234"
    cleared = client.patch(path, headers=headers, json={"phone": None, "status": "inactive"})
    assert cleared.status_code == 200
    assert cleared.json()["data"]["phone"] is None
    assert cleared.json()["data"]["status"] == "inactive"
    listing = client.get("/api/v1/members?status=inactive", headers=headers)
    assert listing.json()["meta"]["total"] == 1

    assert client.delete(path, headers=headers).status_code == 204
    assert client.get(path, headers=headers).status_code == 404
    assert client.delete(path, headers=headers).status_code == 404
    assert db_session.scalar(select(func.count()).select_from(MemberModel)) == 0
    # O cadastro de membro não cria, edita ou remove a conta de acesso da US01.
    assert db_session.scalar(select(func.count()).select_from(UserModel)) == 1


def test_duplicate_create_and_update_rollback_preserve_data(member_admin_client):
    client, headers = member_admin_client
    first = client.post(
        "/api/v1/members", headers=headers, json={"name": "Maria", "email": "maria@example.com"}
    )
    duplicate = client.post(
        "/api/v1/members", headers=headers, json={"name": "Outra", "email": " MARIA@EXAMPLE.COM "}
    )
    assert first.status_code == 201
    assert duplicate.status_code == 409
    second = client.post(
        "/api/v1/members", headers=headers, json={"name": "João", "email": "joao@example.com"}
    )
    assert second.status_code == 201
    path = f"/api/v1/members/{second.json()['data']['id']}"
    conflict = client.patch(path, headers=headers, json={"email": "MARIA@EXAMPLE.COM"})
    assert conflict.status_code == 409
    assert client.get(path, headers=headers).json()["data"]["email"] == "joao@example.com"
    changed = client.patch(path, headers=headers, json={"name": "João Atualizado"})
    assert changed.status_code == 200
    assert client.get("/api/v1/members", headers=headers).json()["meta"]["total"] == 2


def test_pagination_status_and_literal_search(member_admin_client):
    client, headers = member_admin_client
    for payload in [
        {"name": "Maria", "email": "maria@example.com", "status": "active"},
        {"name": "João", "email": "joao@example.com", "status": "inactive"},
        {"name": "Mariana", "email": "mariana@example.com", "status": "active"},
    ]:
        assert client.post("/api/v1/members", headers=headers, json=payload).status_code == 201
    page = client.get("/api/v1/members?page=2&page_size=2", headers=headers).json()
    assert page["meta"] == {"page": 2, "page_size": 2, "total": 3, "total_pages": 2}
    assert len(page["data"]) == 1
    filtered = client.get("/api/v1/members?status=active&q=MARIA", headers=headers).json()
    assert filtered["meta"]["total"] == 2
    # Caracteres de padrão SQL são tratados como texto, não como curingas.
    for query in ["%", "_"]:
        response = client.get("/api/v1/members", headers=headers, params={"q": query})
        assert response.json()["meta"]["total"] == 0


def test_database_constraints_reject_invalid_member_status(db_session):
    now = datetime.now(UTC)
    db_session.add(
        MemberModel(
            name="Maria", email="maria@example.com", status="other", created_at=now, updated_at=now
        )
    )
    with pytest.raises(IntegrityError) as caught:
        db_session.flush()
    assert caught.value.orig.diag.constraint_name == "ck_members_status"
    db_session.rollback()
