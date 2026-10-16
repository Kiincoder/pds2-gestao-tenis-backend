import hashlib
import re
import secrets


class TokenService:
    """Tokens opacos com 256 bits de entropia; somente o digest é persistido."""

    def issue(self) -> str:
        return secrets.token_urlsafe(32)

    def is_well_formed(self, token: str) -> bool:
        return re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is not None

    def digest(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()
