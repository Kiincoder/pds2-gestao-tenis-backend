from collections.abc import Iterator
from functools import cache
from typing import Annotated

from fastapi import Depends, Request
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.handlers.register_user import RegisterUserHandler
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
