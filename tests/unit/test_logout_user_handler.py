import unittest
from datetime import UTC, datetime
from unittest.mock import Mock

from app.domain.entities import AuthenticatedSession, User
from app.domain.exceptions import AuthenticationError
from app.handlers.logout_user import LogoutUserHandler
from app.repositories.contracts import SessionRepository


class LogoutUserHandlerTests(unittest.TestCase):
    def setUp(self):
        self.sessions = Mock(spec=SessionRepository)
        self.now = datetime(2026, 10, 15, 12, tzinfo=UTC)
        self.context = AuthenticatedSession(
            User(1, "Maria", "maria@example.com", self.now), "token-hash"
        )
        self.handler = LogoutUserHandler(self.sessions, clock=lambda: self.now)

    def test_only_current_token_is_revoked(self):
        self.sessions.revoke.return_value = True
        self.assertIsNone(self.handler.handle(self.context))
        self.sessions.revoke.assert_called_once_with("token-hash", self.now)

    def test_already_revoked_session_is_rejected(self):
        self.sessions.revoke.return_value = False
        with self.assertRaises(AuthenticationError):
            self.handler.handle(self.context)
