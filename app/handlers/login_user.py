from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app.core.tokens import TokenService
from app.data.login_user import LoginUserData
from app.domain.entities import LoginResult
from app.domain.exceptions import InvalidCredentialsError
from app.repositories.contracts import SessionRepository, UserRepository


class CredentialVerifier(Protocol):
    def verify(self, password: str, password_hash: str | None) -> bool: ...


class LoginUserHandler:
    def __init__(
        self,
        users: UserRepository,
        sessions: SessionRepository,
        verifier: CredentialVerifier,
        tokens: TokenService,
        ttl: timedelta,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        if ttl <= timedelta(0):
            raise ValueError("A duração da sessão deve ser positiva.")
        self.users = users
        self.sessions = sessions
        self.verifier = verifier
        self.tokens = tokens
        self.ttl = ttl
        self.clock = clock

    def handle(self, data: LoginUserData) -> LoginResult:
        credentials = self.users.find_credentials_by_email(data.email)
        password_hash = credentials.password_hash if credentials is not None else None
        verified = self.verifier.verify(data.password, password_hash)
        if credentials is None or not verified:
            raise InvalidCredentialsError

        token = self.tokens.issue()
        expires_at = self.clock() + self.ttl
        self.sessions.create(
            user_id=credentials.user.id,
            token_hash=self.tokens.digest(token),
            expires_at=expires_at,
        )
        return LoginResult(credentials.user, token, expires_at)
