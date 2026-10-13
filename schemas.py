from pydantic import BaseModel, Field, ConfigDict
from datetime import date



class TodoCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    task: str = Field(min_length=1)
    priority: int = 0
    description: str | None = None
    due_date: date | None = None


class TodoReturn(BaseModel):
    id: int
    task: str
    completed: bool
    priority: int
    description: str | None = None
    due_date: date | None = None

    model_config = {
        "from_attributes": True
    }


class TodoUpdate(BaseModel):
    task: str
    completed: bool
    priority: int = 0
    description: str | None = None
    due_date: date | None = None


class TodoPatch(BaseModel):
    task: str | None = None
    completed: bool | None = None
    priority: int | None = None
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
