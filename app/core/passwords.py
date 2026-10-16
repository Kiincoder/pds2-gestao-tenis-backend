import secrets

from pwdlib import PasswordHash
from pwdlib.exceptions import UnknownHashError


class PasswordVerifier:
    def __init__(self, hasher: PasswordHash) -> None:
        self.hasher = hasher
        self.dummy_hash = hasher.hash(secrets.token_urlsafe(32))

    def verify(self, password: str, password_hash: str | None) -> bool:
        # Contas inexistentes também executam uma verificação Argon2.
        try:
            matches = self.hasher.verify(password, password_hash or self.dummy_hash)
        except (UnknownHashError, ValueError):
            return False
        return matches and password_hash is not None
