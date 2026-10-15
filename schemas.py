from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Priority = Literal["urgent", "important", "normal"]


class TodoCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    task: str = Field(min_length=1)
    priority: Priority = "normal"
    description: str | None = None
    due_date: date | None = None


class TodoReturn(BaseModel):
    id: int
    task: str
    completed: bool
    priority: Priority
    description: str | None = None
    due_date: date | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TodoUpdate(BaseModel):
    task: str
    completed: bool
    priority: Priority = "normal"
    description: str | None = None
    due_date: date | None = None


class TodoPatch(BaseModel):
    task: str | None = None
    completed: bool | None = None
    priority: Priority | None = None
    description: str | None = None
    due_date: date | None = None


class UserCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserReturn(BaseModel):
    id: int
    first_name: str
    last_name: str
    username: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EmailVerificationRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=5, max_length=255)
    otp: str = Field(pattern=r"^\d{6}$")


class ResendOTPRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=5, max_length=255)


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=5, max_length=255)


class VerifyResetOTPRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    email: str = Field(min_length=5, max_length=255)
    otp: str = Field(pattern=r"^\d{6}$")


class ResetPasswordRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    reset_token: str = Field(min_length=1, max_length=255)
    new_password: str = Field(min_length=8, max_length=128)
