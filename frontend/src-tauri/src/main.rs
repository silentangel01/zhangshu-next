// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
use tauri::Manager;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x08000000;

/// State to track the backend child process PID for cleanup.
struct BackendState {
    pid: u32,
}

/// Resolve the backend executable path.
/// Checks both same directory (--onefile) and subdirectory (--onedir).
#[cfg_attr(debug_assertions, allow(dead_code))]
fn find_backend_exe() -> Option<std::path::PathBuf> {
    let exe = std::env::current_exe().ok()?;
    let dir = exe.parent()?;
    // --onedir mode: backend in zhangshu-backend/ subdirectory
    let backend_dir = dir.join("zhangshu-backend").join("zhangshu-backend.exe");
    if backend_dir.exists() {
        return Some(backend_dir);
    }
    // --onefile mode: backend in same directory
    let backend = dir.join("zhangshu-backend.exe");
    if backend.exists() {
        return Some(backend);
    }
    None
}

/// Resolve the frontend dist directory (same directory as this exe).
/// The release package includes a `frontend-dist/` folder next to the exe.
#[cfg_attr(debug_assertions, allow(dead_code))]
fn find_frontend_dist() -> Option<std::path::PathBuf> {
    let exe = std::env::current_exe().ok()?;
    let dir = exe.parent()?;
    let frontend_dist = dir.join("frontend-dist");
    if frontend_dist.join("index.html").exists() {
        Some(frontend_dist)
    } else {
        None
    }
}

/// Check if a TCP port is currently accepting connections.
#[cfg_attr(debug_assertions, allow(dead_code))]
fn is_port_in_use(port: u16) -> bool {
    use std::net::TcpStream;
    use std::time::Duration;
    TcpStream::connect_timeout(
        &format!("127.0.0.1:{}", port).parse().unwrap(),
        Duration::from_millis(300),
    )
    .is_ok()
}

/// Kill any process listening on the given port (Windows only).
/// Uses netstat + taskkill to clean up stale processes.
#[cfg_attr(debug_assertions, allow(dead_code))]
fn kill_process_on_port(port: u16) {
    // Fast path: if nothing is listening, skip expensive netstat
    if !is_port_in_use(port) {
        return;
    }

    #[cfg(target_os = "windows")]
    {
        let output = match Command::new("netstat").args(["-ano"]).output() {
            Ok(o) => o,
            Err(_) => return,
        };

        let text = String::from_utf8_lossy(&output.stdout);
        let listen_pattern = format!(":{} ", port);
        let mut pids: Vec<String> = Vec::new();

        for line in text.lines() {
            if line.contains("LISTENING") && line.contains(&listen_pattern) {
                if let Some(pid_str) = line.split_whitespace().last() {
                    let pid_str = pid_str.trim();
                    if pid_str.parse::<u32>().is_ok() && pid_str != "0" {
                        pids.push(pid_str.to_string());
                    }
                }
            }
        }

        pids.sort();
        pids.dedup();

        for pid in &pids {
            eprintln!(
                "[章枢] 端口 {} 被进程 PID={} 占用，正在清理...",
                port, pid
            );
            let _ = Command::new("taskkill")
                .args(["/F", "/T", "/PID", pid])
                .creation_flags(CREATE_NO_WINDOW)
                .output();
        }

        if !pids.is_empty() {
            // Poll until port is free instead of hardcoded 1s sleep
            for _ in 0..20 {
                if !is_port_in_use(port) {
                    break;
                }
                std::thread::sleep(std::time::Duration::from_millis(50));
            }
        }
    }
}

/// Poll the backend /health endpoint until it responds 200 or timeout.
#[cfg_attr(debug_assertions, allow(dead_code))]
fn wait_for_backend_ready(port: u16, timeout_secs: u64) -> bool {
    use std::io::{Read, Write};
    use std::net::TcpStream;
    use std::time::{Duration, Instant};

    let deadline = Instant::now() + Duration::from_secs(timeout_secs);

    while Instant::now() < deadline {
        if let Ok(mut stream) = TcpStream::connect_timeout(
            &format!("127.0.0.1:{}", port).parse().unwrap(),
            Duration::from_millis(200),
        ) {
            let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
            let _ = stream.set_write_timeout(Some(Duration::from_secs(2)));
            let request = format!(
                "GET /health HTTP/1.1\r\nHost: 127.0.0.1:{}\r\nConnection: close\r\n\r\n",
                port
            );
            if stream.write_all(request.as_bytes()).is_ok() {
                let mut response = String::new();
                let _ = stream.read_to_string(&mut response);
                if response.contains("200 OK") {
                    println!("[章枢] 后端已就绪 (port {})", port);
                    return true;
                }
            }
        }
        std::thread::sleep(Duration::from_millis(100));
    }

    eprintln!("[章枢] 后端启动超时 ({}s)", timeout_secs);
    false
}

/// Launch the backend process directly via std::process::Command.
/// This is more reliable than Tauri's sidecar mechanism in release builds.
#[cfg_attr(debug_assertions, allow(dead_code))]
fn launch_backend(
    exe_path: &std::path::Path,
    data_dir: &std::path::Path,
    logs_dir: &std::path::Path,
    frontend_dist: &std::path::Path,
    port: u16,
) -> std::io::Result<Child> {
    let port_str = port.to_string();

    // Cloud API base URL: respect existing env var, otherwise use default
    let cloud_api_base_url = std::env::var("ZHANGSHU_CLOUD_API_BASE_URL")
        .unwrap_or_else(|_| "https://api.emailbs.xin".to_string());

    let mut cmd = Command::new(exe_path);
    cmd.env("ZHANGSHU_BACKEND_HOST", "127.0.0.1")
        .env("ZHANGSHU_BACKEND_PORT", &port_str)
        .env("ZHANGSHU_DATA_DIR", data_dir)
        .env("ZHANGSHU_LOG_DIR", logs_dir)
        .env("ZHANGSHU_DB_FILENAME", "zhangshu.sqlite3")
        .env("ZHANGSHU_FRONTEND_DIST", frontend_dist)
        .env("ZHANGSHU_CLOUD_API_BASE_URL", &cloud_api_base_url)
        .env("PYTHONUNBUFFERED", "1")
        .stdout(std::process::Stdio::null())
        .stderr(std::process::Stdio::null());

    #[cfg(target_os = "windows")]
    cmd.creation_flags(CREATE_NO_WINDOW);

    cmd.spawn()
}

/// Spawn an async task that reads from a pipe and forwards to stdout/stderr.
#[allow(dead_code)]
fn forward_pipe_to_log(
    reader: impl std::io::Read + Send + 'static,
    prefix: &'static str,
) {
    use std::io::BufRead;
    tauri::async_runtime::spawn(async move {
        let reader = std::io::BufReader::new(reader);
        for line in reader.lines().map_while(Result::ok) {
            println!("[{}] {}", prefix, line);
        }
    });
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            // Second instance launched — focus existing window
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }
        }))
        .setup(|app| {
            // ── Release-only: launch bundled backend and navigate ──
            // In dev mode, the developer runs the backend separately
            // (uvicorn) and Tauri uses the Vite devUrl (localhost:5180).
            // In release mode, the backend exe is bundled next to the
            // desktop exe and serves the pre-built frontend static files.
            #[cfg(not(debug_assertions))]
            {
                let app_handle = app.handle().clone();
                let port: u16 = 8765;
                // ── 1. Clean up stale backend from previous sessions ──
                kill_process_on_port(port);

                // ── 2. Prepare data and log directories ──
                let data_dir = app_handle
                    .path()
                    .app_local_data_dir()
                    .expect("failed to get app local data dir")
                    .join("data");
                let logs_dir = app_handle
                    .path()
                    .app_local_data_dir()
                    .expect("failed to get app local data dir")
                    .join("logs");

                std::fs::create_dir_all(&data_dir).ok();
                std::fs::create_dir_all(&logs_dir).ok();

                // ── 3. Find and launch the backend exe ──
                let backend_exe = find_backend_exe().unwrap_or_else(|| {
                    eprintln!("[章枢] 找不到 zhangshu-backend.exe");
                    eprintln!(
                        "[章枢] 当前目录: {:?}",
                        std::env::current_exe().ok()
                    );
                    panic!(
                        "zhangshu-backend.exe not found next to zhangshu-desktop.exe"
                    );
                });

                // Find frontend dist (served by the backend)
                let frontend_dist = find_frontend_dist().unwrap_or_else(|| {
                    eprintln!("[章枢] 警告: frontend-dist/ 未找到，前端页面可能无法加载");
                    // Pass a non-existent path; the backend will skip static mounting
                    std::env::current_exe().unwrap().parent().unwrap().join("frontend-dist")
                });

                println!("[章枢] 启动后端: {:?}", backend_exe);
                println!("[章枢] 数据目录: {:?}", data_dir);
                println!("[章枢] 前端目录: {:?}", frontend_dist);

                let child = launch_backend(&backend_exe, &data_dir, &logs_dir, &frontend_dist, port)
                    .unwrap_or_else(|e| {
                        panic!("Failed to start zhangshu-backend.exe: {}", e);
                    });

                let pid = child.id();
                println!("[章枢] 后端进程 PID={}", pid);

                // Store PID for cleanup when window closes
                app.manage(BackendState { pid });

                // ── 4. Wait for backend to be ready before UI loads ──
                let ready = wait_for_backend_ready(port, 30);
                if !ready {
                    eprintln!("[章枢] 警告：后端未能在 30 秒内就绪");
                }

                // ── 5. Redirect webview to backend-served frontend ──
                let backend_url = format!("http://127.0.0.1:{}", port);
                let nav_handle = app.handle().clone();
                tauri::async_runtime::spawn(async move {
                    if let Some(window) = nav_handle.get_webview_window("main") {
                        println!("[章枢] 加载前端: {}", backend_url);
                        if let Err(e) = window.navigate(backend_url.parse().unwrap()) {
                            eprintln!("[章枢] 导航失败: {:?}", e);
                        }
                    }
                });
            }

            // In dev mode, store a dummy PID so BackendState is always managed
            #[cfg(debug_assertions)]
            app.manage(BackendState { pid: 0 });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state = window.state::<BackendState>();
                let pid = state.pid;
                if pid > 0 {
                    eprintln!("[章枢] 窗口关闭，清理后端 PID={}", pid);
                    let _ = std::process::Command::new("taskkill")
                        .args(["/F", "/T", "/PID", &pid.to_string()])
                        .creation_flags(CREATE_NO_WINDOW)
                        .output();
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
