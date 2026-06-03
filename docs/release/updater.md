# 章枢桌面版 - 更新系统说明

本文档描述章枢 Windows 桌面版的更新系统架构、构建流程和发布步骤。

## 架构概述

更新系统采用 **完整安装包覆盖更新** 方案，不使用差分补丁或热替换：

1. **Release Manifest** - 静态 JSON 文件，托管在 HTTPS 服务器上，声明最新版本信息。
2. **应用内检查** - 用户点击"检查更新"后，Tauri Rust 端获取 manifest 并比较版本号。
3. **下载与校验** - Rust 下载安装包到本地缓存目录，计算 SHA256 并校验。
4. **Updater Helper** - 独立进程，等待主程序退出后运行 Inno Setup 安装器，再重启应用。

### 安全边界

- 所有网络请求必须使用 HTTPS 协议（开发环境允许 localhost HTTP）。
- SHA256 校验是安装前的强制步骤，校验失败禁止安装。
- Rust 端独立维护 verified metadata，前端传入的路径和 hash 不被信任。
- Updater helper 只执行 Rust 验证过的本地安装器，不接受任意路径。

### 数据保护

- 用户数据存储在 `%LOCALAPPDATA%\com.zhangshu.desktop\data\`。
- 安装目录 (`Program Files\章枢`) 和用户数据目录互相独立。
- 覆盖安装不会删除或覆盖用户数据。

## 版本号管理

版本号以 `frontend/package.json` 的 `version` 字段为唯一来源。以下文件必须保持一致：

| 文件 | 字段 |
|---|---|
| `frontend/package.json` | `"version"` |
| `frontend/src-tauri/tauri.conf.json` | `"version"` |
| `frontend/src-tauri/Cargo.toml` | `version` |

构建脚本 (`scripts/build_installer.ps1`) 会在构建前验证版本一致性，不一致则中止。

## 构建与发布流程

### 1. 构建安装包

```powershell
cd F:\zhangshu
.\scripts\build_installer.ps1
```

该脚本会：

1. 验证版本号一致性。
2. 构建前端 dist。
3. PyInstaller 构建后端 sidecar。
4. 运行 smoke test。
5. Cargo 构建 Tauri desktop + updater helper。
6. Inno Setup 生成安装包。
7. 计算 SHA256 并生成 release manifest。

输出：

- `release/章枢_Setup_{version}_windows_x64.exe` - 安装包
- `release/latest.windows-x64.json` - Release manifest

### 2. 验证 Manifest

```powershell
.\scripts\smoke_updater_manifest.ps1
```

验证 manifest JSON 格式、字段完整性、SHA256 与本地安装包匹配。

### 3. 上传发布文件

将以下文件上传到发布服务器（`121.40.247.143`）：

| 本地文件 | 服务器目标路径 | 说明 |
|---|---|---|
| `release/章枢_Setup_{version}_windows_x64.exe` | `/var/www/zhangshu-downloads/zhangshu/releases/{version}/` | 安装包下载 |
| `release/latest.windows-x64.json` | `/var/www/zhangshu-updates/zhangshu/stable/windows-x64/` | Release manifest |

> **注意**：构建脚本生成的安装包和 manifest 仅为本地构建产物，不会自动上传到服务器。发布前需手动上传，并建议先备份服务器上的旧 `latest.json`。

### 4. Manifest URL 配置

应用内检查更新时使用以下地址（按优先级）：

| 类型 | URL |
|---|---|
| 主用 | `https://updates.zhangshu.xin/zhangshu/stable/windows-x64/latest.json` |
| 备用 | `https://updates.emailbs.xin/zhangshu/stable/windows-x64/latest.json` |

Fallback 逻辑：主地址成功（含"已是最新"）时不请求备用地址；主地址网络失败、DNS 失败、TLS 失败或 5xx 时尝试备用地址；两个地址都失败时提示"主用与备用更新源均不可用"。

定义位置：`frontend/src/entities/update/api.ts`

构建时传入下载基础 URL：

```powershell
.\scripts\build_installer.ps1 -DownloadBaseUrl "https://downloads.zhangshu.xin/zhangshu/releases/$version"
```

或在 `generate_update_manifest.ps1` 中传入：

```powershell
.\scripts\generate_update_manifest.ps1 `
    -Version "0.9.0" `
    -InstallerPath "release\章枢_Setup_0.9.0_windows_x64.exe" `
    -DownloadBaseUrl "https://downloads.zhangshu.xin/zhangshu/releases/0.9.0"
```

## 代理环境兼容策略

从 `0.8.1` 版本开始，更新系统支持在用户挂代理的环境下正常工作。

### 请求策略

更新系统采用"代理优先，直连兜底"的请求策略：

1. **第一次请求**：使用 reqwest 默认 client，尊重系统代理设置和环境变量代理（如 `HTTP_PROXY`、`HTTPS_PROXY`、`ALL_PROXY`）。
2. **代理失败时**：如果请求失败，检查目标 URL 的 host 是否在可信更新域名列表中。
3. **直连兜底**：仅对可信更新域名执行直连重试（使用 `no_proxy()` client 绕过所有代理）。
4. **非可信域名**：不允许对任意 URL 做无条件直连兜底，直接返回代理模式的错误。

### 可信更新域名

以下域名被允许使用直连兜底：

- `updates.zhangshu.xin` — 主更新源
- `downloads.zhangshu.xin` — 安装包下载
- `updates.emailbs.xin` — 备用更新源

开发环境（debug builds）额外允许：

- `127.0.0.1`
- `localhost`

### 错误诊断

当代理和直连都失败时，错误信息会区分两种模式的失败原因：

```
无法连接更新服务器（代理模式: 代理连接超时, 直连模式: 直连超时），请检查网络连接
```

这有助于用户判断是代理配置问题还是服务器本身不可达。

### 实现位置

网络兼容逻辑位于 `frontend/src-tauri/src/updater.rs`：

- `is_trusted_update_host()` — 判断 URL 是否为可信更新域名（用于直连兜底）
- `build_update_client()` — 构建带代理的 HTTP client（接受 timeout 参数）
- `build_no_proxy_client()` — 构建直连 HTTP client（绕过代理）
- `build_strategies_inner()` — 共享策略构建器（代理 → 直连 → 默认网络）

manifest 获取和安装包下载复用代理优先、直连兜底、默认网络的策略框架，但使用不同 timeout profile：

- `build_manifest_strategies()` — manifest 专用（30 秒总超时）
- `build_download_strategies()` — 安装包下载专用（600 秒总超时）

### 请求超时

从 `0.8.2` 版本开始，manifest 请求和安装包下载使用不同的超时策略：

| 请求类型 | 连接超时 | 总超时 |
|---|---|---|
| Manifest 获取 | 8 秒 | 30 秒 |
| 安装包下载 | 8 秒 | 600 秒（10 分钟） |

分离超时可避免大文件下载在慢速网络下被 30 秒杀死。下载阶段显示"正在下载新版本，请勿关闭…"提示用户耐心等待。

## 客户端安全加固（0.8.2+）

### Host Allowlist

Rust 端强制校验 URL 所属 host，前端传入的 URL 若不在可信列表中将被拒绝：

| URL 类型 | 可信 Host |
|---|---|
| Manifest | `updates.zhangshu.xin`, `updates.emailbs.xin` |
| Installer | `downloads.zhangshu.xin`, `downloads.emailbs.xin` |

开发环境（`#[cfg(debug_assertions)]`）额外允许 `127.0.0.1` 和 `localhost`。

### 下载大小校验

下载安装包时会执行双重大小校验：

1. 对比 HTTP 响应头 `Content-Length`（如有），超过 `sizeBytes × 1.1` 直接跳过。
2. 下载流中累计字节数，超过 `sizeBytes × 1.1` 立即中止并删除临时文件。
3. 下载完成后，要求实际字节数与 manifest `sizeBytes` 严格一致。
4. SHA256 校验仍作为最终防线。

### minSupportedVersion 强制执行

`minSupportedVersion` 字段参与更新决策：

- **空字符串**：视为无最低版本约束，按正常版本比较逻辑判断。
- **非空且合法 semver**：当 `minSupportedVersion` 高于当前应用版本时，`has_update` 返回 `false`，`requiresManualDownload` 返回 `true`，前端显示"当前版本过旧，需手动下载最新安装包"。
- **非空但非法 semver**：返回 manifest 校验错误，不再静默忽略。

### UI 诊断信息

错误详情区域支持"展开详情"（长错误不再被截断）和"复制诊断信息"按钮，方便用户将完整错误信息反馈给开发者。错误信息包含阶段标记（`[manifest 阶段]` / `[安装包下载阶段]`），便于快速定位失败环节。

### 代理解析增强

`get_windows_system_proxy()` 改进了 Windows 注册表 `ProxyServer` 字符串解析：

- `127.0.0.1:7897` → 自动补 `http://` 前缀
- `http://127.0.0.1:7897` → 保持原样（不再双重补前缀）
- `http=host:port;https=host:port` → 优先选择 `https` 条目
- SOCKS / PAC / WPAD 等不支持的类型 → 输出 `eprintln!` 诊断日志，不静默失败

## Manifest Schema

```json
{
  "schemaVersion": 1,
  "channel": "stable",
  "platform": "windows",
  "arch": "x64",
  "version": "0.9.0",
  "minSupportedVersion": "0.8.0",
  "publishedAt": "2026-06-01T00:00:00Z",
  "installer": {
    "url": "https://downloads.zhangshu.xin/zhangshu/releases/0.9.0/章枢_Setup_0.9.0_windows_x64.exe",
    "sha256": "<64-char-hex>",
    "sizeBytes": 123456789
  },
  "releaseNotes": ["新功能说明"],
  "critical": false
}
```

## MVP 边界

当前版本（MVP）的已知限制：

- **完整安装包覆盖** - 不支持差分更新，每次更新需下载完整安装包。
- **手动触发** - 用户需主动点击"检查更新"，不支持后台自动检查。
- **需要 UAC 确认** - Inno Setup 使用 admin 权限安装，更新时会弹出 Windows 安全提示。
- **无强制更新** - 不实现强制更新机制，用户可选择不更新。
- **无多渠道** - manifest 中保留 `channel` 字段但仅支持 `stable`。
- **无代码签名** - 当前仅使用 SHA256 校验，后续可增加代码签名。
- **manifest 未签名** - 当前 manifest 依赖 HTTPS 传输安全 + 安装包 SHA256 校验。SHA256 可验证安装包完整性，但无法证明 manifest 本身未被中间人替换。建议后续引入 Ed25519 manifest 签名校验，配合发布流程签名，消除 manifest 替换风险。

## 故障排除

### 更新后数据丢失

不应该发生。如果发现数据丢失，检查：

1. `%LOCALAPPDATA%\com.zhangshu.desktop\data\` 目录是否存在。
2. 安装器是否被配置为覆盖用户数据目录（默认不会）。

### SHA256 校验失败

可能原因：

- 下载过程中网络错误导致文件损坏。
- 服务器上的安装包被替换但 manifest 未更新。
- manifest 中的 sha256 字段值错误。

解决：删除缓存目录 `%LOCALAPPDATA%\com.zhangshu.desktop\updater_cache\` 并重新下载。

### 安装器无法启动

检查：

- `zhangshu-updater.exe` 是否存在于安装目录。
- 日志文件 `%TEMP%\zhangshu-updater.log` 中的错误信息。
- Windows 安全策略是否阻止了安装器执行。
