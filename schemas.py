from pydantic import BaseModel


class TodoCreate(BaseModel):
    task: str
    priority: int = 0


class TodoReturn(BaseModel):
    id: int
    task: str
    completed: bool
    priority: int

    model_config={
        "from_attributes":True
    }


class TodoUpdate(BaseModel):
    task: str
    completed: bool
    priority: int = 0


class TodoPatch(BaseModel):
    task: str | None = None
    completed: bool | None = None
    priority: int | None = None
