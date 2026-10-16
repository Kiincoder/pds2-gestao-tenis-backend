import unittest
from datetime import UTC, datetime
from unittest.mock import Mock

from app.data.register_user import RegisterUserData
from app.domain.entities import User
from app.domain.exceptions import DuplicateEmailError
from app.handlers.register_user import PasswordHasher, RegisterUserHandler
from app.repositories.contracts import UserRepository


class RegisterUserHandlerTests(unittest.TestCase):
    def setUp(self):
        self.repository = Mock(spec=UserRepository)
        self.hasher = Mock(spec=PasswordHasher)
        self.handler = RegisterUserHandler(self.repository, self.hasher)
        self.data = RegisterUserData("Maria", "maria@example.com", "SenhaSegura123")

    def test_only_hashed_password_is_sent_to_repository(self):
        user = User(1, "Maria", "maria@example.com", datetime.now(UTC))
        self.hasher.hash.return_value = "encoded-password"
        self.repository.create.return_value = user

        self.assertIs(self.handler.handle(self.data), user)
        self.hasher.hash.assert_called_once_with("SenhaSegura123")
        self.repository.create.assert_called_once_with(
            name="Maria", email="maria@example.com", password_hash="encoded-password"
        )

    def test_hashing_failure_does_not_persist_user(self):
        self.hasher.hash.side_effect = RuntimeError("Falha no hash")
        with self.assertRaises(RuntimeError):
            self.handler.handle(self.data)
        self.repository.create.assert_not_called()

    def test_duplicate_email_is_propagated_to_http_boundary(self):
        self.repository.create.side_effect = DuplicateEmailError
        with self.assertRaises(DuplicateEmailError):
            self.handler.handle(self.data)

    def test_password_is_hidden_in_data_representation(self):
        self.assertNotIn("SenhaSegura123", repr(self.data))
