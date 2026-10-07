from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="Karya")

todos = [
    {"id": 1, "task": "FastAPI", "completed": False},
    {"id": 2, "task": "LangChain", "completed": True},
    {"id": 3, "task": "LangGraph", "completed": True},
    {"id": 4, "task": "n8n", "completed": True}
]

next_id = 5


class TodoCreate(BaseModel):
    task: str


class TodoReturn(BaseModel):
    id: int
    task: str
    completed: bool

class TodoUpdate(BaseModel):
    task: str
    completed: bool


@app.get("/")
def home():
    return {"message": "Welcome to Karya"}


@app.get("/todos", response_model=list[TodoReturn])
def get_todos():
    return todos


@app.get("/todo/{todo_id}", response_model=TodoReturn)
def get_todo(todo_id: int):
    for todo in todos:
        if todo["id"] == todo_id:
            return todo

    return {"message": "Task not found"}


@app.post("/todo", response_model=TodoReturn)
def post_todo(todo: TodoCreate):
    global next_id

    todos.append({
        "id": next_id,
        "task": todo.task,
        "completed": False
    })

    next_id += 1

    return {"message": todo}

@app.put("/todo/{todo_id}")
def update_todo(todo_id: int, todo: TodoUpdate):
    for item in todos:
        if item["id"] == todo_id:
            item["task"] = todo.task
            item["completed"] = todo.completed

            return {"message": "Todo updated", "todo": item}

    return {"message": "Todo not found"}


@app.delete("/todo/{todo_id}")
def del_todo(todo_id: int):
    for todo in todos:
        if todo["id"] == todo_id:
            todos.remove(todo)
            return {"message": f'{todo["task"]} removed!'}

    return {"message": "Todo not present"}