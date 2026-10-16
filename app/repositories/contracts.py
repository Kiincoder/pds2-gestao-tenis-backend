from datetime import datetime
from typing import Protocol

from app.domain.entities import AuthenticatedSession, User, UserCredentials


class UserRepository(Protocol):
    def create(self, *, name: str, email: str, password_hash: str) -> User: ...

    def find_credentials_by_email(self, email: str) -> UserCredentials | None: ...


class SessionRepository(Protocol):
    def create(self, *, user_id: int, token_hash: str, expires_at: datetime) -> None: ...

    def find_active(self, token_hash: str, now: datetime) -> AuthenticatedSession | None: ...

    def revoke(self, token_hash: str, now: datetime) -> bool: ...
