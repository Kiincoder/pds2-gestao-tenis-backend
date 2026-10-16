from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import UserModel
from app.domain.entities import User
from app.domain.exceptions import DuplicateEmailError


class SqlAlchemyUserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

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
