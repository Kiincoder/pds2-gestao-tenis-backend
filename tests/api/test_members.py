from datetime import UTC, datetime

import pytest

from app.dependencies import get_current_session
from app.domain.entities import AuthenticatedSession, MemberStatus, User
from app.domain.exceptions import DuplicateMemberEmailError, MemberNotFoundError

ENDPOINTS = [
    ("POST", "/api/v1/members", {"name": "Maria", "email": "maria@example.com"}),
    ("GET", "/api/v1/members", None),
    ("GET", "/api/v1/members/1", None),
    ("PATCH", "/api/v1/members/1", {"name": "Maria Atualizada"}),
    ("DELETE", "/api/v1/members/1", None),
]


@pytest.mark.parametrize(("method", "path", "payload"), ENDPOINTS)
def test_all_member_operations_require_login(member_http_client, method, path, payload):
    client, handlers, application = member_http_client
    del application.dependency_overrides[get_current_session]
    response = client.request(method, path, json=payload)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    for handler in handlers.values():
        handler.handle.assert_not_called()


@pytest.mark.parametrize(("method", "path", "payload"), ENDPOINTS)
def test_all_member_operations_require_admin(member_http_client, method, path, payload):
    client, handlers, application = member_http_client
    user = User(1, "Usuário", "usuario@example.com", datetime.now(UTC))
    context = AuthenticatedSession(user, "hash")
    application.dependency_overrides[get_current_session] = lambda: context
    response = client.request(method, path, json=payload)
    assert response.status_code == 403
    assert response.headers["Cache-Control"] == "no-store"
    for handler in handlers.values():
        handler.handle.assert_not_called()


def test_admin_can_create_normalized_member(member_http_client):
    client, handlers, _ = member_http_client
    response = client.post(
        "/api/v1/members",
        json={
            "name": " Maria Silva ",
            "email": " MARIA@Example.COM ",
            "phone": "+55 (31) 99999-1234",
            "status": "active",
        },
    )
    assert response.status_code == 201
    assert response.json()["data"]["id"] == 1
    data = handlers["create"].handle.call_args.args[0]
    assert data.name == "Maria Silva"
    assert data.email == "maria@example.com"
    assert data.status == MemberStatus.ACTIVE
    assert "password" not in response.json()["data"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": " "},
        {"name": "a" * 121},
        {"email": "inválido"},
        {"email": None},
        {"phone": "abcdefg"},
        {"phone": "---"},
        {"status": "unknown"},
        {"status": None},
        {"is_admin": True},
        {"role": "admin"},
        {"password": "SenhaSegura123"},
    ],
)
def test_create_rejects_invalid_or_extra_fields(member_http_client, overrides):
    client, handlers, _ = member_http_client
    payload = {"name": "Maria", "email": "maria@example.com", **overrides}
    assert client.post("/api/v1/members", json=payload).status_code == 422
    handlers["create"].handle.assert_not_called()


def test_listing_passes_filters_and_pagination(member_http_client):
    client, handlers, _ = member_http_client
    response = client.get("/api/v1/members?page=2&page_size=10&status=inactive&q=%20Maria%20")
    assert response.status_code == 200
    assert response.json()["meta"]["total"] == 1
    handlers["list"].handle.assert_called_once_with(
        page=2, page_size=10, status=MemberStatus.INACTIVE, search="Maria"
    )


@pytest.mark.parametrize(
    "query", ["page=0", "page_size=0", "page_size=101", "status=other", "q=" + "a" * 121]
)
def test_invalid_listing_parameters_are_rejected(member_http_client, query):
    client, handlers, _ = member_http_client
    assert client.get("/api/v1/members?" + query).status_code == 422
    handlers["list"].handle.assert_not_called()


@pytest.mark.parametrize("member_id", ["0", "-1", "text", "9223372036854775808"])
def test_invalid_identifiers_are_rejected(member_http_client, member_id):
    client, handlers, _ = member_http_client
    assert client.get("/api/v1/members/" + member_id).status_code == 422
    handlers["get"].handle.assert_not_called()


def test_omitted_phone_is_preserved_by_update(member_http_client):
    client, handlers, _ = member_http_client
    assert client.patch("/api/v1/members/1", json={"name": "Maria"}).status_code == 200
    data = handlers["update"].handle.call_args.args[1]
    assert not data.update_phone


def test_explicit_phone_null_removes_phone(member_http_client):
    client, handlers, _ = member_http_client
    assert client.patch("/api/v1/members/1", json={"phone": None}).status_code == 200
    data = handlers["update"].handle.call_args.args[1]
    assert data.update_phone and data.phone is None


def test_status_can_be_updated_to_inactive(member_http_client):
    client, handlers, _ = member_http_client
    assert client.patch("/api/v1/members/1", json={"status": "inactive"}).status_code == 200
    assert handlers["update"].handle.call_args.args[1].status == MemberStatus.INACTIVE


@pytest.mark.parametrize("payload", [{}, {"name": None}, {"email": None}, {"status": None}])
def test_invalid_partial_updates_are_rejected(member_http_client, payload):
    client, handlers, _ = member_http_client
    assert client.patch("/api/v1/members/1", json=payload).status_code == 422
    handlers["update"].handle.assert_not_called()


@pytest.mark.parametrize("method", ["GET", "PATCH", "DELETE"])
def test_missing_member_returns_404(member_http_client, method):
    client, handlers, _ = member_http_client
    key = {"GET": "get", "PATCH": "update", "DELETE": "delete"}[method]
    handlers[key].handle.side_effect = MemberNotFoundError
    response = client.request(method, "/api/v1/members/100", json={"name": "Maria"})
    assert response.status_code == 404


@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_duplicate_email_returns_409(member_http_client, method):
    client, handlers, _ = member_http_client
    key = "create" if method == "POST" else "update"
    handlers[key].handle.side_effect = DuplicateMemberEmailError
    path = "/api/v1/members" if method == "POST" else "/api/v1/members/1"
    response = client.request(method, path, json={"name": "Maria", "email": "maria@example.com"})
    assert response.status_code == 409
    assert "email" in response.json()["errors"]


def test_admin_can_delete_member(member_http_client):
    client, handlers, _ = member_http_client
    response = client.delete("/api/v1/members/1")
    assert response.status_code == 204
    assert response.content == b""
    handlers["delete"].handle.assert_called_once_with(1)


def test_swagger_protects_all_member_operations(member_http_client):
    client, _, _ = member_http_client
    spec = client.get("/openapi.json").json()
    for path in ["/api/v1/members", "/api/v1/members/{member_id}"]:
        for operation in spec["paths"][path].values():
            assert {"BearerAuth": []} in operation["security"]
            assert "403" in operation["responses"]
