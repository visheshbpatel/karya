from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from schemas import TodoCreate, TodoUpdate, TodoReturn
from database import get_db, Todo


app = FastAPI(title="Karya")


@app.get("/")
def home():
    return {"message": "Welcome to Karya"}


@app.get("/todos", response_model=list[TodoReturn])
def get_todos(db: Session = Depends(get_db)):

    result = db.execute(select(Todo))
    todos = result.scalars().all()

    return todos


@app.get("/todo/{todo_id}", response_model=TodoReturn)
def get_todo(todo_id: int, db: Session = Depends(get_db)):

    result = db.execute(
        select(Todo).where(Todo.id == todo_id)
    )
    todo = result.scalar_one_or_none()

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    return todo


@app.post("/todo", response_model=TodoReturn)
def post_todo(todo: TodoCreate, db: Session = Depends(get_db)):

    new_todo = Todo (
                task = todo.task,
                completed= False
            )

    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)

    return new_todo
    

@app.put("/todo/{todo_id}")
def update_todo(todo_id: int, todo_data: TodoUpdate, db: Session = Depends(get_db)):


    result = db.execute(
        select(Todo).where(Todo.id == todo_id)
    )

    todo = result.scalar_one_or_none()

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    todo.task = todo_data.task
    todo.completed = todo_data.completed

    db.commit()
    db.refresh(todo)

    return {"message": "Todo updated", "todo": todo}


@app.delete("/todo/{todo_id}")
def del_todo(todo_id: int, db: Session = Depends(get_db)):


    result = db.execute(
        select(Todo).where(Todo.id == todo_id)
    )

    todo = result.scalar_one_or_none()

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    db.delete(todo)
    db.commit()

    return {"message": f'Task {todo.task} removed!'}

