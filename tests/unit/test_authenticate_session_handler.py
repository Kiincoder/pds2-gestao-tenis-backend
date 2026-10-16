import unittest
from datetime import UTC, datetime
from unittest.mock import Mock

from app.core.tokens import TokenService
from app.domain.entities import AuthenticatedSession, User
from app.domain.exceptions import AuthenticationError
from app.handlers.authenticate_session import AuthenticateSessionHandler
from app.repositories.contracts import SessionRepository


class AuthenticateSessionHandlerTests(unittest.TestCase):
    def setUp(self):
        self.sessions = Mock(spec=SessionRepository)
        self.tokens = TokenService()
        self.now = datetime(2026, 10, 15, 12, tzinfo=UTC)
        self.handler = AuthenticateSessionHandler(
            self.sessions, self.tokens, clock=lambda: self.now
        )

    def test_active_session_returns_authenticated_user(self):
        token = self.tokens.issue()
        context = AuthenticatedSession(
            User(1, "Maria", "maria@example.com", self.now), self.tokens.digest(token)
        )
        self.sessions.find_active.return_value = context
        self.assertIs(self.handler.handle(token), context)
        self.sessions.find_active.assert_called_once_with(self.tokens.digest(token), self.now)

    def test_absent_active_session_is_rejected(self):
        self.sessions.find_active.return_value = None
        with self.assertRaises(AuthenticationError):
            self.handler.handle(self.tokens.issue())

    def test_malformed_token_is_rejected_before_database_lookup(self):
        with self.assertRaises(AuthenticationError):
            self.handler.handle("invalid-token")
        self.sessions.find_active.assert_not_called()
