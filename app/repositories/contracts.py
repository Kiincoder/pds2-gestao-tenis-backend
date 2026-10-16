from datetime import datetime
from typing import Protocol

from app.data.members import CreateMemberData, UpdateMemberData
from app.domain.entities import (
    AuthenticatedSession,
    Member,
    MemberPage,
    MemberStatus,
    User,
    UserCredentials,
)


class UserRepository(Protocol):
    def create(self, *, name: str, email: str, password_hash: str) -> User: ...

    def find_credentials_by_email(self, email: str) -> UserCredentials | None: ...

    def promote_administrator(self, email: str) -> User | None: ...


class SessionRepository(Protocol):
    def create(self, *, user_id: int, token_hash: str, expires_at: datetime) -> None: ...

    def find_active(self, token_hash: str, now: datetime) -> AuthenticatedSession | None: ...

    def revoke(self, token_hash: str, now: datetime) -> bool: ...


class MemberRepository(Protocol):
    def create(self, data: CreateMemberData) -> Member: ...

    def get(self, member_id: int) -> Member | None: ...

    def list(
        self,
        *,
        page: int,
        page_size: int,
        status: MemberStatus | None,
        search: str | None,
    ) -> MemberPage: ...

    def update(self, member_id: int, data: UpdateMemberData) -> Member | None: ...

    def delete(self, member_id: int) -> bool: ...
