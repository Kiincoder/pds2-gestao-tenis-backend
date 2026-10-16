from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.data.members import CreateMemberData, UpdateMemberData
from app.db.models import MemberModel
from app.domain.entities import Member, MemberPage, MemberStatus
from app.domain.exceptions import DuplicateMemberEmailError


class SqlAlchemyMemberRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def _to_member(record: MemberModel) -> Member:
        return Member(
            record.id,
            record.name,
            record.email,
            record.phone,
            MemberStatus(record.status),
            record.created_at,
            record.updated_at,
        )

    def _save(self, record: MemberModel) -> Member:
        try:
            self.session.flush()
            self.session.refresh(record)
            member = self._to_member(record)
            self.session.commit()
            return member
        except IntegrityError as error:
            self.session.rollback()
            constraint = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if (
                getattr(error.orig, "sqlstate", None) == "23505"
                and constraint == "uq_members_email"
            ):
                raise DuplicateMemberEmailError from None
            raise

    def create(self, data: CreateMemberData) -> Member:
        record = MemberModel(
            name=data.name, email=data.email, phone=data.phone, status=data.status.value
        )
        self.session.add(record)
        return self._save(record)

    def get(self, member_id: int) -> Member | None:
        record = self.session.get(MemberModel, member_id)
        return self._to_member(record) if record is not None else None

    def list(
        self,
        *,
        page: int,
        page_size: int,
        status: MemberStatus | None,
        search: str | None,
    ) -> MemberPage:
        filters = []
        if status is not None:
            filters.append(MemberModel.status == status.value)
        if search:
            filters.append(
                or_(
                    MemberModel.name.icontains(search, autoescape=True),
                    MemberModel.email.icontains(search, autoescape=True),
                )
            )
        total = self.session.scalar(select(func.count()).select_from(MemberModel).where(*filters))
        records = self.session.scalars(
            select(MemberModel)
            .where(*filters)
            .order_by(MemberModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = tuple(self._to_member(record) for record in records)
        return MemberPage(items, total or 0, page, page_size)

    def update(self, member_id: int, data: UpdateMemberData) -> Member | None:
        record = self.session.scalar(
            select(MemberModel).where(MemberModel.id == member_id).with_for_update()
        )
        if record is None:
            return None
        if data.name is not None:
            record.name = data.name
        if data.email is not None:
            record.email = data.email
        if data.update_phone:
            record.phone = data.phone
        if data.status is not None:
            record.status = data.status.value
        return self._save(record)

    def delete(self, member_id: int) -> bool:
        deleted_id = self.session.scalar(
            delete(MemberModel).where(MemberModel.id == member_id).returning(MemberModel.id)
        )
        self.session.commit()
        return deleted_id is not None
