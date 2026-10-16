from typing import Protocol

from app.domain.entities import User


class UserRepository(Protocol):
    def create(self, *, name: str, email: str, password_hash: str) -> User: ...
