from collections.abc import Callable
from datetime import UTC, datetime

from app.core.tokens import TokenService
from app.domain.entities import AuthenticatedSession
from app.domain.exceptions import AuthenticationError
from app.repositories.contracts import SessionRepository


class AuthenticateSessionHandler:
    def __init__(
        self,
        sessions: SessionRepository,
        tokens: TokenService,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.sessions = sessions
        self.tokens = tokens
        self.clock = clock

    def handle(self, token: str) -> AuthenticatedSession:
        if not self.tokens.is_well_formed(token):
            raise AuthenticationError
        session = self.sessions.find_active(self.tokens.digest(token), self.clock())
        if session is None:
            raise AuthenticationError
        return session
