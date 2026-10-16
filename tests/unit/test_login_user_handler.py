import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

from app.core.tokens import TokenService
from app.data.login_user import LoginUserData
from app.domain.entities import User, UserCredentials
from app.domain.exceptions import InvalidCredentialsError
from app.handlers.login_user import CredentialVerifier, LoginUserHandler
from app.repositories.contracts import SessionRepository, UserRepository


class LoginUserHandlerTests(unittest.TestCase):
    def setUp(self):
        self.users = Mock(spec=UserRepository)
        self.sessions = Mock(spec=SessionRepository)
        self.verifier = Mock(spec=CredentialVerifier)
        self.tokens = TokenService()
        self.now = datetime(2026, 10, 15, 12, tzinfo=UTC)
        self.user = User(1, "Maria", "maria@example.com", self.now)
        credentials = UserCredentials(self.user, "stored-hash")
        self.users.find_credentials_by_email.return_value = credentials
        self.handler = LoginUserHandler(
            self.users,
            self.sessions,
            self.verifier,
            self.tokens,
            ttl=timedelta(minutes=60),
            clock=lambda: self.now,
        )
        self.data = LoginUserData("maria@example.com", "SenhaSegura123")

    def test_success_persists_only_digest_and_expiration(self):
        self.verifier.verify.return_value = True
        result = self.handler.handle(self.data)
        self.assertEqual(result.user, self.user)
        self.assertEqual(result.expires_at, self.now + timedelta(hours=1))
        self.assertTrue(self.tokens.is_well_formed(result.access_token))
        self.verifier.verify.assert_called_once_with("SenhaSegura123", "stored-hash")
        self.sessions.create.assert_called_once_with(
            user_id=1,
            token_hash=self.tokens.digest(result.access_token),
            expires_at=result.expires_at,
        )
        self.assertNotIn(result.access_token, repr(result))

    def test_wrong_password_does_not_create_session(self):
        self.verifier.verify.return_value = False
        with self.assertRaises(InvalidCredentialsError):
            self.handler.handle(self.data)
        self.sessions.create.assert_not_called()

    def test_missing_user_still_checks_password_without_creating_session(self):
        self.users.find_credentials_by_email.return_value = None
        self.verifier.verify.return_value = False
        with self.assertRaises(InvalidCredentialsError):
            self.handler.handle(self.data)
        self.verifier.verify.assert_called_once_with("SenhaSegura123", None)
        self.sessions.create.assert_not_called()

    def test_missing_user_is_rejected_even_if_verifier_returns_true(self):
        self.users.find_credentials_by_email.return_value = None
        self.verifier.verify.return_value = True
        with self.assertRaises(InvalidCredentialsError):
            self.handler.handle(self.data)
        self.sessions.create.assert_not_called()

    def test_independent_logins_issue_different_tokens(self):
        self.verifier.verify.return_value = True
        first = self.handler.handle(self.data)
        second = self.handler.handle(self.data)
        self.assertNotEqual(first.access_token, second.access_token)

    def test_password_and_hash_are_hidden_in_representations(self):
        self.assertNotIn(self.data.password, repr(self.data))
        self.assertNotIn("stored-hash", repr(UserCredentials(self.user, "stored-hash")))

    def test_nonpositive_ttl_is_rejected(self):
        with self.assertRaises(ValueError):
            LoginUserHandler(
                self.users, self.sessions, self.verifier, self.tokens, ttl=timedelta(0)
            )
