from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from routes import router


app = FastAPI(title="Karya")

app.include_router(router)


@app.get("/")
def home():
    return {"message": "Welcome to Karya"}



_frontend = Path(__file__).parent / "frontend"
if _frontend.is_dir():
    app.mount("/app", StaticFiles(directory=_frontend, html=True), name="frontend")
