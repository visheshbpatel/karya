from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from schemas import TodoCreate, TodoUpdate, TodoReturn, TodoPatch
from database import get_db, Todo


router = APIRouter()


@router.get("/todos", response_model=list[TodoReturn])
def get_todos(db: Session = Depends(get_db)):

    result = db.execute(select(Todo))
    todos = result.scalars().all()

    return todos


@router.get("/todo/{todo_id}", response_model=TodoReturn)
def get_todo(todo_id: int, db: Session = Depends(get_db)):

    result = db.execute(
        select(Todo).where(Todo.id == todo_id)
    )
    todo = result.scalar_one_or_none()

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    return todo


@router.post("/todo", response_model=TodoReturn, status_code=201)
def post_todo(todo: TodoCreate, db: Session = Depends(get_db)):

    new_todo = Todo (
                task = todo.task,
                completed= False,
                priority= todo.priority
            )

    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)

    return new_todo
    

@router.put("/todo/{todo_id}", response_model=TodoReturn)
def update_todo(todo_id: int, todo_data: TodoUpdate, db: Session = Depends(get_db)):


    result = db.execute(
        select(Todo).where(Todo.id == todo_id)
    )

    todo = result.scalar_one_or_none()

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    todo.task = todo_data.task
    todo.completed = todo_data.completed
    todo.priority = todo_data.priority

    db.commit()
    db.refresh(todo)

    return todo


@router.delete("/todo/{todo_id}", status_code=204)
def del_todo(todo_id: int, db: Session = Depends(get_db)):


    result = db.execute(
        select(Todo).where(Todo.id == todo_id)
    )

    todo = result.scalar_one_or_none()

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    db.delete(todo)
    db.commit()


@router.patch("/todo/{todo_id}", response_model=TodoReturn)
def patch_todo(todo_id:int, todo_data: TodoPatch, db: Session = Depends(get_db)):
    result = db.execute(
        select(Todo).where(Todo.id == todo_id)
    )

    todo = result.scalar_one_or_none()

    if todo is None:
        raise HTTPException(status_code=404, detail="Todo not found")

    update_data = todo_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(todo, field, value)

    db.commit()
    db.refresh(todo)

    return todo