<!-- archived: 2026-05-25; reason: Tauri Desktop Shell V1 completed by Claude Code -->

# Task Summary

规划章枢桌面版 Tauri 壳 V1，由 Claude Code 执行实现。Codex 本轮未修改任何业务代码。

本任务目标是先做一个 **Thin Tauri Shell**：让章枢可以作为 Windows 桌面应用启动、自动拉起本地 FastAPI 后端 sidecar、加载现有 Vue 前端、使用本机应用数据目录，并完成基础打包验证。

本任务不是重写业务架构，也不是把前端/后端逻辑迁入 Rust。Tauri 层只负责桌面运行环境：

- 桌面窗口；
- 后端 sidecar 启动与退出管理；
- 本地应用数据目录；
- 基础打包配置；
- 后续原生能力预留。

参考官方文档：

- Tauri v2 配置文件：`devUrl`、`frontendDist`、`beforeDevCommand`、`beforeBuildCommand`
  - https://v2.tauri.app/develop/configuration-files/
- Tauri sidecar / external binary
  - https://v2.tauri.app/develop/sidecar/

# Current Codebase Findings

1. 当前交接区状态：
   - `docs/ai-handoff/` 当前只有 `README.md` 和 `archive/`。
   - 没有活跃 `CODEX_PLAN.md`、`CLAUDE_EXECUTION_REPORT.md`、`CODEX_REVIEW.md`。
   - 本轮不需要归档旧交接文件。

2. 当前工作区存在未提交业务改动：
   - 写作统计仪表盘 V1 的后端、前端、测试文件仍处于 git 未提交状态。
   - Claude Code 执行本计划前必须先确认这些改动是上一轮任务结果，不要回滚、覆盖或混入无关修复。

3. 当前没有 Tauri 桌面壳：
   - 根目录没有 `src-tauri/`。
   - `frontend/` 下没有 `src-tauri/`。
   - README 中明确写 `Desktop Shell: Tauri，后续阶段规划`。

4. 当前前端结构：
   - `frontend/package.json` 使用 Vue 3 + Vite。
   - Vite dev server 端口为 `5180`，见 `frontend/vite.config.ts`。
   - `frontend/src/shared/api/client.ts` 当前通过 `import.meta.env.VITE_API_BASE_URL ?? ''` 决定 API 基址。
   - 这意味着桌面版如果由 Tauri 自己加载前端资源，必须显式提供 API base URL；否则前端会把 `/api/...` 请求发到 Tauri 静态资源协议，而不是 FastAPI。

5. 当前后端结构：
   - FastAPI app 在 `backend/app/main.py`。
   - 后端已支持 `ZHANGSHU_DATA_DIR`、`ZHANGSHU_DB_FILENAME`、`ZHANGSHU_FRONTEND_DIST`。
   - `_mount_frontend_static()` 已能在存在前端 dist 时由 FastAPI 托管前端静态资源。
   - CORS 当前允许 `5173` 与 `5180`。

6. 当前已有 PyInstaller 原型：
   - `backend/packaged_main.py` 会准备本地数据目录、寻找空闲端口、启动 uvicorn，并自动打开系统浏览器。
   - `scripts/build_windows_exe.ps1` 会先 `npm run build`，再用 PyInstaller 打包 `backend/packaged_main.py`，并把 `frontend/dist` 加入后端 exe。
   - 这说明项目已有“Python 后端 + 前端 dist 打包”的经验，可以复用，但 Tauri sidecar 不应自动打开系统浏览器。

7. 当前 `.gitignore` 特别需要注意：
   - 已忽略 `frontend/src-tauri/target/`，适合 Tauri Rust 构建产物。
   - 但也全局忽略了 `*.ps1`、`*.bat`、`scripts/`、`release/`、`build/`。
   - 如果新增 Tauri 构建脚本需要提交，必须调整 `.gitignore` 例外规则，或把脚本逻辑放入可追踪的 npm / Cargo 配置中。

# Architecture Decision

采用 **Thin Tauri Shell + FastAPI Sidecar** 架构。

## 核心原则

1. Tauri 层不写业务逻辑：
   - 不处理项目、章节、人物、设定、知识库、RAG、统计等业务。
   - 不直接读写 SQLite。
   - 不替代 FastAPI API。

2. 前端仍是现有 Vue 应用：
   - 普通 UI 修改仍发生在 `frontend/src/`。
   - 新增业务页面不需要同步改 Tauri，除非涉及桌面原生能力。

3. 后端仍是现有 FastAPI：
   - 普通 API、Service、Repository、Model 修改不需要同步改 Tauri。
   - Tauri 只负责启动 sidecar 和传递运行环境。

4. 桌面 V1 先只支持 Windows：
   - 当前项目路径、脚本、PowerShell、PyInstaller 原型都以 Windows 为主。
   - macOS/Linux 留作后续，不在本任务扩大范围。

## 桌面运行方式建议

V1 建议采用：

- Tauri 窗口加载 Vite 构建后的前端资源；
- Tauri 启动 FastAPI sidecar；
- 前端通过固定本地端口访问 sidecar，例如 `http://127.0.0.1:8765`；
- 后端数据目录使用 Tauri 应用数据目录，例如 `%APPDATA%` 或 `%LOCALAPPDATA%` 下的 `Zhangshu` 目录。

V1 可以先使用固定端口 `8765`，但必须做端口占用提示。更稳的 V1.1 再做动态端口注入。

选择固定端口的原因：

- 当前前端 API client 是构建时/运行时简单字符串；
- 动态端口需要 Tauri 在前端加载前注入运行时配置，复杂度更高；
- V1 目标是桌面壳跑通，而不是一次性解决所有启动拓扑问题。

## 后端 sidecar 入口

不要直接复用 `backend/packaged_main.py` 作为 Tauri sidecar，原因：

- 它会自动打开系统浏览器；
- 它会自己找空闲端口；
- 它的职责是旧版独立 exe，而不是 Tauri sidecar。

建议新增：

- `backend/tauri_sidecar_main.py`

职责：

- 读取 `ZHANGSHU_BACKEND_HOST`，默认 `127.0.0.1`；
- 读取 `ZHANGSHU_BACKEND_PORT`，默认 `8765`；
- 读取 `ZHANGSHU_DATA_DIR`；
- 读取 `ZHANGSHU_DB_FILENAME`，默认 `zhangshu.sqlite3`；
- 不打开系统浏览器；
- 启动 `app.main:app`；
- 启动失败时把错误写入本地日志目录；
- 对端口占用给出明确日志。

## 前端 API 基址

V1 推荐最小改动：

- 为桌面构建设置 `VITE_API_BASE_URL=http://127.0.0.1:8765`。
- 保持 `frontend/src/shared/api/client.ts` 当前逻辑。

如果 Claude Code 判断当前构建脚本难以稳定设置环境变量，可改为小范围增强 `api/client.ts`：

```ts
declare global {
  interface Window {
    __ZHANGSHU_API_BASE_URL__?: string
  }
}

export const API_BASE_URL =
  window.__ZHANGSHU_API_BASE_URL__ ?? import.meta.env.VITE_API_BASE_URL ?? ''
```

但 V1 不强制要求动态注入，除非固定端口方案在 Tauri 中不可用。

## Tauri 目录位置

建议采用 Tauri 常见结构：

- `frontend/src-tauri/`

原因：

- 当前 Vite 前端在 `frontend/`。
- Tauri 默认能更自然地以 `frontend/` 为前端项目根。
- `frontend/src-tauri/target/` 已在 `.gitignore` 中忽略。

# Files to Create or Modify

## Create

1. `frontend/src-tauri/Cargo.toml`
   - Tauri Rust 项目配置。

2. `frontend/src-tauri/tauri.conf.json`
   - Tauri v2 配置。
   - 配置窗口标题、尺寸、前端 dev/build 命令、frontend dist、bundle 信息、sidecar external binary。

3. `frontend/src-tauri/src/main.rs`
   - Tauri 应用入口。
   - 启动 sidecar。
   - 设置 `ZHANGSHU_DATA_DIR`、`ZHANGSHU_DB_FILENAME`、`ZHANGSHU_BACKEND_PORT`。
   - 窗口关闭时终止 sidecar。

4. `backend/tauri_sidecar_main.py`
   - Tauri 专用 FastAPI sidecar 入口。

5. `frontend/src-tauri/icons/`
   - 可先使用占位图标，或复用现有 favicon 生成必要尺寸。
   - 如果没有正式图标，本任务可以先使用 Tauri 默认图标，但执行报告必须说明。

6. 可选：`frontend/src-tauri/scripts/build-backend-sidecar.ps1`
   - 如果需要脚本打包 sidecar。
   - 如新增 `.ps1` 文件，必须同步调整 `.gitignore` 例外规则，否则脚本不会被 git 跟踪。

## Modify

1. `frontend/package.json`
   - 新增 Tauri 相关 devDependencies：
     - `@tauri-apps/cli`
   - 新增 scripts：
     - `tauri:dev`
     - `tauri:build`
     - `tauri:build:backend` 或等价命令
   - 不新增大型前端 UI 依赖。

2. `frontend/vite.config.ts`
   - 建议将 dev server 设置为：
     - `port: 5180`
     - `strictPort: true`
   - 避免 Tauri devUrl 指向固定端口时 Vite 自动漂移到其他端口。

3. `backend/app/main.py`
   - 如桌面前端通过 `http://127.0.0.1:8765` 访问 API，不需要新增 CORS。
   - 如 Tauri 前端通过自定义协议访问 API，则需要补充 Tauri origin。Claude Code 应先在实际 Tauri dev 中确认 Origin 后再修改。

4. `.gitignore`
   - 确保忽略：
     - `frontend/src-tauri/target/`
     - Tauri build 输出
     - sidecar 编译产物
   - 如果需要提交 Tauri 构建脚本，添加精确例外：
     - `!frontend/src-tauri/scripts/`
     - `!frontend/src-tauri/scripts/*.ps1`

5. `README.md`
   - 新增“桌面开发/打包”简短说明。
   - 不需要写长篇用户手册。

6. 可选：`backend/requirements.txt`
   - 仅当 Tauri sidecar 打包流程确认缺少 PyInstaller 时添加。
   - 如果 PyInstaller 已在本地 venv 但不在 requirements，Claude Code 应先确认现有构建脚本是否依赖它。

# Implementation Steps for Claude Code

1. 保护当前工作区状态
   - 读取本计划。
   - 执行 `git status --short`。
   - 确认写作统计仪表盘 V1 的未提交改动存在。
   - 不回滚、不重排、不格式化无关业务文件。
   - 如果当前写作统计代码无法编译，先停止并反馈，不要把统计修复混入 Tauri 任务。

2. 确认本机依赖
   - 检查 Node 与 npm：
     - `node --version`
     - `npm --version`
   - 检查 Rust/Cargo：
     - `rustc --version`
     - `cargo --version`
   - 检查 Python venv：
     - `backend\.venv\Scripts\python.exe --version`
   - 检查 PyInstaller：
     - `backend\.venv\Scripts\python.exe -m PyInstaller --version`
   - 如果 Rust 或 PyInstaller 缺失，停止并在执行报告说明，不要临时联网安装，除非用户明确同意。

3. 初始化 Tauri
   - 在 `frontend/` 下创建 `src-tauri/`。
   - 使用 Tauri v2 配置。
   - 不使用 `create-tauri-app` 重建前端项目。
   - 不移动 `frontend/src/`。
   - 不重建 Vue 项目。

4. 配置 Tauri 窗口
   - 应用名：`章枢`
   - 窗口标题：`章枢`
   - 默认尺寸建议：
     - width: `1440`
     - height: `900`
   - 最小尺寸建议：
     - width: `1280`
     - height: `720`
   - 先使用系统标题栏，不做自定义标题栏。
   - 不做托盘、自动更新、开机自启。

5. 配置 Vite dev/build
   - 修改 `frontend/vite.config.ts`：
     - 保留 `port: 5180`。
     - 增加 `strictPort: true`。
   - Tauri devUrl 使用 `http://localhost:5180`。

6. 设置桌面前端 API base
   - 桌面 production 构建必须让前端请求 `http://127.0.0.1:8765/api/...`。
   - 首选方案：
     - 在 Tauri `beforeBuildCommand` 或 npm script 中设置 `VITE_API_BASE_URL=http://127.0.0.1:8765` 后执行 `npm run build`。
   - Windows 命令可用 PowerShell 风格：
     - `$env:VITE_API_BASE_URL='http://127.0.0.1:8765'; npm run build`
   - 如果 Tauri CLI 对该命令兼容性不好，改用一个可提交的构建脚本，并按 `.gitignore` 例外处理。

7. 新增 Tauri sidecar 后端入口
   - 创建 `backend/tauri_sidecar_main.py`。
   - 可参考 `backend/packaged_main.py`，但必须移除：
     - `webbrowser.open`
     - `open_browser_later`
   - 固定默认端口：
     - `ZHANGSHU_BACKEND_PORT`，默认 `8765`
   - 数据目录：
     - 优先使用 `ZHANGSHU_DATA_DIR`。
     - 如果未设置，回退到 sidecar exe 旁的 `zhangshu_data`。
   - 日志目录：
     - `ZHANGSHU_LOG_DIR` 或数据目录下 `logs`。
   - 启动失败写 `startup_error.log`。

8. 打包 backend sidecar
   - 使用 PyInstaller onedir 或 onefile，Claude Code 根据 Tauri sidecar external binary 要求选择。
   - 建议输出到可被 Tauri bundle 引用的位置，例如：
     - `frontend/src-tauri/binaries/zhangshu-backend-x86_64-pc-windows-msvc.exe`
   - 该输出是构建产物，是否提交由 Tauri 规范和项目策略决定：
     - 源码仓库不应提交大体积二进制；
     - 如果 Tauri build 必须读取该文件，则执行报告需说明“构建前生成，不提交”。

9. 在 Tauri Rust 入口中启动 sidecar
   - 使用 Tauri 官方 sidecar 机制。
   - 启动前设置环境变量：
     - `ZHANGSHU_BACKEND_HOST=127.0.0.1`
     - `ZHANGSHU_BACKEND_PORT=8765`
     - `ZHANGSHU_DB_FILENAME=zhangshu.sqlite3`
     - `ZHANGSHU_DATA_DIR=<Tauri app local data dir>/data`
     - `ZHANGSHU_LOG_DIR=<Tauri app local data dir>/logs`
   - sidecar stdout/stderr 可写入 Tauri 日志或开发控制台，但不得输出 API key 或知识库正文。
   - 窗口关闭时终止 sidecar。

10. 端口占用处理
    - V1 固定端口 `8765`。
    - 如果端口占用：
      - sidecar 启动失败；
      - Tauri 前端显示可理解错误，或至少执行报告列为已知限制。
    - 不要在本轮做动态端口注入，除非固定端口方案无法跑通。

11. 不引入 Tauri 原生业务能力
    - 本轮不要做文件夹选择器替换。
    - 不要做系统托盘。
    - 不要做自动更新。
    - 不要做通知。
    - 不要做自定义标题栏。
    - 不要把导入/导出改成 Tauri command。

12. README 更新
    - 简短说明：
      - Web 开发仍用 `start-zhangshu-dev.bat` 或前后端独立命令。
      - 桌面开发使用 `cd frontend && npm run tauri:dev`。
      - 桌面打包使用 `cd frontend && npm run tauri:build`。
      - 桌面版数据存放在本机应用数据目录，不提交到 git。

13. 执行报告
    - Claude Code 完成后生成：
      - `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`
    - 报告必须写明：
      - 是否成功启动 Tauri dev；
      - 是否成功打包；
      - sidecar 输出位置；
      - 数据目录策略；
      - 端口策略；
      - 任何需要用户本机安装的依赖。

# Constraints

1. Codex 未修改业务代码，本计划应由 Claude Code 执行。

2. Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

3. 不要修改业务模块：
   - 项目、章节、人物、设定、伏笔、时间线、关系图、知识库、RAG、统计等功能逻辑不属于本任务。

4. 不要把业务逻辑写入 Tauri Rust 层。

5. 不要重建 Vue 项目。

6. 不要移动 `frontend/src/` 或 `backend/app/`。

7. 不要替换 FastAPI 为 Tauri command。

8. 不要新增大型 UI 库。

9. 不要提交构建产物：
   - `frontend/src-tauri/target/`
   - `release/`
   - `build/`
   - sidecar 编译输出 exe
   - 本地数据库
   - 日志

10. 不要提交 API key、`.env`、`.env.local` 或本地配置。

11. 如需新增 `.ps1` 构建脚本，必须处理 `.gitignore`，否则文件可能不会被跟踪。

12. 先做 Windows V1，不扩大到 macOS/Linux。

# Verification Commands

检查基础依赖：

```powershell
node --version
npm --version
rustc --version
cargo --version
backend\.venv\Scripts\python.exe --version
backend\.venv\Scripts\python.exe -m PyInstaller --version
```

前端现有验证：

```powershell
cd frontend
npm run type-check
npm run build
```

后端现有验证：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

构建 sidecar：

```powershell
cd frontend
npm run tauri:build:backend
```

Tauri dev：

```powershell
cd frontend
npm run tauri:dev
```

Tauri build：

```powershell
cd frontend
npm run tauri:build
```

桌面手动验收：

- 启动桌面应用；
- 确认窗口标题为 `章枢`；
- 确认后端 sidecar 自动启动；
- 打开项目列表；
- 打开一个项目；
- 保存章节；
- 打开知识库或统计页；
- 关闭窗口后确认 sidecar 进程退出；
- 确认数据写入应用数据目录，而不是仓库 `data/`；
- 确认 `git status --short` 中没有构建产物和本地数据。

# Acceptance Criteria

1. `frontend/src-tauri/` 存在，并且是最小 Tauri v2 壳。

2. `npm run tauri:dev` 能启动桌面窗口。

3. 桌面窗口可以加载现有 Vue 前端。

4. 桌面窗口内 API 请求能打到本地 FastAPI sidecar。

5. FastAPI sidecar 不会打开系统浏览器。

6. 桌面应用使用独立本地数据目录，不默认写入仓库 `data/`。

7. 关闭桌面窗口后，sidecar 进程不会残留。

8. 普通前端和后端 Web 开发命令仍可用。

9. `npm run type-check` 通过。

10. `npm run build` 通过。

11. 后端 pytest 通过，或执行报告明确说明失败原因与是否和本任务相关。

12. `npm run tauri:build` 能生成 Windows 桌面包，或执行报告明确说明阻塞原因。

13. 没有把业务逻辑搬进 Tauri/Rust。

14. 没有提交构建产物、数据库、日志、密钥或 `.env`。

15. README 有简短桌面开发/打包说明。

# Risks and Watchpoints

1. Tauri 依赖本机 Rust 工具链：
   - 如果用户机器没有 Rust，Claude Code 不能擅自联网安装。
   - 应在执行报告说明需要安装 Rust。

2. PyInstaller 可能不在 requirements 中：
   - 现有构建脚本已使用 PyInstaller。
   - 如果本地 venv 没有安装，需反馈，不要临时改依赖。

3. 固定端口 `8765` 有占用风险：
   - V1 可接受，但必须清楚提示。
   - 后续可做动态端口注入。

4. 前端 API base 是关键风险：
   - Web dev、Web production、Tauri dev、Tauri production 可能需要不同 API base。
   - Claude Code 必须实际验证桌面窗口里的 API 请求，不只看构建通过。

5. CORS 风险：
   - 如果桌面前端通过 Tauri 自定义协议访问 `127.0.0.1` API，可能需要补充 CORS origin。
   - 不要猜 origin；应在实际 devtools 或请求头中确认。

6. sidecar 生命周期：
   - 如果 Tauri 关闭但 sidecar 残留，会导致端口占用和数据锁。
   - 必须验证关闭窗口后进程退出。

7. 数据目录迁移：
   - Web 开发使用仓库 `data/`。
   - 桌面版使用应用数据目录。
   - 这会导致同一项目在 Web dev 和桌面版里不是同一个数据库，这是 V1 可接受行为，但 README 要说明。

8. 现有 `backend/packaged_main.py` 不应被破坏：
   - 它可能仍用于旧版 exe 打包。
   - Tauri sidecar 建议新增入口，避免影响旧打包流程。

9. `.gitignore` 当前很激进：
   - `*.ps1` 和 `scripts/` 被忽略。
   - 新增构建脚本时容易漏提交。

10. 当前工作区已有未提交写作统计改动：
    - Tauri 任务不要顺手修写作统计。
    - 执行报告需列明哪些改动属于本任务，哪些是已有改动。

# Review Checklist

Claude Code 执行完成后，Codex 复审时必须读取：

- `docs/ai-handoff/CODEX_PLAN.md`
- `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`
- 当前 `git diff`

复审重点：

1. 是否只新增/修改 Tauri 壳、sidecar 启动、打包配置和必要说明文件。

2. 是否没有改动业务逻辑。

3. 是否没有把项目、章节、知识库、RAG、统计等业务写进 Rust。

4. `frontend/src-tauri/` 是否是最小可维护结构。

5. sidecar 是否使用专用入口，不会打开系统浏览器。

6. sidecar 是否读取应用数据目录环境变量。

7. 桌面前端 API base 是否在 Tauri dev/build 中可用。

8. 是否处理了 fixed port 失败提示或记录为已知限制。

9. 窗口关闭后 sidecar 是否退出。

10. README 是否清楚说明 Web 开发与桌面开发的区别。

11. `.gitignore` 是否没有误忽略应提交的 Tauri 配置/脚本。

12. git diff 中是否没有：
    - `frontend/src-tauri/target/`
    - sidecar exe
    - `release/`
    - `build/`
    - `data/`
    - `logs/`
    - `.env`
    - API key

13. `npm run type-check`、`npm run build`、后端 pytest、`npm run tauri:dev`、`npm run tauri:build` 的执行结果是否在报告中说明。

14. 如 Tauri build 未通过，是否属于环境缺失，而不是代码结构错误。

15. 最终建议应为 Accept、Minor Revision 或 Rework。
