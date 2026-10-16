from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import UserModel
from app.domain.entities import User, UserCredentials
from app.domain.exceptions import DuplicateEmailError


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def find_credentials_by_email(self, email: str) -> UserCredentials | None:
        record = self.session.scalar(select(UserModel).where(UserModel.email == email))
        if record is None:
            return None
        return UserCredentials(
            User(record.id, record.name, record.email, record.created_at), record.password_hash
        )

    def create(self, *, name: str, email: str, password_hash: str) -> User:
        record = UserModel(name=name, email=email, password_hash=password_hash)
        try:
            self.session.add(record)
            self.session.flush()
            user = User(record.id, record.name, record.email, record.created_at)
            self.session.commit()
            return user
        except IntegrityError as error:
            self.session.rollback()
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if getattr(error.orig, "sqlstate", None) == "23505" and constraint == "uq_users_email":
                raise DuplicateEmailError from None
            raise
