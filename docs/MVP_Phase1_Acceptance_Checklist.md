# MVP Phase 0 / Phase 1 验收清单

更新时间：2026-05-21

## 验收说明

- 状态含义：
  - Pass：已通过自动检查、接口检查或当前实现确认。
  - Partial：功能存在，但本次未完成端到端浏览器人工验证，或存在已知限制。
  - Fail：当前检查失败。
- 本轮回归不新增功能；仅记录 MVP Phase 0 / Phase 1 覆盖情况。
- 本轮自动检查结果：
  - Backend compile：Pass，`.\.venv\Scripts\python.exe -m compileall app`
  - Frontend type check：Pass，`npx vue-tsc --noEmit -p tsconfig.app.json`
  - Backend `/health`：Pass，返回 `{"status":"ok","service":"zhangshu-local-api"}`
  - Backend `/docs`：Pass，HTTP 200
  - Frontend dev server：Partial，本轮检查时 `http://127.0.0.1:5173` 未运行

## 推荐测试命令

### Backend

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd F:\zhangshu\frontend
npm run dev
```

### Frontend Type Check

```powershell
cd F:\zhangshu\frontend
npx vue-tsc --noEmit -p tsconfig.app.json
```

### Backend Smoke Check

- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

## Phase 0 清单

| 编号 | 项目 | 状态 | 验收记录 |
| --- | --- | --- | --- |
| P0-01 | Backend starts | Pass | 后端服务已在 `127.0.0.1:8000` 响应。 |
| P0-02 | `/health` works | Pass | `/health` 返回服务状态 JSON。 |
| P0-03 | SQLite initializes | Pass | 后端启动可访问；`compileall` 通过；现有 `init_database()` 覆盖表创建。 |
| P0-04 | Project CRUD works | Partial | API 和页面已实现；本轮未执行完整新增/编辑/删除人工流程。 |
| P0-05 | Volume CRUD works | Partial | API 和写作页树操作已实现；本轮未执行完整人工流程。 |
| P0-06 | Chapter CRUD works | Partial | API、编辑器和树操作已实现；本轮未执行完整人工流程。 |
| P0-07 | Frontend starts | Partial | Type check 通过；本轮检查时 dev server 未运行，需要执行 `npm run dev` 复验。 |
| P0-08 | Project list opens | Partial | 路由存在；需要浏览器打开 `/projects` 复验。 |
| P0-09 | Writing page opens | Partial | 路由 `/projects/:projectId` 存在；需要浏览器复验。 |
| P0-10 | Chapter content saves and persists | Partial | 手动保存/自动保存逻辑存在；需要浏览器端创建内容后刷新确认。 |

## Phase 1 清单

| 编号 | 项目 | 状态 | 验收记录 |
| --- | --- | --- | --- |
| P1-01 | Volume/chapter tree create/rename/sort/delete | Partial | 树和 API 已实现；本轮未做完整浏览器拖拽/删除复验。 |
| P1-02 | Manual save | Partial | 编辑器手动保存逻辑和失败保护存在；需要浏览器端复验。 |
| P1-03 | Autosave | Partial | 编辑器 2 秒延迟自动保存逻辑存在；需要浏览器端复验。 |
| P1-04 | Save status | Partial | 保存状态文案存在；需要浏览器观察状态切换。 |
| P1-05 | Chapter versions | Partial | 版本 API 和面板已实现；需要浏览器创建快照复验。 |
| P1-06 | Version restore | Partial | 恢复 API 和确认流程已实现；需要浏览器复验无误。 |
| P1-07 | Recovery drafts | Pass | 已新增本地 + 后端恢复稿链路；后端恢复稿 smoke test 在 Step 24 通过。 |
| P1-08 | Project backup | Pass | 备份 API、zip manifest 和前端入口已实现；Step 19 smoke test 通过。 |
| P1-09 | Backup restore | Pass | 恢复为新项目、ID 映射和报告已实现；Step 19 smoke test 通过。 |
| P1-10 | Import preview | Pass | 新增 `/api/projects/import/preview`，预览不写正式项目；Step 23 smoke test 通过。 |
| P1-11 | Import commit | Pass | 新增 `/api/projects/import/commit`，支持新项目/已有项目；Step 23 smoke test 通过。 |
| P1-12 | Export txt/md/docx if implemented | Partial | TXT/Markdown 已实现；DOCX 导出明确暂未支持。 |
| P1-13 | Search | Pass | LIKE 搜索标题/正文已实现；Step 21 smoke test 通过。 |
| P1-14 | Review check | Pass | 违禁词表、检查结果和页面已实现；Step 22 smoke test 通过。 |
| P1-15 | Chinese text and encoding | Pass | 后端 JSON/导出/导入均使用 UTF-8；多轮中文 smoke test 正常。 |
| P1-16 | Refresh restores selected chapter | Partial | 工作区 `localStorage` 恢复已实现；需要浏览器刷新复验。 |
| P1-17 | No obvious console errors | Partial | Type check 通过；本轮未打开浏览器控制台人工检查。 |

## 本轮发现的问题

| 问题 | 状态 | 说明 |
| --- | --- | --- |
| Frontend dev server 未运行 | 未修复，非代码问题 | `http://127.0.0.1:5173` 无法连接。需要本地执行 `npm run dev` 后复验页面。 |
| 浏览器端人工流程未完整执行 | 未修复，需人工验收 | 包括拖拽排序、保存状态观察、控制台错误检查等。 |
| DOCX manuscript export | 已知限制 | 当前仅 TXT/Markdown 导出；DOCX 导出暂未支持。 |

## 剩余 MVP 风险

1. 浏览器端端到端流程仍需人工复验，尤其是编辑器保存、自动保存、刷新恢复和版本恢复。
2. 前端生产构建在当前沙箱中曾多次因 Vite `spawn EPERM` 失败；type check 通过，但仍建议在正常本机终端执行一次 `npm run build`。
3. 导入 DOCX 仅做基础段落文本提取，不覆盖复杂 Word 结构。
4. 搜索使用 SQLite LIKE，项目规模变大后可能需要 FTS5。
5. 恢复稿以后端和本地时间戳选择最新稿，极端时钟差异场景仍需人工判断。
