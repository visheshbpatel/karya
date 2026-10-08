from fastapi import FastAPI
from sqlalchemy import Integer, Boolean, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from pydantic import BaseModel


app = FastAPI(title="Karya")

DATABASE_URL = "sqlite:///./karya.db"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass

class Todo(Base):
    __tablename__ = "todos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task: Mapped[str] = mapped_column(String)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)

Base.metadata.create_all(engine)


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


@app.get("/")
def home():
    return {"message": "Welcome to Karya"}


@app.get("/todos", response_model=list[TodoReturn])
def get_todos():

    with SessionLocal() as db:
        result = db.execute(select(Todo))
        todos = result.scalars().all()

    return todos


@app.get("/todo/{todo_id}", response_model=TodoReturn)
def get_todo(todo_id: int):

    with SessionLocal() as db:
        result = db.execute(
            select(Todo).where(Todo.id == todo_id)
        )
        todo = result.scalar_one_or_none()

    if todo is None:
            return {"message": "Task not found"}

    return todo


@app.post("/todo", response_model=TodoReturn)
def post_todo(todo: TodoCreate):

    new_todo = Todo (
                task = todo.task,
                completed= False
            )

    with SessionLocal() as db:
        db.add(new_todo)
        db.commit()
        db.refresh(new_todo)

    return new_todo
    

@app.put("/todo/{todo_id}")
def update_todo(todo_id: int, todo_data: TodoUpdate):

    with SessionLocal() as db:
        result = db.execute(
            select(Todo).where(Todo.id == todo_id)
        )

        todo = result.scalar_one_or_none()

        if todo is None:
            return {"message": "Todo not found"}

        todo.task = todo_data.task
        todo.completed = todo_data.completed

        db.commit()
        db.refresh(todo)

        return {"message": "Todo updated", "todo": todo}

    


@app.delete("/todo/{todo_id}")
def del_todo(todo_id: int):

    with SessionLocal() as db:
            result = db.execute(
                select(Todo).where(Todo.id == todo_id)
            )
    
            todo = result.scalar_one_or_none()
    
            if todo is None:
                return {"message": "Todo not found"}

            
    
            db.delete(todo)
            db.commit()
    
            return {"message": f'Task {todo.task} removed!'}