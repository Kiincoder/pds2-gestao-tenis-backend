from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class User:
    id: int
    name: str
    email: str
    created_at: datetime


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
