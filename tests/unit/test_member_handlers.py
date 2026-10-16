import unittest
from datetime import UTC, datetime
from unittest.mock import Mock

from app.data.members import CreateMemberData, UpdateMemberData
from app.domain.entities import Member, MemberPage, MemberStatus
from app.domain.exceptions import DuplicateMemberEmailError, MemberNotFoundError
from app.handlers.members import (
    CreateMemberHandler,
    DeleteMemberHandler,
    GetMemberHandler,
    ListMembersHandler,
    UpdateMemberHandler,
)
from app.repositories.contracts import MemberRepository


class MemberHandlerTests(unittest.TestCase):
    def setUp(self):
        self.members = Mock(spec=MemberRepository)
        now = datetime(2026, 10, 15, tzinfo=UTC)
        self.member = Member(1, "Maria", "maria@example.com", None, MemberStatus.ACTIVE, now, now)

    def test_create_returns_persisted_member(self):
        data = CreateMemberData("Maria", "maria@example.com")
        self.members.create.return_value = self.member
        self.assertIs(CreateMemberHandler(self.members).handle(data), self.member)
        self.members.create.assert_called_once_with(data)

    def test_duplicate_creation_is_propagated_to_http_boundary(self):
        self.members.create.side_effect = DuplicateMemberEmailError
        with self.assertRaises(DuplicateMemberEmailError):
            CreateMemberHandler(self.members).handle(CreateMemberData("Maria", "maria@example.com"))

    def test_get_returns_existing_member(self):
        self.members.get.return_value = self.member
        self.assertIs(GetMemberHandler(self.members).handle(1), self.member)

    def test_get_missing_member_raises_not_found(self):
        self.members.get.return_value = None
        with self.assertRaises(MemberNotFoundError):
            GetMemberHandler(self.members).handle(100)

    def test_list_passes_filters_and_pagination(self):
        page = MemberPage((self.member,), 1, 2, 10)
        self.members.list.return_value = page
        result = ListMembersHandler(self.members).handle(
            page=2, page_size=10, status=MemberStatus.INACTIVE, search="Maria"
        )
        self.assertIs(result, page)
        self.members.list.assert_called_once_with(
            page=2, page_size=10, status=MemberStatus.INACTIVE, search="Maria"
        )

    def test_update_passes_explicit_phone_removal(self):
        data = UpdateMemberData(phone=None, update_phone=True)
        self.members.update.return_value = self.member
        self.assertIs(UpdateMemberHandler(self.members).handle(1, data), self.member)
        self.members.update.assert_called_once_with(1, data)

    def test_update_missing_member_raises_not_found(self):
        self.members.update.return_value = None
        with self.assertRaises(MemberNotFoundError):
            UpdateMemberHandler(self.members).handle(100, UpdateMemberData(name="Outro nome"))

    def test_duplicate_update_is_propagated(self):
        self.members.update.side_effect = DuplicateMemberEmailError
        with self.assertRaises(DuplicateMemberEmailError):
            UpdateMemberHandler(self.members).handle(1, UpdateMemberData(email="outra@example.com"))

    def test_delete_reports_success(self):
        self.members.delete.return_value = True
        self.assertIsNone(DeleteMemberHandler(self.members).handle(1))
        self.members.delete.assert_called_once_with(1)

    def test_delete_missing_member_raises_not_found(self):
        self.members.delete.return_value = False
        with self.assertRaises(MemberNotFoundError):
            DeleteMemberHandler(self.members).handle(100)
