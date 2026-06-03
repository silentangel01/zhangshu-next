//! Desktop updater module for Zhangshu.
//!
//! Handles: manifest fetching, version comparison, HTTPS download with SHA256
//! verification, cached installer management, and launching the updater helper.
//!
//! Security invariants:
//! - Only HTTPS URLs are accepted for manifest and download (localhost allowed in debug only).
//! - Manifest and installer URLs must belong to explicitly trusted host allowlists.
//! - The install command reads verified metadata from Rust-managed state/file,
//!   NOT from frontend-supplied paths.
//! - SHA256 is re-verified before the installer is executed.
//! - Download size is checked against manifest `sizeBytes` to prevent unbounded downloads.
//! - `minSupportedVersion` is enforced: versions below the minimum must download manually.

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::error::Error;
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::Mutex;
use std::time::Duration;
use tauri::{AppHandle, Manager, State};
use tokio::io::AsyncWriteExt;

#[cfg(target_os = "windows")]
use std::os::windows::process::CommandExt;

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x08000000;

// ── Host allowlists ──

/// Hosts allowed to serve the update manifest JSON.
const TRUSTED_MANIFEST_HOSTS: &[&str] = &[
    "updates.zhangshu.xin",
    "updates.emailbs.xin",
];

/// Hosts allowed to serve installer binaries.
const TRUSTED_INSTALLER_HOSTS: &[&str] = &[
    "downloads.zhangshu.xin",
    "downloads.emailbs.xin",
];

/// Trusted update server hosts for direct-connection fallback (union of manifest + installer).
const TRUSTED_UPDATE_HOSTS: &[&str] = &[
    "updates.zhangshu.xin",
    "downloads.zhangshu.xin",
    "updates.emailbs.xin",
    "downloads.emailbs.xin",
];

// ── Timeouts ──

/// Total request timeout for manifest fetches (seconds).
const MANIFEST_TIMEOUT_SECS: u64 = 30;

/// Total request timeout for installer downloads (seconds).
/// Large installers (~36 MB) need generous time on slower connections.
const INSTALLER_DOWNLOAD_TIMEOUT_SECS: u64 = 600;

/// TCP connect timeout shared by all request types (seconds).
const CONNECT_TIMEOUT_SECS: u64 = 8;

/// Maximum download size tolerance factor relative to manifest `sizeBytes`.
/// e.g. 1.1 allows up to 10% overshoot.
const DOWNLOAD_SIZE_TOLERANCE: f64 = 1.1;

// ── Manifest types (parsed from remote JSON) ──

#[derive(Debug, Deserialize)]
struct RemoteInstallerInfo {
    url: String,
    sha256: String,
    #[serde(rename = "sizeBytes")]
    size_bytes: u64,
}

#[derive(Debug, Deserialize)]
struct RemoteManifest {
    #[serde(rename = "schemaVersion")]
    schema_version: u32,
    #[allow(dead_code)]
    channel: String,
    platform: String,
    arch: String,
    version: String,
    #[serde(rename = "minSupportedVersion")]
    min_supported_version: String,
    #[serde(rename = "publishedAt")]
    published_at: String,
    installer: RemoteInstallerInfo,
    #[serde(rename = "releaseNotes")]
    release_notes: Option<Vec<String>>,
    #[allow(dead_code)]
    critical: Option<bool>,
}

// ── Response types (serialized to frontend) ──

#[derive(Debug, Clone, Serialize)]
pub struct InstallerInfo {
    pub url: String,
    pub sha256: String,
    #[serde(rename = "sizeBytes")]
    pub size_bytes: u64,
}

#[derive(Debug, Clone, Serialize)]
pub struct UpdateManifestResponse {
    #[serde(rename = "schemaVersion")]
    pub schema_version: u32,
    pub channel: String,
    pub platform: String,
    pub arch: String,
    pub version: String,
    #[serde(rename = "minSupportedVersion")]
    pub min_supported_version: String,
    #[serde(rename = "publishedAt")]
    pub published_at: String,
    pub installer: InstallerInfo,
    #[serde(rename = "releaseNotes")]
    pub release_notes: Vec<String>,
    pub critical: bool,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateCheckResult {
    pub has_update: bool,
    pub current_version: String,
    pub latest_version: String,
    pub manifest: Option<UpdateManifestResponse>,
    pub error: Option<String>,
    /// True when the current version is below the manifest's `minSupportedVersion`.
    /// The user must download the latest installer manually; auto-update is blocked.
    pub requires_manual_download: bool,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateDownloadResult {
    pub success: bool,
    pub version: String,
    pub cached_path: Option<String>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct UpdateInstallResult {
    pub success: bool,
    pub error: Option<String>,
}

// ── Internal verified metadata ──

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VerifiedUpdateMetadata {
    version: String,
    sha256: String,
    installer_path: String,
    size_bytes: u64,
}

/// Tauri managed state for in-memory verified update metadata.
pub struct VerifiedUpdateState {
    pub metadata: Mutex<Option<VerifiedUpdateMetadata>>,
}

// ── Helpers ──

/// Resolve the updater cache directory: `<app_local_data_dir>/updater_cache/`.
fn get_cache_dir(app: &AppHandle) -> Result<PathBuf, String> {
    let cache = app
        .path()
        .app_local_data_dir()
        .map_err(|e| format!("无法获取应用数据目录: {}", e))?
        .join("updater_cache");
    std::fs::create_dir_all(&cache)
        .map_err(|e| format!("无法创建缓存目录: {}", e))?;
    Ok(cache)
}

/// Validate that a URL is HTTPS.
///
/// In debug builds, `http://127.0.0.1` and `http://localhost` are allowed for
/// local testing. Production builds reject everything except HTTPS.
fn validate_https_url(url: &str) -> Result<(), String> {
    if url.starts_with("https://") {
        return Ok(());
    }
    #[cfg(debug_assertions)]
    {
        if url.starts_with("http://127.0.0.1") || url.starts_with("http://localhost") {
            return Ok(());
        }
    }
    Err(format!(
        "下载地址必须使用 HTTPS 协议: {}",
        url
    ))
}

/// Validate that a URL's host is in the manifest host allowlist.
fn validate_manifest_host(url: &str) -> Result<(), String> {
    let parsed = url::Url::parse(url).map_err(|e| format!("无效的 manifest URL: {}", e))?;
    let host = parsed
        .host_str()
        .ok_or_else(|| format!("manifest URL 缺少 host: {}", url))?;

    if TRUSTED_MANIFEST_HOSTS
        .iter()
        .any(|trusted| trusted.eq_ignore_ascii_case(host))
    {
        return Ok(());
    }

    #[cfg(debug_assertions)]
    {
        if host == "127.0.0.1" || host == "localhost" {
            return Ok(());
        }
    }

    Err(format!(
        "manifest 地址不在可信列表中: {}（可信: {}）",
        host,
        TRUSTED_MANIFEST_HOSTS.join(", ")
    ))
}

/// Validate that a URL's host is in the installer host allowlist.
fn validate_installer_host(url: &str) -> Result<(), String> {
    let parsed = url::Url::parse(url).map_err(|e| format!("无效的安装包 URL: {}", e))?;
    let host = parsed
        .host_str()
        .ok_or_else(|| format!("安装包 URL 缺少 host: {}", url))?;

    if TRUSTED_INSTALLER_HOSTS
        .iter()
        .any(|trusted| trusted.eq_ignore_ascii_case(host))
    {
        return Ok(());
    }

    #[cfg(debug_assertions)]
    {
        if host == "127.0.0.1" || host == "localhost" {
            return Ok(());
        }
    }

    Err(format!(
        "安装包地址不在可信列表中: {}（可信: {}）",
        host,
        TRUSTED_INSTALLER_HOSTS.join(", ")
    ))
}

/// Get the compile-time app version from Cargo.toml.
fn get_current_version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}

/// Parse a semver string, returning a user-friendly error on failure.
fn parse_semver(version: &str) -> Result<semver::Version, String> {
    semver::Version::parse(version)
        .map_err(|e| format!("无效版本号: {} ({})", version, e))
}

/// Check if a URL's host is in the trusted update hosts list.
///
/// This is used to determine whether direct connection fallback is allowed
/// when proxy connection fails.
fn is_trusted_update_host(url: &str) -> bool {
    if let Ok(parsed) = url::Url::parse(url) {
        if let Some(host) = parsed.host_str() {
            return TRUSTED_UPDATE_HOSTS
                .iter()
                .any(|trusted| trusted.eq_ignore_ascii_case(host));
        }
    }
    false
}

/// Build a reqwest HTTP client with the given timeout and optional proxy.
///
/// # Arguments
/// * `total_timeout` - Total request timeout (connect + transfer).
/// * `proxy_url` - If `Some(url)`, use this proxy (e.g. `http://127.0.0.1:7897`).
///                 If `None`, use reqwest defaults (reads `HTTPS_PROXY` etc. env vars).
fn build_update_client(
    total_timeout: Duration,
    proxy_url: Option<&str>,
) -> Result<reqwest::Client, String> {
    let mut builder = reqwest::Client::builder()
        .user_agent("Zhangshu-Updater/1.0")
        .connect_timeout(Duration::from_secs(CONNECT_TIMEOUT_SECS))
        .timeout(total_timeout);

    if let Some(url) = proxy_url {
        let proxy = reqwest::Proxy::all(url)
            .map_err(|e| format!("创建代理失败: {}", e))?;
        builder = builder.proxy(proxy);
    }

    builder.build().map_err(|e| format!("创建 HTTP 客户端失败: {}", e))
}

fn summarize_reqwest_error(error: &reqwest::Error) -> String {
    let category = if error.is_timeout() {
        "请求超时"
    } else if error.is_connect() {
        "连接失败"
    } else if error.is_builder() {
        "请求地址无效"
    } else if error.is_decode() {
        "响应解析失败"
    } else {
        "请求失败"
    };

    let mut chain = Vec::new();
    let mut source = error.source();
    while let Some(err) = source {
        chain.push(err.to_string());
        source = err.source();
    }

    if chain.is_empty() {
        return format!("{}: {}", category, error);
    }

    format!("{}: {}；底层原因: {}", category, error, chain.join(" -> "))
}

async fn try_get_with_client(
    label: &str,
    client: reqwest::Client,
    url: &str,
    require_success_status: bool,
) -> Result<reqwest::Response, String> {
    match client.get(url).send().await {
        Ok(response) => {
            let status = response.status();
            if require_success_status && !status.is_success() {
                Err(format!("{}: HTTP {}", label, status))
            } else {
                Ok(response)
            }
        }
        Err(error) => Err(format!("{}: {}", label, summarize_reqwest_error(&error))),
    }
}

fn short_digest(hash: &str) -> &str {
    let end = hash.len().min(16);
    &hash[..end]
}

/// Build a reqwest client that bypasses all proxy settings.
fn build_no_proxy_client(total_timeout: Duration) -> Result<reqwest::Client, String> {
    reqwest::Client::builder()
        .user_agent("Zhangshu-Updater/1.0")
        .connect_timeout(Duration::from_secs(CONNECT_TIMEOUT_SECS))
        .timeout(total_timeout)
        .no_proxy()
        .build()
        .map_err(|e| format!("创建直连 HTTP 客户端失败: {}", e))
}

/// Detect system proxy from Windows Internet Options registry.
///
/// Users often have proxy clients (Clash, V2Ray, etc.) that set system proxy
/// via Internet Options but do NOT set environment variables like HTTPS_PROXY.
/// reqwest only reads env vars by default, so we must detect the system proxy
/// ourselves and pass it to reqwest explicitly.
///
/// Returns `Some("http://host:port")` if a system proxy is enabled, `None` otherwise.
///
/// Handles the following `ProxyServer` formats:
/// - `127.0.0.1:7897` → `http://127.0.0.1:7897`
/// - `http://127.0.0.1:7897` → kept as-is
/// - `http=host:port;https=host:port` → picks `https` first, then `http`
///
/// Unsupported formats (SOCKS, PAC/WPAD) are detected and logged to stderr;
/// the caller will fall through to direct / default-network strategies.
#[cfg(target_os = "windows")]
fn get_windows_system_proxy() -> Option<String> {
    let output = std::process::Command::new("reg")
        .args([
            "query",
            r"HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ])
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .creation_flags(CREATE_NO_WINDOW)
        .output()
        .ok()?;

    if !output.status.success() {
        return None;
    }

    let text = String::from_utf8_lossy(&output.stdout);

    // Parse ProxyEnable (REG_DWORD). Must be 1 for proxy to be active.
    let proxy_enabled = text.lines().any(|line| {
        line.contains("ProxyEnable")
            && line.contains("REG_DWORD")
            && line.contains("0x1")
    });

    if !proxy_enabled {
        return None;
    }

    // Check for AutoConfigURL (PAC/WPAD). If set, the proxy is script-based.
    let has_auto_config = text.lines().any(|line| {
        line.contains("AutoConfigURL") && line.contains("REG_SZ")
    });

    // Parse ProxyServer (REG_SZ). Value like "127.0.0.1:7897" or "http=host:port;..."
    let proxy_server = text.lines().find_map(|line| {
        if !line.contains("ProxyServer") || !line.contains("REG_SZ") {
            return None;
        }
        let parts: Vec<&str> = line.splitn(2, "REG_SZ").collect();
        if parts.len() != 2 {
            return None;
        }
        let value = parts[1].trim();
        if value.is_empty() {
            return None;
        }
        Some(value.to_string())
    });

    // No ProxyServer value: check if AutoConfigURL is set (PAC/WPAD)
    if proxy_server.is_none() {
        if has_auto_config {
            eprintln!("[updater] 检测到 PAC/WPAD 自动代理配置，暂不支持，将使用直连或默认网络");
        }
        return None;
    }

    let proxy_server = proxy_server.unwrap();

    // Check for SOCKS proxy before parsing
    if proxy_server
        .to_lowercase()
        .contains("socks")
    {
        eprintln!("[updater] 检测到 SOCKS 代理配置，暂不支持，将使用直连或默认网络");
        return None;
    }

    // Handle IE-style multi-proxy format: "http=host:port;https=host:port;..."
    // Pick the HTTPS proxy first, then HTTP.
    let proxy_addr = if proxy_server.contains('=') {
        proxy_server
            .split(';')
            .find_map(|part| {
                let kv: Vec<&str> = part.splitn(2, '=').collect();
                if kv.len() == 2 && kv[0].trim().eq_ignore_ascii_case("https") {
                    return Some(kv[1].trim().to_string());
                }
                None
            })
            .or_else(|| {
                proxy_server.split(';').find_map(|part| {
                    let kv: Vec<&str> = part.splitn(2, '=').collect();
                    if kv.len() == 2 && kv[0].trim().eq_ignore_ascii_case("http") {
                        return Some(kv[1].trim().to_string());
                    }
                    None
                })
            })?
    } else {
        proxy_server
    };

    // Avoid double-prefixing if the address already has a scheme
    if proxy_addr.starts_with("http://") || proxy_addr.starts_with("https://") {
        return Some(proxy_addr);
    }

    Some(format!("http://{}", proxy_addr))
}

#[cfg(not(target_os = "windows"))]
fn get_windows_system_proxy() -> Option<String> {
    None
}

/// Build request strategies for manifest fetches (short timeout).
fn build_manifest_strategies(url: &str) -> Vec<(String, reqwest::Client)> {
    let timeout = Duration::from_secs(MANIFEST_TIMEOUT_SECS);
    build_strategies_inner(url, timeout)
}

/// Build request strategies for installer downloads (long timeout).
fn build_download_strategies(url: &str) -> Vec<(String, reqwest::Client)> {
    let timeout = Duration::from_secs(INSTALLER_DOWNLOAD_TIMEOUT_SECS);
    build_strategies_inner(url, timeout)
}

/// Shared strategy builder. The caller controls timeout to distinguish manifest vs download.
fn build_strategies_inner(url: &str, timeout: Duration) -> Vec<(String, reqwest::Client)> {
    let trusted = is_trusted_update_host(url);
    let mut strategies: Vec<(String, reqwest::Client)> = Vec::new();

    if let Some(proxy_url) = get_windows_system_proxy() {
        let addr = proxy_url.strip_prefix("http://").unwrap_or(&proxy_url);
        if let Ok(client) = build_update_client(timeout, Some(&proxy_url)) {
            strategies.push((format!("系统代理({})", addr), client));
        }
    }

    if trusted {
        if let Ok(client) = build_no_proxy_client(timeout) {
            strategies.push(("直连".to_string(), client));
        }
    }

    if let Ok(client) = build_update_client(timeout, None) {
        strategies.push(("默认网络".to_string(), client));
    }

    strategies
}

async fn fetch_remote_manifest(url: &str) -> Result<RemoteManifest, String> {
    let mut errors: Vec<String> = Vec::new();

    for (label, client) in build_manifest_strategies(url) {
        match try_get_with_client(&label, client, url, true).await {
            Ok(response) => match response.text().await {
                Ok(body) => match serde_json::from_str::<RemoteManifest>(&body) {
                    Ok(remote) => return Ok(remote),
                    Err(error) => {
                        let preview = body
                            .chars()
                            .take(80)
                            .collect::<String>()
                            .replace('\r', " ")
                            .replace('\n', " ");
                        errors.push(format!(
                            "{}: manifest 格式错误: {}，响应预览: {}",
                            label, error, preview
                        ));
                    }
                },
                Err(error) => errors.push(format!(
                    "{}: 读取 manifest 响应失败: {}",
                    label,
                    summarize_reqwest_error(&error)
                )),
            },
            Err(error) => errors.push(format!("[manifest 阶段] {}", error)),
        }
    }

    let detail = if errors.is_empty() {
        "所有网络策略均失败".to_string()
    } else {
        errors.join("; ")
    };

    Err(format!("无法获取有效更新清单（{}）", detail))
}

async fn download_verified_installer(
    download_url: &str,
    expected_sha256: &str,
    expected_size_bytes: u64,
    temp_path: &PathBuf,
    installer_path: &PathBuf,
) -> Result<String, String> {
    let mut errors: Vec<String> = Vec::new();
    let max_allowed_size = (expected_size_bytes as f64 * DOWNLOAD_SIZE_TOLERANCE) as u64;

    for (label, client) in build_download_strategies(download_url) {
        let response = match try_get_with_client(&label, client, download_url, true).await {
            Ok(response) => response,
            Err(error) => {
                errors.push(format!("[安装包下载阶段] {}", error));
                continue;
            }
        };

        // Pre-check Content-Length header if available
        if let Some(content_length) = response.content_length() {
            if content_length > max_allowed_size {
                errors.push(format!(
                    "{}: 安装包声明大小 ({} bytes) 超过 manifest sizeBytes ({} bytes) 的容差上限",
                    label, content_length, expected_size_bytes
                ));
                continue;
            }
        }

        let mut file = match tokio::fs::File::create(temp_path).await {
            Ok(file) => file,
            Err(error) => return Err(format!("创建临时文件失败: {}", error)),
        };

        let mut hasher = Sha256::new();
        let mut downloaded_bytes: u64 = 0;
        let mut stream = response.bytes_stream();

        use futures_util::StreamExt;
        let mut stream_failed = false;
        while let Some(chunk) = stream.next().await {
            match chunk {
                Ok(chunk) => {
                    downloaded_bytes += chunk.len() as u64;

                    // Abort if cumulative download exceeds tolerance
                    if downloaded_bytes > max_allowed_size {
                        let _ = tokio::fs::remove_file(temp_path).await;
                        errors.push(format!(
                            "{}: 下载大小 ({} bytes) 超过 manifest 声明大小 ({} bytes) 的容差上限，已中止",
                            label, downloaded_bytes, expected_size_bytes
                        ));
                        stream_failed = true;
                        break;
                    }

                    file.write_all(&chunk)
                        .await
                        .map_err(|e| format!("写入临时文件失败: {}", e))?;
                    hasher.update(&chunk);
                }
                Err(error) => {
                    errors.push(format!(
                        "{}: 下载数据流错误: {}",
                        label,
                        summarize_reqwest_error(&error)
                    ));
                    stream_failed = true;
                    break;
                }
            }
        }

        if stream_failed {
            let _ = tokio::fs::remove_file(temp_path).await;
            continue;
        }

        file.flush()
            .await
            .map_err(|e| format!("刷新临时文件失败: {}", e))?;
        drop(file);

        // Verify exact size matches manifest sizeBytes
        if downloaded_bytes != expected_size_bytes {
            let _ = tokio::fs::remove_file(temp_path).await;
            errors.push(format!(
                "{}: 安装包大小不匹配，期望: {} bytes，实际: {} bytes",
                label, expected_size_bytes, downloaded_bytes
            ));
            continue;
        }

        let actual_sha256 = hex::encode(hasher.finalize());
        if actual_sha256 != expected_sha256 {
            let _ = tokio::fs::remove_file(temp_path).await;
            errors.push(format!(
                "{}: 安装包 SHA256 不匹配，期望: {}，实际: {}",
                label,
                short_digest(expected_sha256),
                short_digest(&actual_sha256)
            ));
            continue;
        }

        if installer_path.exists() {
            let _ = tokio::fs::remove_file(installer_path).await;
        }
        tokio::fs::rename(temp_path, installer_path)
            .await
            .map_err(|e| format!("重命名安装包失败: {}", e))?;

        return Ok(actual_sha256);
    }

    let detail = if errors.is_empty() {
        "所有网络策略均失败".to_string()
    } else {
        errors.join("; ")
    };
    Err(format!("下载安装包失败，所有网络策略均未通过校验（{}）", detail))
}

// ── Tauri commands ──

/// Check for updates by fetching the release manifest.
///
/// Returns version comparison result and manifest metadata.
/// Does NOT download or install anything.
///
/// If `current_version < minSupportedVersion`, returns `requires_manual_download: true`
/// and blocks automatic update.
#[tauri::command]
pub async fn check_update(
    manifest_url: String,
    channel: Option<String>,
) -> Result<UpdateCheckResult, String> {
    validate_https_url(&manifest_url)?;
    validate_manifest_host(&manifest_url)?;

    let current_version = get_current_version().to_string();

    // Fetch manifest JSON with proxy-first, direct-fallback strategy
    let remote = fetch_remote_manifest(&manifest_url).await?;

    // Validate schema version
    if remote.schema_version != 1 {
        return Err(format!(
            "不支持的 manifest 版本: schemaVersion={}",
            remote.schema_version
        ));
    }

    // Validate platform and arch
    if remote.platform != "windows" || remote.arch != "x64" {
        return Err(format!(
            "平台或架构不匹配: 期望 windows/x64, 得到 {}/{}",
            remote.platform, remote.arch
        ));
    }

    // Validate channel if specified
    if let Some(ref expected_channel) = channel {
        if &remote.channel != expected_channel {
            return Err(format!(
                "频道不匹配: 期望 {}, 得到 {}",
                expected_channel, remote.channel
            ));
        }
    }

    // Parse versions using semver
    let remote_ver = parse_semver(&remote.version)?;
    let current_ver = parse_semver(&current_version)?;

    let version_is_newer = remote_ver > current_ver;

    // Enforce minSupportedVersion: non-empty value must be valid semver
    let mut requires_manual_download = false;
    if !remote.min_supported_version.is_empty() {
        let min_ver = parse_semver(&remote.min_supported_version).map_err(|e| {
            format!("manifest 字段 minSupportedVersion 非法: {}", e)
        })?;
        if current_ver < min_ver {
            requires_manual_download = true;
        }
    }

    let manifest_response = UpdateManifestResponse {
        schema_version: remote.schema_version,
        channel: remote.channel,
        platform: remote.platform,
        arch: remote.arch,
        version: remote.version.clone(),
        min_supported_version: remote.min_supported_version,
        published_at: remote.published_at,
        installer: InstallerInfo {
            url: remote.installer.url,
            sha256: remote.installer.sha256,
            size_bytes: remote.installer.size_bytes,
        },
        release_notes: remote.release_notes.unwrap_or_default(),
        critical: remote.critical.unwrap_or(false),
    };

    // has_update only when version is newer AND auto-update is allowed
    let has_update = version_is_newer && !requires_manual_download;

    Ok(UpdateCheckResult {
        has_update,
        current_version,
        latest_version: remote.version,
        // Include manifest even when no auto-update, so the UI can show version info
        manifest: if version_is_newer || requires_manual_download {
            Some(manifest_response)
        } else {
            None
        },
        error: None,
        requires_manual_download,
    })
}

/// Download the installer and verify its SHA256 hash and size.
///
/// Re-fetches the manifest server-side to avoid trusting frontend-supplied data.
/// On success, stores verified metadata in Tauri state and persists it to disk.
/// On hash/size mismatch, cleans up the corrupt file and returns an error.
#[tauri::command]
pub async fn download_update(
    app: AppHandle,
    manifest_url: String,
    expected_version: String,
) -> Result<UpdateDownloadResult, String> {
    validate_https_url(&manifest_url)?;
    validate_manifest_host(&manifest_url)?;

    // Re-fetch manifest with proxy-first, direct-fallback strategy
    // (do not trust frontend-supplied hash/url)
    let remote = fetch_remote_manifest(&manifest_url).await?;

    // Verify the version matches what the frontend expected
    if remote.version != expected_version {
        return Err(format!(
            "版本不一致: 期望 {}, manifest 返回 {}",
            expected_version, remote.version
        ));
    }

    let download_url = &remote.installer.url;
    let expected_sha256 = remote.installer.sha256.to_lowercase();
    let expected_size = remote.installer.size_bytes;

    validate_https_url(download_url)?;
    validate_installer_host(download_url)?;

    // Prepare cache directory
    let cache_dir = get_cache_dir(&app)?;
    let installer_name = format!("zhangshu-{}-setup.exe", remote.version);
    let installer_path = cache_dir.join(&installer_name);
    let temp_path = cache_dir.join(format!("{}.part", installer_name));

    let actual_sha256 = download_verified_installer(
        download_url,
        &expected_sha256,
        expected_size,
        &temp_path,
        &installer_path,
    )
    .await?;

    // Store verified metadata in memory (Tauri state)
    let metadata = VerifiedUpdateMetadata {
        version: remote.version.clone(),
        sha256: actual_sha256,
        installer_path: installer_path.to_string_lossy().to_string(),
        size_bytes: expected_size,
    };

    // Persist metadata to disk for cross-session install
    let metadata_path = cache_dir.join("verified_update.json");
    let metadata_json = serde_json::to_string_pretty(&metadata)
        .map_err(|e| format!("序列化元数据失败: {}", e))?;
    std::fs::write(&metadata_path, metadata_json)
        .map_err(|e| format!("写入元数据文件失败: {}", e))?;

    // Update in-memory state
    let state: State<VerifiedUpdateState> = app.state();
    *state.metadata.lock().map_err(|_| "状态锁获取失败")? = Some(metadata);

    Ok(UpdateDownloadResult {
        success: true,
        version: remote.version,
        cached_path: Some(installer_path.to_string_lossy().to_string()),
        error: None,
    })
}

/// Launch the updater helper to install a previously downloaded and verified update.
///
/// Security: reads verified metadata from Rust state (or persisted file),
/// re-checks SHA256 of the cached installer, then spawns the updater helper
/// and exits the main app.
#[tauri::command]
pub async fn install_update(
    app: AppHandle,
    expected_version: String,
) -> Result<UpdateInstallResult, String> {
    // 1. Read verified metadata from memory or disk
    let metadata = {
        let state: State<VerifiedUpdateState> = app.state();
        let guard = state
            .metadata
            .lock()
            .map_err(|_| "状态锁获取失败")?;
        if let Some(ref m) = *guard {
            m.clone()
        } else {
            // Try loading from persisted file
            let cache_dir = get_cache_dir(&app)?;
            let metadata_path = cache_dir.join("verified_update.json");
            let content = std::fs::read_to_string(&metadata_path)
                .map_err(|_| "未找到已验证的更新元数据，请先下载更新")?;
            serde_json::from_str::<VerifiedUpdateMetadata>(&content)
                .map_err(|e| format!("读取元数据失败: {}", e))?
        }
    };

    // 2. Verify version matches
    if metadata.version != expected_version {
        return Err(format!(
            "版本不匹配: 期望 {}, 已缓存 {}",
            expected_version, metadata.version
        ));
    }

    // 3. Verify installer file still exists and hash still matches
    let installer_path = PathBuf::from(&metadata.installer_path);
    if !installer_path.exists() {
        return Err("安装包文件不存在，请重新下载".to_string());
    }

    let file_bytes = std::fs::read(&installer_path)
        .map_err(|e| format!("读取安装包失败: {}", e))?;
    let actual_sha256 = hex::encode(Sha256::digest(&file_bytes));
    if actual_sha256 != metadata.sha256 {
        let _ = std::fs::remove_file(&installer_path);
        return Err("安装包已被篡改，请重新下载".to_string());
    }

    // 4. Locate the updater helper next to the main exe
    let app_exe = std::env::current_exe()
        .map_err(|e| format!("获取当前程序路径失败: {}", e))?;
    let app_dir = app_exe
        .parent()
        .ok_or_else(|| "无法获取程序目录".to_string())?;
    let updater_exe = app_dir.join("zhangshu-updater.exe");
    if !updater_exe.exists() {
        return Err(format!(
            "找不到更新工具: {}",
            updater_exe.display()
        ));
    }

    // 5. Spawn updater helper with verified arguments
    let parent_pid = std::process::id().to_string();
    let mut cmd = std::process::Command::new(&updater_exe);
    cmd.arg("--installer")
        .arg(&metadata.installer_path)
        .arg("--app-exe")
        .arg(&app_exe)
        .arg("--parent-pid")
        .arg(&parent_pid)
        .arg("--silent");

    #[cfg(target_os = "windows")]
    cmd.creation_flags(CREATE_NO_WINDOW);

    cmd.spawn()
        .map_err(|e| format!("启动更新工具失败: {}", e))?;

    // 6. Exit main app so the updater helper can proceed with installation
    app.exit(0);

    // This return is unreachable after exit, but satisfies the type checker
    Ok(UpdateInstallResult {
        success: true,
        error: None,
    })
}
