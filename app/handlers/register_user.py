from typing import Protocol

from app.data.register_user import RegisterUserData
from app.domain.entities import User
from app.repositories.contracts import UserRepository


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...


class RegisterUserHandler:
    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self.users = users
        self.hasher = hasher

    def handle(self, data: RegisterUserData) -> User:
        password_hash = self.hasher.hash(data.password)
        return self.users.create(name=data.name, email=data.email, password_hash=password_hash)
