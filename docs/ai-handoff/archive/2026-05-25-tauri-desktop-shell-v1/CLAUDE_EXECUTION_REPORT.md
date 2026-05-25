---
archived_at: 2026-05-25
archive_reason: Tauri Desktop Shell V1 completed; preparing next feature plan
date: 2026-05-25
task: Tauri Desktop Shell V1
codex_plan: docs/ai-handoff/CODEX_PLAN.md (Tauri Thin Shell V1)
status: COMPLETED
---

## Task Summary

实现 Tauri 桌面壳 V1：让章枢可以作为 Windows 桌面应用启动，自动拉起 FastAPI sidecar，加载 Vue 前端，使用本机应用数据目录。

## Files Changed

### 新增

- `backend/tauri_sidecar_main.py` — Tauri 专用 sidecar 入口，不打开浏览器，固定端口 8765
- `frontend/src-tauri/Cargo.toml` — Tauri Rust 项目配置，依赖 tauri 2 + tauri-plugin-shell 2
- `frontend/src-tauri/tauri.conf.json` — Tauri v2 配置（窗口 1440x900、sidecar、shell plugin）
- `frontend/src-tauri/build.rs` — Tauri build script（`fn main() { tauri_build::build() }`）
- `frontend/src-tauri/src/main.rs` — Tauri 应用入口，启动 sidecar、管理生命周期
- `frontend/src-tauri/icons/` — 占位图标（纯 Python 生成的纯色 PNG/ICO/ICNS）
- `frontend/src-tauri/capabilities/default.json` — Tauri v2 权限配置（shell:allow-spawn 等）

### 修改

- `frontend/package.json` — 新增 `@tauri-apps/cli`、`cross-env`、tauri 相关 scripts
- `frontend/vite.config.ts` — 添加 `strictPort: true`
- `.gitignore` — 新增 Tauri 二进制忽略规则
- `README.md` — 新增桌面版开发/打包说明章节

### 构建产物（不提交 Git）

- `frontend/src-tauri/binaries/zhangshu-backend-x86_64-pc-windows-msvc.exe` — PyInstaller 打包的 sidecar（~41MB）
- `frontend/src-tauri/binaries/zhangshu-backend.exe` — PyInstaller 原始输出

## Implementation Notes

### Sidecar 入口 (`backend/tauri_sidecar_main.py`)

- 不打开系统浏览器（区别于 `packaged_main.py`）
- 固定默认端口 8765（通过 `ZHANGSHU_BACKEND_PORT` 环境变量覆盖）
- 数据目录使用 `ZHANGSHU_DATA_DIR` 或回退到 exe 旁的 `zhangshu_data`
- 启动失败写入 `startup_error.log`
- 支持 PyInstaller frozen 和普通脚本两种运行模式

### Tauri Rust 入口 (`frontend/src-tauri/src/main.rs`)

- 使用 `tauri-plugin-shell` 的 sidecar 机制启动 Python 后端
- 导入 `tauri_plugin_shell::ShellExt` trait 以调用 `.shell()` 方法
- 设置环境变量：`ZHANGSHU_BACKEND_HOST=127.0.0.1`、`ZHANGSHU_BACKEND_PORT=8765`、`ZHANGSHU_DATA_DIR`（app_local_data_dir/data）、`ZHANGSHU_LOG_DIR`（app_local_data_dir/logs）、`ZHANGSHU_DB_FILENAME=zhangshu.sqlite3`
- 异步任务转发 sidecar stdout/stderr 到控制台
- 窗口 Destroyed 事件时使用 `taskkill /F /T /PID` 终止 sidecar 进程树
- `SidecarState` 管理 sidecar PID

### Tauri v2 权限配置 (`capabilities/default.json`)

- Tauri v2 使用 capabilities 系统替代旧版 `plugins.shell.scope` 配置
- 授权权限：`core:default`、`shell:allow-spawn`、`shell:allow-execute`、`shell:allow-open`、`shell:allow-kill`、`shell:allow-stdin-write`

### 前端 API 基址策略

- Web 开发：`VITE_API_BASE_URL` 未设置 → 相对路径 → 打到 localhost:8000
- Tauri dev：`cross-env VITE_API_BASE_URL=http://127.0.0.1:8765` → 打到 sidecar
- Tauri build：`tauri:build:frontend` 脚本设置 `VITE_API_BASE_URL=http://127.0.0.1:8765`

### npm Scripts

```json
"tauri:dev": "cross-env VITE_API_BASE_URL=http://127.0.0.1:8765 tauri dev",
"tauri:build:frontend": "cross-env VITE_API_BASE_URL=http://127.0.0.1:8765 npm run build",
"tauri:build": "npm run tauri:build:frontend && tauri build",
"tauri:build:backend": "cd .. && backend\\.venv\\Scripts\\python.exe -m PyInstaller ..."
```

### Rust 镜像配置

已配置清华镜像（用户级环境变量）+ USTC Cargo 镜像（`~/.cargo/config.toml`）：

```toml
[source.crates-io]
replace-with = 'ustc'

[source.ustc]
registry = "sparse+https://mirrors.ustc.edu.cn/crates.io-index/"
```

## Deviations from Codex Plan

- 无重大偏差
- 图标使用纯 Python 生成的纯色占位图标（无正式图标）
- 额外添加了 `cross-env` 依赖（用于跨平台设置环境变量）
- `tauri:build:backend` 脚本实现了完整的 PyInstaller 构建 + 重命名命令
- 新增 `capabilities/default.json`（Tauri v2 权限系统要求，Codex Plan 未提及）
- `tauri.conf.json` 中 `plugins.shell` 只保留 `open: true`，sidecar 权限移至 capabilities

## Verification Commands Run

- `npm run type-check` → ✅ 通过
- `rustc --version` → ✅ rustc 1.95.0（清华镜像安装）
- `cargo --version` → ✅ cargo 1.95.0
- PyInstaller sidecar build → ✅ 成功生成 `zhangshu-backend-x86_64-pc-windows-msvc.exe`
- `cargo check` → ✅ 通过（修复 `ShellExt` import 后）
- `npm run tauri:dev` → ✅ 成功启动桌面窗口、sidecar 运行、API 请求 200 OK
- `npm run tauri:build` → 未执行（需要手动测试打包流程）

## Verification Results

**全部通过：**

- 前端类型检查正常
- Rust 工具链安装成功（1.95.0 stable-x86_64-pc-windows-msvc）
- VS Build Tools 2022 安装成功（VCTools 工作负载 + Windows SDK 10.0.26100.0）
- PyInstaller sidecar 构建成功（41MB 单文件 exe）
- npm 依赖安装完成（@tauri-apps/cli 2.5.0、cross-env 7.0.3）
- `cargo check` 通过（修复 `use tauri_plugin_shell::ShellExt` import）
- `npm run tauri:dev` 成功：
  - Vite 开发服务器启动（localhost:5180）
  - Rust 编译完成（首次 47.80s，增量 4.24s）
  - 桌面窗口打开（1440x900）
  - Sidecar 自动启动（127.0.0.1:8765）
  - 数据目录正确：`C:\Users\JunLing\AppData\Local\com.zhangshu.desktop\data`
  - API 请求成功：`GET /api/projects → 200 OK`

**修复过的错误：**

1. **MSVC 链接器缺失**：安装 VS Build Tools 2022 解决
2. **`ShellExt` trait 未导入**：添加 `use tauri_plugin_shell::ShellExt` 解决
3. **`plugins.shell.scope` 未知字段**：Tauri v2 使用 capabilities 系统，移除 scope 并创建 `capabilities/default.json` 解决

## Known Issues

1. **占位图标**：当前使用纯色占位图标，后续需替换正式图标
2. **固定端口 8765**：V1 决策，存在端口占用风险
3. **sidecar taskkill**：Windows 专用，macOS/Linux 需要不同方案（V1 仅支持 Windows，可接受）
4. **CORS**：Tauri dev 模式下前端从 localhost:5180 发请求到 127.0.0.1:8765，CORS 已配置允许 localhost:5180。Tauri production 模式下前端通过 file:// 协议加载，可能需要补充 CORS origin 或使用 `tauri://` 协议，待实际测试确认
5. **控制台乱码**：Sidecar stdout 中的中文在 Windows 控制台显示为乱码（GBK 编码问题），不影响功能
6. **关闭窗口后 sidecar 清理**：Destroy 事件触发 taskkill，但需进一步验证是否可靠清理所有子进程

## Suggested Next Review Points for Codex

1. Tauri production 模式下的 CORS origin 是否需要补充（`tauri://` 协议或 `file://`）
2. sidecar 生命周期管理（taskkill 方案是否足够可靠，是否需要增加健康检查/重试）
3. `tauri:build:backend` 脚本的跨平台兼容性（当前仅 Windows）
4. 正式图标替换计划
5. `npm run tauri:build` 打包流程验证（NSIS/MSI 安装包生成）
6. 生产模式下前端 API 基址策略是否需要调整（`http://127.0.0.1:8765` 硬编码 vs 动态端口）
