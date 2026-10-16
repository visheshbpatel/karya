
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from routes import router


app = FastAPI(title="Karya")

app.include_router(router)


@app.get("/", include_in_schema=False)
def home():
    return RedirectResponse(url="/app")


_frontend = Path(__file__).parent / "frontend"
if _frontend.is_dir():
    app.mount("/app", StaticFiles(directory=_frontend, html=True), name="frontend")
