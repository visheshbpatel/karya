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
