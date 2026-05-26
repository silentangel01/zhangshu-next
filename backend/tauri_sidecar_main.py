from __future__ import annotations

import os
from pathlib import Path
import sys
import traceback

import uvicorn


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
DEFAULT_DB_FILENAME = "zhangshu.sqlite3"


def get_sidecar_base_dir() -> Path:
    """Get the base directory for the sidecar executable."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle
        return Path(sys.executable).resolve().parent
    # Running as script (development)
    return Path(__file__).resolve().parents[1]


def get_bundle_dir() -> Path:
    """Get the bundle directory (may differ from base for PyInstaller)."""
    return Path(getattr(sys, "_MEIPASS", get_sidecar_base_dir())).resolve()


def prepare_environment() -> Path:
    """Prepare data and log directories, set environment defaults."""
    base_dir = get_sidecar_base_dir()

    # Data directory: use env var or fallback to sidecar exe directory
    data_dir = Path(os.environ.get("ZHANGSHU_DATA_DIR", base_dir / "zhangshu_data"))
    logs_dir = Path(os.environ.get("ZHANGSHU_LOG_DIR", data_dir / "logs"))

    data_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Set environment defaults
    os.environ.setdefault("ZHANGSHU_DATA_DIR", str(data_dir))
    os.environ.setdefault("ZHANGSHU_DB_FILENAME", DEFAULT_DB_FILENAME)

    # Frontend dist: look in bundle first, then base directory
    bundle_dir = get_bundle_dir()
    frontend_dist = bundle_dir / "frontend" / "dist"
    if not frontend_dist.exists():
        frontend_dist = base_dir / "frontend" / "dist"
    os.environ.setdefault("ZHANGSHU_FRONTEND_DIST", str(frontend_dist))

    return logs_dir


def main() -> None:
    """Start the FastAPI sidecar for Tauri desktop shell."""
    logs_dir = prepare_environment()

    host = os.environ.get("ZHANGSHU_BACKEND_HOST", DEFAULT_HOST)
    port = int(os.environ.get("ZHANGSHU_BACKEND_PORT", DEFAULT_PORT))

    print(f"章枢 Tauri Sidecar 启动中...")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Data Dir: {os.environ.get('ZHANGSHU_DATA_DIR')}")

    try:
        from app.main import app

        print(f"FastAPI app loaded, starting uvicorn...")
        uvicorn.run(app, host=host, port=port, log_level="info")
    except OSError as e:
        # Port likely in use
        error_path = logs_dir / "startup_error.log"
        error_msg = f"端口 {port} 可能被占用或网络错误：{e}\n\n{traceback.format_exc()}"
        error_path.write_text(error_msg, encoding="utf-8")
        print(f"启动失败：{e}")
        print(f"错误日志已写入：{error_path}")
        sys.exit(1)
    except Exception:
        error_path = logs_dir / "startup_error.log"
        error_path.write_text(traceback.format_exc(), encoding="utf-8")
        print(f"启动失败，错误日志已写入：{error_path}")
        sys.exit(1)


if __name__ == "__main__":
    main()
