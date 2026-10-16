from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class User:
    id: int
    name: str
    email: str
    created_at: datetime
    is_admin: bool = False


@dataclass(frozen=True, slots=True)
class UserCredentials:
    user: User
    password_hash: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    user: User
    token_hash: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class LoginResult:
    user: User
    access_token: str = field(repr=False)
    expires_at: datetime


class MemberStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


@dataclass(frozen=True, slots=True)
class Member:
    id: int
    name: str
    email: str
    phone: str | None
    status: MemberStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MemberPage:
    items: tuple[Member, ...]
    total: int
    page: int
    page_size: int
