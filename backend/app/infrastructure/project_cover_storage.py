from __future__ import annotations

from pathlib import Path

from app.infrastructure.database import DATABASE_DIR


COVERS_ROOT = DATABASE_DIR / "project_covers"

ALLOWED_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAX_COVER_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


class CoverStorageError(Exception):
    pass


def _project_cover_dir(project_id: str) -> Path:
    return COVERS_ROOT / project_id


def _safe_relative_path(project_id: str, ext: str) -> str:
    return f"project_covers/{project_id}/cover{ext}"


def save_project_cover(
    project_id: str,
    content_type: str | None,
    content: bytes,
) -> str:
    if not content_type or content_type not in ALLOWED_CONTENT_TYPES:
        raise CoverStorageError("Unsupported image type")

    if len(content) > MAX_COVER_SIZE_BYTES:
        raise CoverStorageError("File too large")

    ext = ALLOWED_CONTENT_TYPES[content_type]
    cover_dir = _project_cover_dir(project_id)
    cover_dir.mkdir(parents=True, exist_ok=True)

    # Remove any existing cover files in this project's directory.
    for existing in cover_dir.iterdir():
        if existing.is_file():
            existing.unlink()

    target = cover_dir / f"cover{ext}"
    target.write_bytes(content)

    return _safe_relative_path(project_id, ext)


def delete_project_cover_files(relative_path: str | None) -> None:
    if not relative_path:
        return

    resolved = resolve_project_cover_path(relative_path)
    if resolved is None:
        return

    try:
        resolved.unlink(missing_ok=True)
        parent = resolved.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
    except OSError:
        pass


def resolve_project_cover_path(relative_path: str | None) -> Path | None:
    if not relative_path:
        return None

    candidate = (DATABASE_DIR / relative_path).resolve()

    # Ensure the resolved path is still under DATABASE_DIR.
    try:
        candidate.relative_to(DATABASE_DIR.resolve())
    except ValueError:
        return None

    if candidate.is_file():
        return candidate
    return None


def get_project_cover_media_type(path: Path) -> str:
    ext = path.suffix.lower()
    for content_type, known_ext in ALLOWED_CONTENT_TYPES.items():
        if ext == known_ext:
            return content_type
    return "application/octet-stream"
