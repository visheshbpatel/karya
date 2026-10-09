from pydantic import BaseModel


class TodoCreate(BaseModel):
    task: str


class TodoReturn(BaseModel):
    id: int
    task: str
    completed: bool

    model_config={
        "from_attributes":True
    }


class TodoUpdate(BaseModel):
    task: str
    completed: bool


class TodoPatch(BaseModel):
    task: str | None = None
    completed: bool | None = None
