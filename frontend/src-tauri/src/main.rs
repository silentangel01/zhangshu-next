// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use tauri_plugin_shell::ShellExt;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let app_handle = app.handle().clone();

            // Prepare environment variables for sidecar
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

            // Ensure directories exist
            std::fs::create_dir_all(&data_dir).ok();
            std::fs::create_dir_all(&logs_dir).ok();

            // Launch sidecar with environment variables
            let sidecar = app_handle
                .shell()
                .sidecar("zhangshu-backend")
                .expect("failed to get sidecar");

            let (mut rx, child) = sidecar
                .envs(vec![
                    ("ZHANGSHU_BACKEND_HOST".to_string(), "127.0.0.1".to_string()),
                    ("ZHANGSHU_BACKEND_PORT".to_string(), "8765".to_string()),
                    ("ZHANGSHU_DATA_DIR".to_string(), data_dir.to_string_lossy().to_string()),
                    ("ZHANGSHU_LOG_DIR".to_string(), logs_dir.to_string_lossy().to_string()),
                    ("ZHANGSHU_DB_FILENAME".to_string(), "zhangshu.sqlite3".to_string()),
                ])
                .spawn()
                .expect("failed to spawn sidecar");

            // Store sidecar PID for cleanup
            app.manage(SidecarState { pid: child.pid() });

            // Spawn task to forward sidecar output to console
            tauri::async_runtime::spawn(async move {
                use tauri_plugin_shell::process::CommandEvent;
                while let Some(event) = rx.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            println!("[sidecar stdout] {}", String::from_utf8_lossy(&line));
                        }
                        CommandEvent::Stderr(line) => {
                            eprintln!("[sidecar stderr] {}", String::from_utf8_lossy(&line));
                        }
                        CommandEvent::Error(err) => {
                            eprintln!("[sidecar error] {}", err);
                        }
                        CommandEvent::Terminated(payload) => {
                            println!("[sidecar terminated] code: {:?}, signal: {:?}", payload.code, payload.signal);
                            break;
                        }
                        _ => {}
                    }
                }
            });

            Ok(())
        })
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                // Kill sidecar when window is destroyed
                let state = window.state::<SidecarState>();
                let pid = state.pid;
                // Use shell kill command as a fallback
                let _ = std::process::Command::new("taskkill")
                    .args(["/F", "/T", "/PID", &pid.to_string()])
                    .output();
            }
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

struct SidecarState {
    pid: u32,
}
