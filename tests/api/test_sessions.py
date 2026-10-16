from datetime import UTC, datetime

import pytest

from app.dependencies import get_current_session, get_session
from app.domain.entities import AuthenticatedSession, User
from app.domain.exceptions import AuthenticationError, InvalidCredentialsError


def test_login_returns_token_and_only_public_user_data(auth_http_client):
    client, login_handler, _, _ = auth_http_client
    response = client.post(
        "/api/v1/auth/login", json={"email": "maria@example.com", "password": "SenhaSegura123"}
    )
    assert response.status_code == 200
    assert response.json()["access_token"] == login_handler.handle.return_value.access_token
    assert response.json()["token_type"] == "bearer"
    assert "expires_at" in response.json()
    assert set(response.json()["user"]) == {"id", "name", "email", "created_at"}
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["Pragma"] == "no-cache"


def test_login_normalizes_email_but_preserves_password(auth_http_client):
    client, login_handler, _, _ = auth_http_client
    response = client.post(
        "/api/v1/auth/login", json={"email": " MARIA@Example.COM ", "password": " SenhaSegura123 "}
    )
    assert response.status_code == 200
    data = login_handler.handle.call_args.args[0]
    assert data.email == "maria@example.com"
    assert data.password == " SenhaSegura123 "


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": "invalid", "password": "SenhaSegura123"},
        {"email": "maria@example.com"},
        {"email": "maria@example.com", "password": ""},
        {"email": "maria@example.com", "password": "a" * 129},
        {"email": "maria@example.com", "password": ["SenhaSegura123"]},
        {"email": "maria@example.com", "password": "SenhaSegura123", "role": "admin"},
    ],
)
def test_login_validation_does_not_expose_password(auth_http_client, payload):
    client, handler, _, _ = auth_http_client
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 422
    assert "SenhaSegura123" not in response.text
    assert response.headers["Cache-Control"] == "no-store"
    handler.handle.assert_not_called()


def test_incorrect_credentials_return_generic_401(auth_http_client):
    client, handler, _, _ = auth_http_client
    handler.handle.side_effect = InvalidCredentialsError
    response = client.post(
        "/api/v1/auth/login", json={"email": "maria@example.com", "password": "SenhaIncorreta"}
    )
    assert response.status_code == 401
    assert response.json() == {"message": "E-mail ou senha inválidos."}
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["Cache-Control"] == "no-store"


def test_login_is_limited_independently_from_registration(auth_http_client):
    client, _, _, _ = auth_http_client
    for _ in range(10):
        assert client.post("/api/v1/auth/login", json={}).status_code == 422
    response = client.post("/api/v1/auth/login", json={})
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0
    assert response.headers["Cache-Control"] == "no-store"
    assert client.post("/api/v1/auth/register", json={}).status_code == 422


@pytest.mark.parametrize("path", ["/me", "/logout"])
@pytest.mark.parametrize("authorization", [None, "Basic abc", "Bearer", "Bearer short"])
def test_protected_routes_reject_missing_or_malformed_token(auth_http_client, path, authorization):
    client, _, logout_handler, application = auth_http_client
    # A sessão só seria consultada para um token com formato válido.
    application.dependency_overrides[get_session] = lambda: None
    headers = {"Authorization": authorization} if authorization else {}
    method = client.get if path == "/me" else client.post
    response = method("/api/v1/auth" + path, headers=headers)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["Cache-Control"] == "no-store"
    logout_handler.handle.assert_not_called()


def test_current_user_uses_authenticated_context(auth_http_client):
    client, _, _, application = auth_http_client
    user = User(1, "Maria", "maria@example.com", datetime.now(UTC))
    context = AuthenticatedSession(user, "hash")
    application.dependency_overrides[get_current_session] = lambda: context
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "maria@example.com"
    assert "token_hash" not in response.text


def test_logout_returns_empty_204(auth_http_client):
    client, _, logout_handler, application = auth_http_client
    context = AuthenticatedSession(User(1, "Maria", "maria@example.com", datetime.now(UTC)), "hash")
    application.dependency_overrides[get_current_session] = lambda: context
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    assert response.content == b""
    logout_handler.handle.assert_called_once_with(context)


def test_revocation_race_returns_401(auth_http_client):
    client, _, logout_handler, application = auth_http_client
    context = AuthenticatedSession(User(1, "Maria", "maria@example.com", datetime.now(UTC)), "hash")
    application.dependency_overrides[get_current_session] = lambda: context
    logout_handler.handle.side_effect = AuthenticationError
    assert client.post("/api/v1/auth/logout").status_code == 401


def test_swagger_documents_bearer_and_new_routes(auth_http_client):
    client, _, _, _ = auth_http_client
    spec = client.get("/openapi.json").json()
    assert spec["components"]["securitySchemes"]["BearerAuth"]["scheme"] == "bearer"
    assert "401" in spec["paths"]["/api/v1/auth/login"]["post"]["responses"]
    for path, method in [("/me", "get"), ("/logout", "post")]:
        assert {"BearerAuth": []} in spec["paths"]["/api/v1/auth" + path][method]["security"]
