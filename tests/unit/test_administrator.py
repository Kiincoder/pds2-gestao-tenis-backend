import unittest
from datetime import UTC, datetime
from unittest.mock import Mock

from app.domain.entities import AuthenticatedSession, User
from app.domain.exceptions import ForbiddenError, UserNotFoundError
from app.handlers.administrator import PromoteAdministratorHandler, RequireAdministratorHandler
from app.repositories.contracts import UserRepository


class AdministratorTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 15, tzinfo=UTC)

    def test_ordinary_user_is_forbidden(self):
        user = User(1, "Maria", "maria@example.com", self.now)
        with self.assertRaises(ForbiddenError):
            RequireAdministratorHandler().handle(AuthenticatedSession(user, "hash"))

    def test_administrator_is_allowed(self):
        user = User(1, "Maria", "maria@example.com", self.now, is_admin=True)
        self.assertIs(
            RequireAdministratorHandler().handle(AuthenticatedSession(user, "hash")), user
        )

    def test_promotion_normalizes_existing_account_email(self):
        users = Mock(spec=UserRepository)
        user = User(1, "Maria", "maria@example.com", self.now, is_admin=True)
        users.promote_administrator.return_value = user
        self.assertIs(PromoteAdministratorHandler(users).handle(" MARIA@Example.COM "), user)
        users.promote_administrator.assert_called_once_with("maria@example.com")

    def test_unknown_account_cannot_be_promoted(self):
        users = Mock(spec=UserRepository)
        users.promote_administrator.return_value = None
        with self.assertRaises(UserNotFoundError):
            PromoteAdministratorHandler(users).handle("ausente@example.com")

    def test_user_is_not_an_administrator_by_default(self):
        self.assertFalse(User(1, "Maria", "maria@example.com", self.now).is_admin)
