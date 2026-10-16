from app.data.members import CreateMemberData, UpdateMemberData
from app.domain.entities import Member, MemberPage, MemberStatus
from app.domain.exceptions import MemberNotFoundError
from app.repositories.contracts import MemberRepository


class CreateMemberHandler:
    def __init__(self, members: MemberRepository) -> None:
        self.members = members

    def handle(self, data: CreateMemberData) -> Member:
        return self.members.create(data)


class GetMemberHandler:
    def __init__(self, members: MemberRepository) -> None:
        self.members = members

    def handle(self, member_id: int) -> Member:
        member = self.members.get(member_id)
        if member is None:
            raise MemberNotFoundError
        return member


class ListMembersHandler:
    def __init__(self, members: MemberRepository) -> None:
        self.members = members

    def handle(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        status: MemberStatus | None = None,
        search: str | None = None,
    ) -> MemberPage:
        return self.members.list(page=page, page_size=page_size, status=status, search=search)


class UpdateMemberHandler:
    def __init__(self, members: MemberRepository) -> None:
        self.members = members

    def handle(self, member_id: int, data: UpdateMemberData) -> Member:
        member = self.members.update(member_id, data)
        if member is None:
            raise MemberNotFoundError
        return member


class DeleteMemberHandler:
    def __init__(self, members: MemberRepository) -> None:
        self.members = members

    def handle(self, member_id: int) -> None:
        if not self.members.delete(member_id):
            raise MemberNotFoundError
