from fastapi import FastAPI
from routes import router


app = FastAPI(title="Karya")

app.include_router(router)


@app.get("/")
def home():
    return {"message": "Welcome to Karya"}

