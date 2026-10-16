from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    ValidationInfo,
    field_validator,
)


class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    name: str = Field(min_length=1, max_length=120, examples=["Maria Silva"])
    email: EmailStr = Field(max_length=254, examples=["maria@example.com"])
    password: SecretStr = Field(min_length=12, max_length=128)
    password_confirmation: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("name", "email", mode="before")
    @classmethod
    def normalize_text(cls, value: object, info: ValidationInfo) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value.lower() if info.field_name == "email" else value
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: SecretStr) -> SecretStr:
        password = value.get_secret_value()
        if not (
            any(char.isupper() for char in password)
            and any(char.islower() for char in password)
            and any(char.isdigit() for char in password)
        ):
            raise ValueError("A senha deve conter letras maiúsculas, minúsculas e números.")
        return value

    @field_validator("password_confirmation")
    @classmethod
    def confirm_password(cls, value: SecretStr, info: ValidationInfo) -> SecretStr:
        password = info.data.get("password")
        if password is not None and value.get_secret_value() != password.get_secret_value():
            raise ValueError("A confirmação de senha não confere.")
        return value


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime


class UserEnvelope(BaseModel):
    data: UserResponse


class ValidationErrorResponse(BaseModel):
    message: str
    errors: dict[str, list[str]]


class RateLimitResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    email: EmailStr = Field(max_length=254, examples=["maria@example.com"])
    password: SecretStr = Field(min_length=1, max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class LoginResponse(BaseModel):
    access_token: str = Field(repr=False)
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user: UserResponse


class AuthenticationErrorResponse(BaseModel):
    message: str
