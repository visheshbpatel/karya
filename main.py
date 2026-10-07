from fastapi import FastAPI

app = FastAPI(title="Karya")

todos = ["Fastapi","LangChain","LangGraph","n8n"]

@app.get("/")
def home():
    return {"message": "Welcome to Karya"}


@app.get("/todos")
def get_todos():
    return todos


@app.get("/todo/{todo_id}")
def get_todo(todo_id: int):

    if 0 <= todo_id < len(todos):
            return {"Message":todos[todo_id]}

    return {"message":"Task not found"}


@app.post("/todo")
def post_todo(todo: str):

    if todo:
        todos.append(todo)

        return {"message":'todo added'}

    return {"message":'first add todo'}


@app.delete("/todo/{todo_id}")
def del_todo(todo_id: int):

    if 0 <= todo_id < len(todos):
        todo = todos.pop(todo_id)

        return {"message": f'{todo} removed!'}

    return {"message": 'Todo not present'}