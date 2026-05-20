from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chapter_versions import router as chapter_versions_router
from app.api.chapters import router as chapters_router
from app.api.characters import router as characters_router
from app.api.imports import router as imports_router
from app.api.outlines import router as outlines_router
from app.api.projects import router as projects_router
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
app.include_router(volumes_router)
app.include_router(chapters_router)
app.include_router(chapter_versions_router)
app.include_router(imports_router)
app.include_router(outlines_router)
app.include_router(characters_router)
