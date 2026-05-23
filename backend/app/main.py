import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.backups import router as backups_router
from app.api.chapter_versions import router as chapter_versions_router
from app.api.chapters import router as chapters_router
from app.api.characters import router as characters_router
from app.api.clues import router as clues_router
from app.api.creative_reminders import router as creative_reminders_router
from app.api.exports import router as exports_router
from app.api.graphs import router as graphs_router
from app.api.imports import projects_import_router, router as imports_router
from app.api.material_links import router as material_links_router
from app.api.outlines import router as outlines_router
from app.api.projects import router as projects_router
from app.api.project_covers import router as project_covers_router
from app.api.recovery import router as recovery_router
from app.api.review import router as review_router
from app.api.search import router as search_router
from app.api.timeline import router as timeline_router
from app.api.settings import router as settings_router
from app.api.volumes import router as volumes_router
from app.infrastructure.database import init_database

app = FastAPI(title="Zhangshu Local API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_database()


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "zhangshu-local-api"}


app.include_router(projects_router)
app.include_router(project_covers_router)
app.include_router(backups_router)
app.include_router(exports_router)
app.include_router(recovery_router)
app.include_router(review_router)
app.include_router(search_router)
app.include_router(volumes_router)
app.include_router(chapters_router)
app.include_router(chapter_versions_router)
app.include_router(projects_import_router)
app.include_router(imports_router)
app.include_router(outlines_router)
app.include_router(characters_router)
app.include_router(settings_router)
app.include_router(clues_router)
app.include_router(creative_reminders_router)
app.include_router(material_links_router)
app.include_router(graphs_router)
app.include_router(timeline_router)


def _mount_frontend_static() -> None:
    frontend_dist = os.environ.get("ZHANGSHU_FRONTEND_DIST")
    if frontend_dist is None:
        frontend_dist_path = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    else:
        frontend_dist_path = Path(frontend_dist)

    index_path = frontend_dist_path / "index.html"
    assets_path = frontend_dist_path / "assets"
    if not index_path.exists():
        return

    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=assets_path), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_frontend_app(full_path: str):
        if full_path.startswith(("api/", "docs", "openapi.json", "redoc", "health")):
            return FileResponse(index_path)
        target_path = frontend_dist_path / full_path
        if target_path.is_file():
            return FileResponse(target_path)
        return FileResponse(index_path)


_mount_frontend_static()
