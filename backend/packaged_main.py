from __future__ import annotations

import os
from pathlib import Path
import socket
import sys
import threading
import traceback
import webbrowser

import uvicorn


APP_NAME = "Zhangshu_MVP"
DEFAULT_PORT = 8765


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def get_bundle_dir() -> Path:
    return Path(getattr(sys, "_MEIPASS", get_base_dir())).resolve()


def prepare_environment() -> Path:
    base_dir = get_base_dir()
    data_dir = base_dir / "zhangshu_data"
    logs_dir = base_dir / "logs"
    data_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    bundle_dir = get_bundle_dir()
    frontend_dist = bundle_dir / "frontend" / "dist"
    if not frontend_dist.exists():
        frontend_dist = base_dir / "frontend" / "dist"

    os.environ.setdefault("ZHANGSHU_DATA_DIR", str(data_dir))
    os.environ.setdefault("ZHANGSHU_DB_FILENAME", "zhangshu.sqlite3")
    os.environ.setdefault("ZHANGSHU_FRONTEND_DIST", str(frontend_dist))
    return logs_dir


def find_free_port(start_port: int = DEFAULT_PORT, attempts: int = 20) -> int:
    for port in range(start_port, start_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free local port found for Zhangshu.")


def open_browser_later(url: str) -> None:
    timer = threading.Timer(1.0, lambda: webbrowser.open(url))
    timer.daemon = True
    timer.start()


def main() -> None:
    logs_dir = prepare_environment()
    port = find_free_port()
    url = f"http://127.0.0.1:{port}/"

    try:
        from app.main import app

        print(f"章枢 MVP 测试版已启动：{url}")
        print(f"本地数据目录：{os.environ['ZHANGSHU_DATA_DIR']}")
        open_browser_later(url)
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")
    except Exception:
        error_path = logs_dir / "startup_error.log"
        error_path.write_text(traceback.format_exc(), encoding="utf-8")
        print(f"启动失败，错误日志已写入：{error_path}")
        raise


if __name__ == "__main__":
    main()
