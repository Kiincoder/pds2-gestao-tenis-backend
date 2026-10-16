import re
from datetime import datetime
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from app.domain.entities import MemberStatus


class MemberInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    @field_validator("name", "email", "phone", mode="before", check_fields=False)
    @classmethod
    def normalize_text(cls, value: object, info: ValidationInfo) -> object:
        if isinstance(value, str):
            value = value.strip()
            if info.field_name == "email":
                return value.lower()
            if info.field_name == "phone" and not value:
                return None
        return value

    @field_validator("phone", check_fields=False)
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is not None:
            digits = sum(char.isdigit() for char in value)
            if not re.fullmatch(r"\+?[0-9(). -]+", value) or not 7 <= digits <= 15:
                raise ValueError("Informe um telefone com 7 a 15 dígitos e formato válido.")
        return value


class CreateMemberRequest(MemberInput):
    name: str = Field(min_length=1, max_length=120, examples=["Maria Silva"])
    email: EmailStr = Field(max_length=254, examples=["maria@example.com"])
    phone: str | None = Field(default=None, max_length=32, examples=["+55 (31) 99999-1234"])
    status: MemberStatus = Field(default=MemberStatus.ACTIVE, strict=False)


class UpdateMemberRequest(MemberInput):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = Field(default=None, max_length=254)
    phone: str | None = Field(default=None, max_length=32)
    status: Annotated[MemberStatus, Field(strict=False)] | None = None

    @field_validator("name", "email", "status")
    @classmethod
    def reject_explicit_null(cls, value):
        if value is None:
            raise ValueError("Este campo não pode ser nulo quando informado.")
        return value

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Informe ao menos um campo para atualizar.")
        return self


class MemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    phone: str | None
    status: MemberStatus
    created_at: datetime
    updated_at: datetime


class MemberEnvelope(BaseModel):
    data: MemberResponse


class PaginationMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class MemberListResponse(BaseModel):
    data: list[MemberResponse]
    meta: PaginationMeta


class MemberErrorResponse(BaseModel):
    message: str
