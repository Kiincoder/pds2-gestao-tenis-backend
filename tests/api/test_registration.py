import pytest

from app.domain.exceptions import DuplicateEmailError


def test_registration_returns_only_public_user_fields(http_client, registration_payload):
    client, handler = http_client
    response = client.post("/api/v1/auth/register", json=registration_payload)
    assert response.status_code == 201
    assert set(response.json()["data"]) == {"id", "name", "email", "created_at"}
    handler.handle.assert_called_once()


def test_email_and_name_are_normalized(http_client, registration_payload):
    client, handler = http_client
    registration_payload.update(email=" MARIA@Example.COM ", name=" Maria Silva ")
    assert client.post("/api/v1/auth/register", json=registration_payload).status_code == 201
    data = handler.handle.call_args.args[0]
    assert data.email == "maria@example.com"
    assert data.name == "Maria Silva"


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"name": None}, "name"),
        ({"name": "  "}, "name"),
        ({"name": "a" * 121}, "name"),
        ({"email": "invalido"}, "email"),
        ({"email": ["maria@example.com"]}, "email"),
        ({"password": None}, "password"),
        ({"password": "123", "password_confirmation": "123"}, "password"),
        ({"password": "senhasegura123"}, "password"),
        ({"password": "SenhaSemNumeros"}, "password"),
        ({"password": "A1" + "a" * 127}, "password"),
        ({"password_confirmation": "OutraSenha123"}, "password_confirmation"),
        ({"password_confirmation": None}, "password_confirmation"),
        ({"role": "admin"}, "role"),
        ({"is_admin": True}, "is_admin"),
        ({"id": 100}, "id"),
    ],
)
def test_invalid_inputs_are_rejected(http_client, registration_payload, overrides, field):
    client, handler = http_client
    registration_payload.update(overrides)
    response = client.post("/api/v1/auth/register", json=registration_payload)
    assert response.status_code == 422
    assert field in response.json()["errors"]
    assert "SenhaSegura123" not in response.text
    handler.handle.assert_not_called()


def test_duplicate_email_returns_validation_error(http_client, registration_payload):
    client, handler = http_client
    handler.handle.side_effect = DuplicateEmailError
    response = client.post("/api/v1/auth/register", json=registration_payload)
    assert response.status_code == 422
    assert "email" in response.json()["errors"]


def test_rate_limit_counts_invalid_requests(http_client):
    client, _ = http_client
    for _ in range(5):
        assert client.post("/api/v1/auth/register", json={}).status_code == 422
    response = client.post("/api/v1/auth/register", json={})
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_swagger_and_openapi_expose_registration(http_client):
    client, _ = http_client
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    operation = spec["paths"]["/api/v1/auth/register"]["post"]
    assert {"201", "422", "429"} <= operation["responses"].keys()
    assert "password" not in spec["components"]["schemas"]["UserResponse"]["properties"]


def test_unicode_password_longer_than_72_bytes_is_supported(http_client, registration_payload):
    client, handler = http_client
    password = "Áa1" + "á" * 40
    registration_payload.update(password=password, password_confirmation=password)
    assert client.post("/api/v1/auth/register", json=registration_payload).status_code == 201
    assert handler.handle.call_args.args[0].password == password


def test_password_spaces_are_not_trimmed(http_client, registration_payload):
    client, handler = http_client
    password = " SenhaSegura123 "
    registration_payload.update(password=password, password_confirmation=password)
    assert client.post("/api/v1/auth/register", json=registration_payload).status_code == 201
    assert handler.handle.call_args.args[0].password == password
