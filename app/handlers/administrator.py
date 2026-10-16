from app.domain.entities import AuthenticatedSession, User
from app.domain.exceptions import ForbiddenError, UserNotFoundError
from app.repositories.contracts import UserRepository


class RequireAdministratorHandler:
    def handle(self, session: AuthenticatedSession) -> User:
        if not session.user.is_admin:
            raise ForbiddenError
        return session.user


class PromoteAdministratorHandler:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    def handle(self, email: str) -> User:
        user = self.users.promote_administrator(email.strip().lower())
        if user is None:
            raise UserNotFoundError
        return user
