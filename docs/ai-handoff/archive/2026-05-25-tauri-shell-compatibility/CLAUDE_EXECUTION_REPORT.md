---
archived_at: 2026-05-25
archive_reason: Tauri shell compatibility small fixes completed; moving to cloud architecture discussion
date: 2026-05-25
task: Tauri 桌面壳兼容性回归与小修
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

对 Tauri 桌面壳做兼容性检查和小修。修复了两个已知兼容风险：ReviewCheckPage 的 `:has()` CSS 选择器和两个页面的"更多"菜单缺少点击外部/Esc 关闭。Tauri Rust 编译成功，前端构建正确注入 API base URL。

## Files Changed

- 修改：`frontend/src/pages/review/ReviewCheckPage.vue`
  - 将 segmented control 的 `:has()` CSS 选择器替换为 Vue `:class` 绑定（`.active` class）
  - 添加 `onBeforeUnmount` 清理、`document.addEventListener('pointerdown', handleOutsideClick)` 和 `document.addEventListener('keydown', handleKeyDown)` 实现更多菜单点击外部和 Esc 关闭
- 修改：`frontend/src/pages/knowledge/ProjectKnowledgePage.vue`
  - 添加 `document.addEventListener('keydown', handleKeyDown)` 实现更多菜单 Esc 关闭（click-outside 已有）
  - `onBeforeUnmount` 中清理 keydown 监听

## Implementation Notes

### ReviewCheckPage :has() 修复
- 原有 CSS：`.segmented-control label:has(input[type="radio"]:checked)` 用于高亮选中项
- 改为 Vue class 绑定：`<label :class="{ active: scope === 'chapter' }">`
- 新增 CSS：`.segmented-control label.active` 和 `.segmented-control label.active span`
- 消除了 WebView2 中 `:has()` 选择器的潜在兼容风险

### 更多菜单关闭逻辑
- ReviewCheckPage：添加 `handleOutsideClick`（检查 `.more-menu-wrapper`）和 `handleKeyDown`（Esc 键）
- KnowledgePage：添加 `handleKeyDown`（Esc 键），click-outside 已通过 `document.addEventListener('click', closeMoreMenu)` 实现
- 两个页面均在 `onBeforeUnmount` 中正确清理事件监听，避免内存泄漏

### Tauri 构建配置确认
- `tauri.conf.json` 配置正确：默认窗口 1440×900，最小窗口 1280×720
- `VITE_API_BASE_URL=http://127.0.0.1:8765` 通过 cross-env 正确注入
- Sidecar 配置：`binaries/zhangshu-backend`
- 中文应用名"章枢"和窗口标题配置正确

## Deviations from Codex Plan

无偏差。计划要求修复 `:has()` 和菜单关闭逻辑，均已实现。

## Verification Commands Run

- `npm run type-check` → ✅
- `npm run build` → ✅
- `npm run test:unit -- --run` → ✅ (8 files, 115 tests)
- `npm run tauri:build` → ⚠️ Rust 编译成功，WiX MSI 打包失败（环境问题）

## Verification Results

### 基础构建
- type-check、build、unit tests 全部通过
- 前端正确构建，API base URL 注入正确

### Tauri 构建
- ✅ Rust 后端编译成功（tauri 2.11.2, tauri-build 2.6.2）
- ✅ 前端构建成功，生成 dist/
- ✅ 生成独立 exe：`src-tauri/target/release/zhangshu-desktop.exe` (11MB)
- ❌ WiX MSI 打包失败：`light.exe` 执行失败（本机 WiX 工具环境问题）
- 根据计划："若因本机缺少 Windows 打包工具、证书、NSIS/WiX 或环境问题失败，Claude Code 应记录为环境阻塞，不要改业务代码绕过"

### 环境检查
- Tauri CLI: 2.11.2
- WebView2: 148.0.3967.83
- Rust: 1.95.0 (stable-x86_64-pc-windows-msvc)
- Node: 24.14.1
- cross-env: 已安装

## Known Issues

### 需要手动验证（无法在 CLI 环境中执行）
1. **Tauri dev 启动验证**：需要 GUI 环境，无法在 CLI 中运行 `npm run tauri:dev`
2. **打包应用启动验证**：已生成 exe，但需要手动启动验证首屏加载、API 连接、CORS
3. **CORS 风险**：Tauri production origin 可能是 `tauri://localhost` 或 `https://tauri.localhost`，当前 CORS 配置只包含 `localhost:5180` 和 `127.0.0.1:5180`。如实际测试出现 CORS 错误，需添加 Tauri production origin
4. **文件上传/下载验证**：需要在 Tauri 壳内测试 `webkitdirectory`、Blob URL 下载、文件选择器
5. **最小窗口和缩放验证**：需要在 1280×720 和 125% 缩放下检查布局
6. **主题验证**：需要在 Tauri 壳内测试默认、护眼、黑夜主题

### 未修改项
- **CORS 配置**：根据计划"仅当实际 Tauri production origin 导致 CORS 失败时，做最小 CORS origin 修复"。因无法实际运行 Tauri production 验证，未预防性修改
- **tauri.conf.json**：配置正确，无需修改
- **tauri_sidecar_main.py**：UTF-8 编码正确，中文日志正常，无需修改
- **其他工具页**：未发现问题，根据计划"只有确认存在兼容问题时才修改对应文件"

## Suggested Next Review Points for Codex

1. **CORS 配置**：建议在实际 Tauri production 启动后，如出现 CORS 错误，添加 `tauri://localhost` 和 `https://tauri.localhost` 到 `backend/app/main.py` 的 `allow_origins`
2. **WiX 打包**：需要修复本机 WiX 工具环境，或改用 NSIS 打包（修改 `tauri.conf.json` 的 `bundle.targets`）
3. **文件下载**：Tauri WebView2 中 Blob URL 下载行为可能与浏览器不同，建议实际测试 DOCX/备份导出
4. **webkitdirectory**：需要在 Tauri 壳内测试文件夹选择器，如不可用需确保 zip fallback 入口清晰
