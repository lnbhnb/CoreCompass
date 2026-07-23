from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from app.db import init_db
from app.routes import projects, validate, replan, notify, tasks, auth
from app.services import notify_service

app = FastAPI(title="CoreCompass")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()
    notify_service.start_scheduler()


@app.on_event("shutdown")
def shutdown():
    notify_service.stop_scheduler()


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(projects.router)
app.include_router(validate.router)
app.include_router(replan.router)
app.include_router(notify.router)
app.include_router(tasks.router)
app.include_router(auth.router)


frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=frontend_dir / "static"), name="static")

    @app.get("/")
    def index():
        return FileResponse(frontend_dir / "index.html")
