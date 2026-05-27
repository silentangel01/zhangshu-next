<!-- archived: 2026-05-25; task: tauri-shell-compatibility -->

# Task Summary

本次任务调整为 **Tauri 桌面壳兼容性回归与小修计划**。

用户明确要求：不需要大重构，只需要确保现有工具页和关键流程在打包进 Tauri 壳子后不会出现兼容性 bug。

本计划只要求 Claude Code 做兼容性检查和必要小修，不做工具页大规模 UI 统一，不新增业务功能，不重写页面。

重点检查：

- Tauri dev / build 下前端是否能正确连接 sidecar 后端。
- 打包后 API base、CORS、静态资源路径、文件上传、下载导出是否正常。
- Windows WebView2 中 CSS、菜单、弹窗、文件选择、窗口尺寸是否稳定。
- 深色 / 护眼主题在桌面壳内是否完整生效。
- 工具页在 Tauri 最小窗口尺寸下不出现横向溢出、按钮不可见或弹窗被裁切。

Codex 未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

已检查当前交接区：

- `docs/ai-handoff/` 当前只有 `README.md` 和 `archive/`，没有旧活跃计划或执行报告。

已检查 Tauri 与前端配置：

- `frontend/src-tauri/` 已存在。
- `frontend/src-tauri/tauri.conf.json`
  - 默认窗口约为 `1440 × 900`。
  - 最小窗口约为 `1280 × 720`。
  - `devUrl` 为 `http://localhost:5180`。
  - `frontendDist` 为 `../dist`。
  - sidecar 配置为 `binaries/zhangshu-backend`。
- `frontend/package.json`
  - `tauri:dev` 使用 `VITE_API_BASE_URL=http://127.0.0.1:8765`。
  - `tauri:build:frontend` 使用 `VITE_API_BASE_URL=http://127.0.0.1:8765 npm run build`。
  - `tauri:build` 先构建前端，再执行 `tauri build`。
  - `tauri:build:backend` 使用 PyInstaller 生成 sidecar。
- `frontend/vite.config.ts`
  - Vite dev server 端口为 `5180`，且 `strictPort: true`。
- `frontend/src/shared/api/client.ts`
  - API base 来自 `import.meta.env.VITE_API_BASE_URL ?? ''`。
  - Tauri dev / build 依赖构建脚本注入 `http://127.0.0.1:8765`。
- `backend/tauri_sidecar_main.py`
  - sidecar 默认监听 `127.0.0.1:8765`。
  - 数据目录默认为 sidecar 所在目录下的 `zhangshu_data`，可通过环境变量覆盖。
  - 端口占用或启动失败会写入 `startup_error.log`。

已知 Tauri V1 执行报告中留下的风险点：

- `npm run tauri:dev` 曾成功启动桌面窗口和 sidecar。
- `npm run tauri:build` 当时未完整执行，需要补充打包验证。
- Tauri production 模式下前端 origin、CORS、静态资源协议仍需实际验证。
- sidecar 构建和打包流程当前主要面向 Windows。

已检查近期工具页状态：

- `frontend/src/pages/search/SearchPage.vue`
- `frontend/src/pages/review/ReviewCheckPage.vue`
- `frontend/src/pages/stats/ProjectWritingStatsPage.vue`
- `frontend/src/pages/imports/ProjectBackupPage.vue`
- `frontend/src/pages/imports/ImportPage.vue`
- `frontend/src/pages/versions/ProjectVersionsPage.vue`
- `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`
- `frontend/src/features/knowledge/KnowledgeImportDialog.vue`
- `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue`

这些页面中可能影响 Tauri 壳兼容性的点：

- 下拉菜单如果只靠再次点击按钮关闭，在桌面壳内体验不稳定，应支持点击外部和 Esc 关闭。
- `ReviewCheckPage.vue` 曾使用 CSS `:has()` 处理选中态，虽然 WebView2 通常支持，但为降低壳内兼容风险，建议改为 Vue class 绑定。
- 知识库和导入页使用文件选择、批量文件、文件夹选择、zip 上传，需要在 Tauri WebView2 中验证。
- 导出和备份下载依赖浏览器下载行为，需要确认 Tauri 壳内是否能正确保存文件或触发下载。
- 窗口最小宽度为 `1280 × 720`，但仍需要检查 `1100 × 760` 或用户手动缩放场景，避免布局被标题栏、系统缩放或侧栏挤坏。
- 控制台输出中出现过中文显示异常的迹象，需要确认 Tauri 窗口标题、应用名、sidecar 日志文件是否为正确 UTF-8。

# Architecture Decision

本次任务采用 **兼容性优先、最小修改** 策略。

允许 Claude Code 做：

- 验证 Tauri dev 和 Tauri build。
- 修复会导致桌面壳中不可用、报错、看不见、点不了、下载不了、上传不了的问题。
- 修复明显的 WebView2 兼容风险，例如关键交互依赖 `:has()`。
- 修复下拉菜单点击外部 / Esc 关闭问题。
- 修复 Tauri 壳内 API base、CORS、静态资源路径、窗口尺寸、文件上传下载相关问题。
- 小范围修复工具页在 Tauri 最小窗口下的横向溢出、弹窗裁切、按钮不可见。

不允许 Claude Code 做：

- 大规模 UI 统一。
- 抽象新的设计系统。
- 重写工具页。
- 重构业务逻辑。
- 新增业务功能。
- 为了“顺手好看”调整无关页面。
- 引入大型依赖或 UI 库。

判断标准：

- 如果问题会导致 Tauri 壳中功能不可用或出现兼容 bug，可以修。
- 如果只是视觉风格不够统一，但不影响壳内可用性，本任务不修。

# Files to Create or Modify

Claude Code 应先验证，只有确认存在兼容问题时才修改对应文件。

可能需要修改的文件：

- `frontend/src/pages/review/ReviewCheckPage.vue`
  - 修复更多菜单外部点击 / Esc 关闭。
  - 如仍依赖 `:has()`，改为 Vue class 绑定。

- `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`
  - 修复更多菜单外部点击 / Esc 关闭。
  - 检查知识库浏览、检索、问答、摘要在 Tauri 最小窗口下是否溢出。

- `frontend/src/pages/search/SearchPage.vue`
  - 仅当 Tauri 壳内搜索索引刷新、结果打开、布局溢出出现兼容问题时小修。

- `frontend/src/pages/imports/ImportPage.vue`
  - 仅当 Tauri 壳内文件选择、文件夹选择、项目包导入、zip 上传出现问题时小修。

- `frontend/src/pages/imports/ProjectBackupPage.vue`
  - 仅当 Tauri 壳内 DOCX/TXT/MD 导出、备份下载、备份恢复上传出现问题时小修。

- `frontend/src/pages/versions/ProjectVersionsPage.vue`
  - 仅当 Tauri 壳内版本恢复确认、版本 diff 展示、清理旧版本确认出现兼容问题时小修。

- `frontend/src/pages/stats/ProjectWritingStatsPage.vue`
  - 仅当 Tauri 壳内统计图表、热力图、窗口缩放出现布局问题时小修。

- `frontend/src/shared/api/client.ts`
  - 仅当 Tauri production build 中 API base 不正确时修改。
  - 不要改变普通 Web dev 的默认相对路径行为。

- `backend/app/main.py`
  - 仅当实际 Tauri production origin 导致 CORS 失败时，做最小 CORS origin 修复。
  - 不要修改业务 API。

- `backend/tauri_sidecar_main.py`
  - 仅当 sidecar 启动、中文日志、数据目录、端口冲突提示在打包后存在实际问题时小修。

- `frontend/src-tauri/tauri.conf.json`
  - 仅当打包配置、窗口最小尺寸、bundle sidecar 配置存在实际问题时小修。

- `frontend/package.json`
  - 仅当现有 Tauri scripts 不能完成打包验证时小修。
  - 不新增无关脚本，不改普通 Web dev/build 命令语义。

不应修改：

- 数据库模型、Repository、Service、业务 Schema。
- 工具页业务流程。
- 路由结构。
- 大型全局样式。
- 依赖版本，除非打包验证明确需要且用户确认。
- `data/`、`logs/`、`release/`、`frontend/src-tauri/target/` 等本地产物。

# Implementation Steps for Claude Code

1. 执行前检查
   - 运行：

```powershell
git status --short
```

   - 阅读本计划。
   - 确认本任务是 Tauri 壳兼容性回归，不是 UI 大重构。

2. 基础构建验证
   - 在 `frontend/` 执行：

```powershell
npm run type-check
npm run build
```

   - 如失败，先判断是否与本任务相关。
   - 不要顺手修复无关业务问题；如发现无关失败，写入执行报告并停止或询问。

3. Tauri dev 验证
   - 在 `frontend/` 执行：

```powershell
npm run tauri:dev
```

   - 验证：
     - Tauri 窗口能打开。
     - sidecar 能启动。
     - `/health` 或项目列表 API 请求成功。
     - 普通 Web dev 不受影响。
     - 窗口标题和应用名中文正常。
     - 控制台无明显前端错误。

4. Tauri build 验证
   - 如 sidecar exe 不存在或过期，先执行：

```powershell
npm run tauri:build:backend
```

   - 然后执行：

```powershell
npm run tauri:build
```

   - 若因本机缺少 Windows 打包工具、证书、NSIS/WiX 或环境问题失败，Claude Code 应记录为环境阻塞，不要改业务代码绕过。
   - 若因项目配置、API base、sidecar 路径、CORS、静态资源路径失败，做最小修复。

5. Tauri production 包手动启动验证
   - 找到 `frontend/src-tauri/target/release/bundle/` 下生成的包或可执行文件。
   - 启动打包后的应用。
   - 验证：
     - 首屏加载正常。
     - 项目列表能加载。
     - 进入已有项目能加载写作工作区。
     - API 请求指向 `127.0.0.1:8765`。
     - 没有 CORS 错误。
     - 退出应用后 sidecar 不残留异常进程。

6. 工具页壳内兼容性 smoke test
   - 在 Tauri dev 或打包应用中逐页检查：
     - `/projects/:projectId/search`
     - `/projects/:projectId/review`
     - `/projects/:projectId/stats`
     - `/projects/:projectId/backup`
     - `/imports`
     - `/projects/:projectId/versions`
     - `/projects/:projectId/knowledge`
   - 每页只检查壳内兼容性，不做 UI 大改。

7. 文件上传与导入验证
   - 在 Tauri 壳内检查：
     - 作品导入选择单个 `.txt` / `.md` / `.docx` 文件。
     - 作品导入选择文件夹。
     - 项目包 `.zip` 选择。
     - 知识库批量导入选择文件。
     - 知识库批量导入选择文件夹。
     - 知识库导入 `.zip`。
   - 如果 `webkitdirectory` 在 WebView2 中不可用，应保留 zip 导入作为 fallback，并在 UI 上确保用户能找到 fallback。
   - 不改变导入业务逻辑。

8. 文件下载与导出验证
   - 在 Tauri 壳内检查：
     - TXT 导出。
     - Markdown 导出。
     - DOCX 导出。
     - 项目备份 zip 导出。
     - 词库导出。
   - 如果 `a.download`、Blob URL 或浏览器下载行为在 Tauri 壳中不可用，应优先使用 Tauri shell 已允许能力或现有浏览器可用方式的最小兼容修复。
   - 不改变导出内容格式。

9. 菜单与弹窗兼容性修复
   - 检查 Review 和 Knowledge 的“更多”菜单。
   - 如不能点击外部关闭或 Esc 关闭，按最小方式修复：
     - `document.addEventListener('pointerdown', ...)`
     - `document.addEventListener('keydown', ...)`
     - `onBeforeUnmount` 清理监听。
   - 避免为此创建复杂新组件。
   - 检查弹窗：
     - 知识库导入弹窗。
     - 刷新知识索引弹窗。
     - 版本恢复弹窗。
     - 导入预览/确认相关面板。
   - 确保在 Tauri 最小窗口下不被裁切到无法操作。

10. CSS / WebView2 兼容性修复
    - 检查关键交互是否依赖 `:has()`。
    - 如 Review 检查范围仍用 `:has()`，改为 Vue class active。
    - 不要求移除所有现代 CSS，只处理关键功能选中态、菜单、弹窗、布局。
    - 检查 `position: fixed`、`overflow`、`max-height: 90vh` 在壳内是否正常。
    - 检查深色和护眼主题下菜单、弹窗、空状态、图表是否可读。

11. Tauri 最小窗口与缩放验证
    - 检查尺寸：
      - 默认 `1440 × 900`
      - 最小 `1280 × 720`
      - 手动缩小或系统缩放近似 `1100 × 760`
      - 125% 缩放
    - 验证：
      - 页面无全局横向滚动。
      - 主按钮没有被挤出屏幕。
      - 下拉菜单没有被裁切。
      - 弹窗底部按钮可见。
      - 画布类页面不因主题改变 canvas 背景色。

12. 中文与编码验证
    - 检查 Tauri 窗口标题、应用名、sidecar 日志、错误日志中的中文是否正常。
    - 如发现 `章枢` 显示为乱码，只修正对应配置或日志字符串编码问题。
    - 不改业务文案。

13. 执行报告
    - Claude Code 必须写入：

`docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`

   - 报告必须包含：
     - 执行了哪些命令。
     - Tauri dev 是否通过。
     - Tauri build 是否通过。
     - 打包应用是否实际启动验证。
     - 哪些工具页做了壳内 smoke test。
     - 上传/下载/导入/导出验证结果。
     - 是否发现 CORS、API base、静态资源、WebView2 CSS、菜单、弹窗、中文编码问题。
     - 实际修改了哪些文件。
     - 未修复问题和原因。

# Constraints

- 不做大重构。
- 不做工具页全面统一。
- 不新增业务功能。
- 不修改业务数据结构。
- 不修改路由。
- 不引入新依赖。
- 不重写页面。
- 不重写 Tauri 壳。
- 不提交或保留本地打包产物。
- 不提交 `data/`、`logs/`、`release/`、`frontend/src-tauri/target/`。
- 只有确认存在 Tauri 壳兼容问题时才修改对应文件。
- 所有修复必须是最小必要修复。
- 如果打包失败是本机环境问题，应记录阻塞原因，不要用代码绕过。

# Verification Commands

基础前端验证：

```powershell
cd frontend
npm run type-check
npm run build
```

Tauri dev 验证：

```powershell
cd frontend
npm run tauri:dev
```

sidecar 构建：

```powershell
cd frontend
npm run tauri:build:backend
```

Tauri 打包验证：

```powershell
cd frontend
npm run tauri:build
```

可选后端导入检查：

```powershell
cd backend
python -c "import app.main; print('backend import ok')"
```

手动壳内 smoke test：

- 打开项目列表。
- 打开一个项目。
- 打开搜索、检查、统计、导出备份、导入、版本、知识库页面。
- 测试文件上传、文件夹上传、zip 上传。
- 测试 TXT / MD / DOCX / 项目备份 zip 下载。
- 测试更多菜单点击外部关闭和 Esc 关闭。
- 测试默认、护眼、黑夜主题。
- 测试最小窗口和 125% 缩放。

# Acceptance Criteria

- `npm run type-check` 通过。
- `npm run build` 通过。
- `npm run tauri:dev` 能启动桌面窗口和 sidecar。
- `npm run tauri:build` 能完成，或执行报告明确说明环境阻塞且不是项目配置问题。
- 打包后的应用能启动并加载首屏。
- 打包后的应用能访问 sidecar API，没有 CORS 或 API base 错误。
- 搜索、检查、统计、导入、导出备份、版本、知识库页面在 Tauri 壳内能打开。
- 文件上传、文件夹导入或 zip fallback 在 Tauri 壳内可用。
- TXT / MD / DOCX / 项目备份 zip 下载在 Tauri 壳内可用，或报告明确记录当前 Tauri 下载限制和最小修复建议。
- 更多菜单支持点击外部关闭、Esc 关闭、菜单项点击后关闭。
- 关键选中态不依赖有兼容风险的 CSS `:has()`。
- 最小窗口下无全局横向滚动，弹窗按钮不被裁切。
- 默认、护眼、黑夜主题在壳内可读。
- 中文应用名、窗口标题和错误日志不出现乱码。
- 未进行大重构，未修改无关业务代码。

# Risks and Watchpoints

- Tauri production 的 origin 可能不同于 Web dev，CORS 需要实际验证后再修。
- Tauri 静态资源协议可能暴露 API base 配置问题，不能只跑 Web `npm run build`。
- 文件下载在 WebView2 中可能和浏览器下载行为不同，需要实际壳内验证。
- `webkitdirectory` 在桌面 WebView 中应实测，不要假设完全等同浏览器。
- 打包失败可能来自本机缺少构建工具，不一定是代码问题。
- sidecar 端口 `8765` 可能被占用，需要确认错误提示清楚，但不要本任务扩展为动态端口架构。
- 修改 CORS 时不要放开过宽 origin。
- 修复菜单关闭逻辑时注意清理 document listener，避免内存泄漏或多次触发。
- 不要为了兼容性检查顺手做工具页 UI 统一。
- 不要提交 PyInstaller 输出、Tauri target、日志、数据库或本地配置。

# Review Checklist

- [ ] Claude Code 是否遵守“不做大重构，只做 Tauri 兼容性小修”？
- [ ] 是否没有修改无关业务代码？
- [ ] 是否没有修改数据库、Repository、Service、业务 Schema？
- [ ] 是否执行并记录 `npm run type-check`？
- [ ] 是否执行并记录 `npm run build`？
- [ ] 是否执行并记录 `npm run tauri:dev`？
- [ ] 是否执行并记录 `npm run tauri:build`，或说明环境阻塞？
- [ ] 打包应用是否实际启动验证？
- [ ] Tauri production 下 API base 是否正确？
- [ ] 是否没有 CORS 错误？
- [ ] 文件上传、文件夹导入或 zip fallback 是否可用？
- [ ] TXT / MD / DOCX / 项目备份 zip 下载是否可用？
- [ ] 更多菜单是否支持点击外部和 Esc 关闭？
- [ ] 是否规避了关键 `:has()` 兼容风险？
- [ ] 最小窗口和 125% 缩放下是否无全局横向滚动？
- [ ] 弹窗底部按钮是否始终可见？
- [ ] 默认、护眼、黑夜主题是否在壳内可读？
- [ ] 中文窗口标题、应用名、日志是否正常？
- [ ] 是否没有提交 `data/`、`logs/`、`release/`、`frontend/src-tauri/target/` 或本地打包产物？
