from collections.abc import Callable
from datetime import UTC, datetime

from app.domain.entities import AuthenticatedSession
from app.domain.exceptions import AuthenticationError
from app.repositories.contracts import SessionRepository


class LogoutUserHandler:
    def __init__(
        self,
        sessions: SessionRepository,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.sessions = sessions
        self.clock = clock

    def handle(self, session: AuthenticatedSession) -> None:
        if not self.sessions.revoke(session.token_hash, self.clock()):
            raise AuthenticationError
