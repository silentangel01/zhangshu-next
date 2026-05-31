import importlib
import logging
import os
import threading
import time
from pathlib import Path

# Skip .env loading in packaged/frozen mode (no .env file exists)
if not os.environ.get("ZHANGSHU_SKIP_DOTENV"):
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    load_dotenv()  # also try CWD

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Core routers (lightweight, loaded immediately)
from app.api.app_config import router as app_config_router
from app.api.backups import router as backups_router
from app.api.chapter_versions import router as chapter_versions_router
from app.api.chapters import router as chapters_router
from app.api.characters import router as characters_router
from app.api.clues import router as clues_router
from app.api.creative_reminders import router as creative_reminders_router
from app.api.exports import router as exports_router
from app.api.graphs import router as graphs_router
from app.api.imports import projects_import_router, router as imports_router
from app.api.knowledge import router as knowledge_router
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
from app.api.writing_stats import router as writing_stats_router
from app.api.versions import router as versions_router
from app.infrastructure.database import init_database, run_migrations

logger = logging.getLogger(__name__)

# Deferred routers: heavy dependencies (numpy, httpx, cryptography).
# Loaded in a background thread 1s after startup.
# Format: url_prefix → (module_path, attribute_name)
_DEFERRED_ROUTERS: dict[str, list[tuple[str, str]]] = {
    "/api/knowledge-embedding": [
        ("app.api.knowledge_embedding", "router"),
    ],
    "/api/knowledge-retrieval": [
        ("app.api.knowledge_retrieval", "router"),
    ],
    "/api/rag": [
        ("app.api.rag", "router"),
    ],
    "/api/cloud": [
        ("app.api.cloud", "router"),
        ("app.api.cloud", "projects_cloud_router"),
        ("app.api.cloud_sync", "router"),
    ],
}

_registered_deferred: set[str] = set()
_deferred_lock = threading.Lock()

app = FastAPI(title="Zhangshu Local API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5180",
        "http://127.0.0.1:5180",
        # Tauri desktop: frontend may be loaded from these protocols
        "tauri://localhost",
        "http://tauri.localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _register_deferred_router(prefix: str) -> bool:
    """Synchronously import and register one deferred router group. Thread-safe."""
    with _deferred_lock:
        if prefix in _registered_deferred:
            return True
        specs = _DEFERRED_ROUTERS.get(prefix)
        if not specs:
            return False
        try:
            for module_path, attr_name in specs:
                mod = importlib.import_module(module_path)
                app.include_router(getattr(mod, attr_name))
            _registered_deferred.add(prefix)
            logger.info("Deferred router registered: %s", prefix)
            return True
        except Exception as exc:
            logger.warning("Failed to load deferred router %s: %s", prefix, exc)
            return False


def _load_all_deferred_routers() -> None:
    """Load all deferred routers after a delay (runs in background thread)."""
    time.sleep(1)
    for prefix in _DEFERRED_ROUTERS:
        if prefix not in _registered_deferred:
            _register_deferred_router(prefix)


@app.middleware("http")
async def lazy_router_middleware(request: Request, call_next):
    """Fallback: if a request hits a deferred prefix before background loading
    completes, synchronously register the router on-demand."""
    path = request.url.path
    for prefix in _DEFERRED_ROUTERS:
        if prefix not in _registered_deferred and path.startswith(prefix):
            _register_deferred_router(prefix)
            break
    return await call_next(request)


@app.on_event("startup")
def on_startup():
    init_database()  # fast: create_all only
    threading.Thread(target=run_migrations, daemon=True).start()
    threading.Thread(target=_load_all_deferred_routers, daemon=True).start()


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
app.include_router(knowledge_router)
app.include_router(material_links_router)
app.include_router(graphs_router)
app.include_router(timeline_router)
app.include_router(app_config_router)
app.include_router(writing_stats_router)
app.include_router(versions_router)
# Deferred (loaded in background thread after 1s):
# - knowledge_embedding_router (numpy + httpx)
# - knowledge_retrieval_router (numpy + httpx)
# - rag_router (numpy + httpx + cryptography)
# - cloud_router + projects_cloud_router (httpx + cryptography)


def _mount_frontend_static() -> None:
    """Serve pre-built frontend static files (release/packaged mode only).

    In dev mode (``uvicorn --reload``), Vite serves the frontend and this
    function is a no-op.  In release/packaged mode, the entry point
    (``packaged_main.py`` or ``tauri_sidecar_main.py``) sets
    ``ZHANGSHU_FRONTEND_DIST`` explicitly.

    ``/assets/*`` is served via :class:`StaticFiles`.  All other non-API
    GET requests that do not match an existing route fall back to
    ``index.html`` (SPA routing) via a response-level middleware, so
    deferred routers registered later are never shadowed.
    """
    frontend_dist = os.environ.get("ZHANGSHU_FRONTEND_DIST")
    if frontend_dist is None:
        # Dev mode: Vite serves the frontend.
        return

    frontend_dist_path = Path(frontend_dist)

    index_path = frontend_dist_path / "index.html"
    if not index_path.exists():
        return

    assets_path = frontend_dist_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=assets_path), name="frontend-assets")

    # Serve individual static files (favicon, images, etc.) via middleware
    # rather than a catch-all route, so deferred routers always match first.
    _frontend_dist_path = frontend_dist_path
    _index_path = index_path

    @app.middleware("http")
    async def _spa_fallback_middleware(request: Request, call_next):
        # Serve static files that exist on disk (favicon.ico, etc.)
        path = request.url.path.lstrip("/")
        if path and not path.startswith(("api/", "docs", "openapi.json", "redoc", "health")):
            target = _frontend_dist_path / path
            if target.is_file():
                return FileResponse(target)

        response = await call_next(request)

        # SPA fallback: if no route matched (404) and it's a GET for a
        # non-API path, return index.html for client-side routing.
        if (
            response.status_code == 404
            and request.method == "GET"
            and not request.url.path.startswith("/api/")
        ):
            return FileResponse(_index_path)
        return response


_mount_frontend_static()
