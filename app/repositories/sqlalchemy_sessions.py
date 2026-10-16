from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models import SessionModel, UserModel
from app.domain.entities import AuthenticatedSession, User


class SqlAlchemySessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, user_id: int, token_hash: str, expires_at: datetime) -> None:
        self.session.add(
            SessionModel(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        )
        self.session.commit()

    def find_active(self, token_hash: str, now: datetime) -> AuthenticatedSession | None:
        record = self.session.scalar(
            select(UserModel)
            .join(SessionModel, SessionModel.user_id == UserModel.id)
            .where(
                SessionModel.token_hash == token_hash,
                SessionModel.revoked_at.is_(None),
                SessionModel.expires_at > now,
            )
        )
        if record is None:
            return None
        return AuthenticatedSession(
            User(record.id, record.name, record.email, record.created_at), token_hash
        )

    def revoke(self, token_hash: str, now: datetime) -> bool:
        revoked_id = self.session.scalar(
            update(SessionModel)
            .where(
                SessionModel.token_hash == token_hash,
                SessionModel.revoked_at.is_(None),
                SessionModel.expires_at > now,
            )
            .values(revoked_at=now)
            .returning(SessionModel.id)
        )
        self.session.commit()
        return revoked_id is not None
