from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.data.register_user import RegisterUserData
from app.dependencies import get_register_handler
from app.handlers.register_user import RegisterUserHandler
from app.schemas.auth import (
    RateLimitResponse,
    RegisterRequest,
    UserEnvelope,
    UserResponse,
    ValidationErrorResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["US01 — Cadastro"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=UserEnvelope,
    summary="Criar conta de usuário",
    description=(
        "Nome, e-mail e senha com confirmação. E-mail normalizado para minúsculas. "
        "Senha: 12 a 128 caracteres, com maiúscula, minúscula e número. "
        "Não faz login automático. Limite padrão: 5 tentativas/minuto por IP, por processo."
    ),
    responses={
        422: {
            "model": ValidationErrorResponse,
            "description": "Dados inválidos ou e-mail duplicado",
        },
        429: {
            "model": RateLimitResponse,
            "description": "Limite de requisições excedido",
            "headers": {"Retry-After": {"schema": {"type": "integer"}}},
        },
    },
)
def register(
    payload: RegisterRequest,
    handler: Annotated[RegisterUserHandler, Depends(get_register_handler)],
) -> UserEnvelope:
    user = handler.handle(
        RegisterUserData(payload.name, str(payload.email), payload.password.get_secret_value())
    )
    return UserEnvelope(data=UserResponse.model_validate(user))
