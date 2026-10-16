from collections.abc import Iterator
from datetime import timedelta
from functools import cache
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.core.passwords import PasswordVerifier
from app.core.tokens import TokenService
from app.domain.entities import AuthenticatedSession
from app.domain.exceptions import AuthenticationError
from app.handlers.authenticate_session import AuthenticateSessionHandler
from app.handlers.login_user import LoginUserHandler
from app.handlers.logout_user import LogoutUserHandler
from app.handlers.register_user import RegisterUserHandler
from app.repositories.sqlalchemy_sessions import SqlAlchemySessionRepository
from app.repositories.sqlalchemy_users import SqlAlchemyUserRepository


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


@cache
def get_password_hasher() -> PasswordHash:
    return PasswordHash.recommended()


def get_register_handler(
    session: Annotated[Session, Depends(get_session)],
) -> RegisterUserHandler:
    return RegisterUserHandler(SqlAlchemyUserRepository(session), get_password_hasher())


bearer_auth = HTTPBearer(
    auto_error=False,
    scheme_name="BearerAuth",
    description="Cole o access_token retornado pelo login. A sessão expira e pode ser revogada.",
)


@cache
def get_password_verifier() -> PasswordVerifier:
    return PasswordVerifier(get_password_hasher())


def get_login_handler(
    request: Request,
    session: Annotated[Session, Depends(get_session)],
) -> LoginUserHandler:
    return LoginUserHandler(
        SqlAlchemyUserRepository(session),
        SqlAlchemySessionRepository(session),
        get_password_verifier(),
        TokenService(),
        ttl=timedelta(minutes=request.app.state.settings.access_token_ttl_minutes),
    )


def get_current_session(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_auth)],
    session: Annotated[Session, Depends(get_session)],
) -> AuthenticatedSession:
    if credentials is None:
        raise AuthenticationError
    return AuthenticateSessionHandler(
        SqlAlchemySessionRepository(session), TokenService()
    ).handle(credentials.credentials)


def get_logout_handler(
    session: Annotated[Session, Depends(get_session)],
) -> LogoutUserHandler:
    return LogoutUserHandler(SqlAlchemySessionRepository(session))
