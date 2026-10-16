from dataclasses import dataclass

from app.domain.entities import MemberStatus


@dataclass(frozen=True, slots=True)
class CreateMemberData:
    name: str
    email: str
    phone: str | None = None
    status: MemberStatus = MemberStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class UpdateMemberData:
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    update_phone: bool = False
    status: MemberStatus | None = None
