from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.data.login_user import LoginUserData
from app.dependencies import get_current_session, get_login_handler, get_logout_handler
from app.domain.entities import AuthenticatedSession
from app.handlers.login_user import LoginUserHandler
from app.handlers.logout_user import LogoutUserHandler
from app.schemas.auth import (
    AuthenticationErrorResponse,
    LoginRequest,
    LoginResponse,
    RateLimitResponse,
    UserEnvelope,
    UserResponse,
    ValidationErrorResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["US02 — Autenticação"])
unauthorized_response = {
    "model": AuthenticationErrorResponse,
    "description": "Credenciais incorretas ou sessão ausente, inválida, expirada ou revogada",
    "headers": {"WWW-Authenticate": {"schema": {"type": "string"}, "example": "Bearer"}},
}


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Entrar na conta",
    description=(
        "Recebe e-mail e senha em JSON. Emite um token Bearer com duração padrão de 60 minutos. "
        "Use o token no cabeçalho Authorization das rotas protegidas. "
        "Limite padrão: 10 tentativas/minuto por IP, por processo."
    ),
    responses={
        401: unauthorized_response,
        422: {"model": ValidationErrorResponse, "description": "Dados inválidos"},
        429: {
            "model": RateLimitResponse,
            "description": "Limite de tentativas excedido",
            "headers": {"Retry-After": {"schema": {"type": "integer"}}},
        },
    },
)
def login(
    payload: LoginRequest,
    handler: Annotated[LoginUserHandler, Depends(get_login_handler)],
) -> LoginResponse:
    result = handler.handle(LoginUserData(str(payload.email), payload.password.get_secret_value()))
    return LoginResponse(
        access_token=result.access_token,
        expires_at=result.expires_at,
        user=UserResponse.model_validate(result.user),
    )


@router.get(
    "/me",
    response_model=UserEnvelope,
    summary="Consultar usuário autenticado",
    responses={401: unauthorized_response},
)
def me(session: Annotated[AuthenticatedSession, Depends(get_current_session)]) -> UserEnvelope:
    return UserEnvelope(data=UserResponse.model_validate(session.user))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Sair da sessão atual",
    description=(
        "Revoga no PostgreSQL o token utilizado nesta requisição. "
        "Outras sessões da mesma conta permanecem ativas."
    ),
    responses={401: unauthorized_response},
)
def logout(
    session: Annotated[AuthenticatedSession, Depends(get_current_session)],
    handler: Annotated[LogoutUserHandler, Depends(get_logout_handler)],
) -> Response:
    handler.handle(session)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
