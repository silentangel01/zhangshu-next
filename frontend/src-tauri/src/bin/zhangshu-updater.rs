//! Zhangshu Updater Helper
//!
//! A standalone helper binary that:
//! 1. Waits for the main application process to exit.
//! 2. Runs the Inno Setup installer in silent mode to perform an in-place update.
//! 3. Logs the installer exit code.
//! 4. Restarts the application if the installation succeeded.
//!
//! This binary does NOT perform any network operations, manifest parsing,
//! version comparison, or hash verification. All of those are done by the
//! main application before spawning this helper.
//!
//! Arguments:
//!   --installer <path>   Path to the verified Inno Setup installer
//!   --app-exe <path>     Path to the main application executable
//!   --parent-pid <pid>   PID of the main application process to wait for
//!   --silent             Run the installer in silent mode (default for MVP)

use std::fs::OpenOptions;
use std::io::Write;
use std::path::PathBuf;
use std::process::Command;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[cfg(target_os = "windows")]
extern "system" {
    fn OpenProcess(
        dwDesiredAccess: u32,
        bInheritHandle: i32,
        dwProcessId: u32,
    ) -> *mut std::ffi::c_void;
    fn CloseHandle(hObject: *mut std::ffi::c_void) -> i32;
    fn WaitForSingleObject(hHandle: *mut std::ffi::c_void, dwMilliseconds: u32) -> u32;
}

struct Args {
    installer: PathBuf,
    app_exe: PathBuf,
    parent_pid: u32,
    silent: bool,
}

fn parse_args() -> Result<Args, String> {
    let args: Vec<String> = std::env::args().collect();
    let mut installer: Option<PathBuf> = None;
    let mut app_exe: Option<PathBuf> = None;
    let mut parent_pid: Option<u32> = None;
    let mut silent = false;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--installer" => {
                i += 1;
                installer = Some(PathBuf::from(
                    args.get(i).ok_or("--installer 缺少参数值")?,
                ));
            }
            "--app-exe" => {
                i += 1;
                app_exe = Some(PathBuf::from(
                    args.get(i).ok_or("--app-exe 缺少参数值")?,
                ));
            }
            "--parent-pid" => {
                i += 1;
                let pid_str = args.get(i).ok_or("--parent-pid 缺少参数值")?;
                parent_pid = Some(
                    pid_str
                        .parse::<u32>()
                        .map_err(|_| format!("--parent-pid 不是合法数字: {}", pid_str))?,
                );
            }
            "--silent" => {
                silent = true;
            }
            other => {
                return Err(format!("未知参数: {}", other));
            }
        }
        i += 1;
    }

    Ok(Args {
        installer: installer.ok_or("缺少 --installer 参数")?,
        app_exe: app_exe.ok_or("缺少 --app-exe 参数")?,
        parent_pid: parent_pid.ok_or("缺少 --parent-pid 参数")?,
        silent,
    })
}

/// Get the log file path: `%TEMP%\zhangshu-updater.log`.
fn get_log_path() -> PathBuf {
    let temp = std::env::temp_dir();
    temp.join("zhangshu-updater.log")
}

/// Append a message to the updater log file.
fn log(msg: &str) {
    let log_path = get_log_path();
    if let Ok(mut file) = OpenOptions::new()
        .create(true)
        .append(true)
        .open(&log_path)
    {
        let _ = writeln!(file, "[updater] {}", msg);
    }
    // Also write to stderr for debugging
    eprintln!("[zhangshu-updater] {}", msg);
}

/// Check if a Windows process with the given PID is still running.
#[cfg(target_os = "windows")]
fn is_process_alive(pid: u32) -> bool {
    const PROCESS_QUERY_LIMITED_INFORMATION: u32 = 0x1000;
    const SYNCHRONIZE: u32 = 0x00100000;
    const WAIT_TIMEOUT: u32 = 258;

    let rights = PROCESS_QUERY_LIMITED_INFORMATION | SYNCHRONIZE;
    let handle = unsafe { OpenProcess(rights, 0, pid) };
    if handle.is_null() {
        // Cannot open handle — process does not exist or access denied
        return false;
    }

    let result = unsafe { WaitForSingleObject(handle, 0) };
    unsafe { CloseHandle(handle) };

    // WAIT_OBJECT_0 = process has exited
    // WAIT_TIMEOUT  = process is still running
    result == WAIT_TIMEOUT
}

/// Fallback for non-Windows: use `tasklist` equivalent (not used in MVP).
#[cfg(not(target_os = "windows"))]
fn is_process_alive(_pid: u32) -> bool {
    false
}

/// Wait for the parent process to exit, polling every 500ms with a 120s timeout.
fn wait_for_parent_exit(pid: u32) {
    log(&format!("等待主程序退出 (PID={})...", pid));

    for _ in 0..240 {
        // 120 seconds max
        if !is_process_alive(pid) {
            log("主程序已退出");
            // Brief grace period for file handles to be released
            std::thread::sleep(std::time::Duration::from_millis(1000));
            return;
        }
        std::thread::sleep(std::time::Duration::from_millis(500));
    }

    log("警告: 主程序在 120 秒内未退出，继续尝试安装...");
}

fn main() {
    log("========================================");
    log("章枢更新工具启动");

    let args = match parse_args() {
        Ok(a) => a,
        Err(e) => {
            log(&format!("参数错误: {}", e));
            log("用法: zhangshu-updater --installer <path> --app-exe <path> --parent-pid <pid> [--silent]");
            std::process::exit(1);
        }
    };

    log(&format!("安装器路径: {}", args.installer.display()));
    log(&format!("应用程序路径: {}", args.app_exe.display()));
    log(&format!("父进程 PID: {}", args.parent_pid));
    log(&format!("静默模式: {}", args.silent));

    // Verify installer file exists
    if !args.installer.exists() {
        log(&format!(
            "错误: 安装器文件不存在: {}",
            args.installer.display()
        ));
        std::process::exit(1);
    }

    // Step 1: Wait for main application to exit
    wait_for_parent_exit(args.parent_pid);

    // Step 2: Run the installer
    let install_dir = args
        .app_exe
        .parent()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_default();

    log("正在运行安装程序...");

    let mut cmd = Command::new(&args.installer);

    if args.silent {
        cmd.arg("/VERYSILENT")
            .arg("/SUPPRESSMSGBOXES")
            .arg("/NORESTART");
    }

    if !install_dir.is_empty() {
        cmd.arg(format!("/DIR={}", install_dir));
    }

    #[cfg(target_os = "windows")]
    cmd.creation_flags(0); // Allow installer to show its own window if not silent

    let status = match cmd.status() {
        Ok(s) => s,
        Err(e) => {
            log(&format!("错误: 无法启动安装程序: {}", e));
            std::process::exit(1);
        }
    };

    let exit_code = status.code().unwrap_or(-1);
    log(&format!("安装程序退出码: {}", exit_code));

    // Inno Setup exit codes:
    // 0 = success
    // 1 = setup failed to initialize
    // 2+ = various error conditions
    if exit_code != 0 {
        log(&format!(
            "警告: 安装程序返回非零退出码 ({}), 安装可能未成功",
            exit_code
        ));
        // Do not restart app if install failed
        std::process::exit(exit_code);
    }

    // Step 3: Restart the application
    log("安装成功, 正在重启应用程序...");

    let mut restart_cmd = Command::new(&args.app_exe);
    #[cfg(target_os = "windows")]
    restart_cmd.creation_flags(0);

    match restart_cmd.spawn() {
        Ok(_) => {
            log("应用程序已成功启动");
        }
        Err(e) => {
            log(&format!("警告: 无法重启应用程序: {}", e));
            log("请手动启动章枢");
        }
    }

    log("更新工具完成");
}
