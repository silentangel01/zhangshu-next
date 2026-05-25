---
archived_at: 2026-05-25
archive_reason: DOCX export, project package import, and outline drag sorting completed; preparing SQLite FTS5 and version management plan
date: 2026-05-25
task: DOCX 导出 + 项目包导入 + 大纲拖拽排序
codex_plan: docs/ai-handoff/CODEX_PLAN.md (三项能力)
status: COMPLETED
---

## Task Summary

实现三项功能：DOCX 正文导出、章枢完整项目包导入、大纲拖拽排序。

## Files Changed

### Step 1 — DOCX 正文导出

- 修改：`backend/requirements.txt` — 新增 `python-docx>=1.1,<2.0` 依赖
- 新增：`backend/app/infrastructure/docx_exporter.py` — `render_manuscript_docx()` 函数，将 `ManuscriptDocument` 渲染为 DOCX bytes
- 修改：`backend/app/services/export_service.py` — 移除 DOCX 的 `ExportUnsupportedFormatError` 分支，添加 DOCX 渲染路径（lazy import 避免循环依赖）
- 修改：`frontend/src/pages/imports/ProjectBackupPage.vue` — 移除 DOCX 前端禁用判断和提示文案
- 新增：`backend/tests/test_export_service.py` — 5 个测试（DOCX 全书/分卷/章节导出 + TXT/MD 回归）

### Step 2 — 章枢完整项目包导入

- 修改：`backend/app/services/backup_service.py` — 抽出 `inspect_project_backup()` 只读方法和 `restore_from_payload()` 公共方法，`restore_project_backup()` 改为调用公共方法（消除重复）
- 新增：`backend/app/services/project_package_import_service.py` — `preview_package()` 和 `confirm_package()`，使用临时文件存储预览
- 新增：`backend/app/schemas/project_package_import.py` — 预览和确认请求/响应 schema
- 修改：`backend/app/api/imports.py` — 新增 `POST /api/imports/project-package/preview` 和 `POST /api/imports/project-package/confirm`（路由顺序放在 `/{import_id}/confirm` 之前避免通配符冲突）
- 修改：`frontend/src/entities/import/types.ts` — 新增 `ProjectPackageEntityCounts`、`ProjectPackageImportPreview`、`ProjectPackageImportConfirm` 类型
- 修改：`frontend/src/entities/import/api.ts` — 新增 `previewProjectPackageImport()`、`confirmProjectPackageImport()`
- 修改：`frontend/src/pages/imports/ImportPage.vue` — 新增 tab 切换（导入正文 / 导入章枢项目包），项目包导入 UI 含预览实体数量展示和确认导入
- 新增：`backend/tests/test_project_package_import.py` — 5 个测试（预览、非法 zip、确认导入、缺失预览、只读检查）

### Step 3 — 大纲拖拽排序

- 修改：`backend/app/schemas/outline.py` — 新增 `OutlineReorderItem`、`OutlineReorderRequest`、`OutlineReorderResponse`
- 修改：`backend/app/services/outline_service.py` — 新增 `reorder_outlines()` 方法，含完整环检测（自引用、循环引用、跨项目父级）
- 修改：`backend/app/repositories/outline_repo.py` — 新增 `batch_reorder()` 方法，事务内批量更新
- 修改：`backend/app/api/outlines.py` — 新增 `PATCH /api/projects/{project_id}/outlines/reorder`
- 修改：`frontend/src/entities/outline/types.ts` — 新增 `OutlineReorderItem`、`OutlineReorderResponse` 类型
- 修改：`frontend/src/entities/outline/api.ts` — 新增 `reorderOutlines()` API 函数
- 新增：`frontend/src/features/outlines/outlineDrag.ts` — 纯函数：`buildOutlineTree()`、`isDescendant()`、`flattenTree()`、`buildReorderPayload()`
- 修改：`frontend/src/features/outlines/OutlineTreeNode.vue` — 添加 HTML5 drag/drop 支持（`draggable`、`dragstart`/`dragover`/`dragleave`/`drop` 事件、前/后/内部落点高亮）
- 修改：`frontend/src/features/outlines/OutlineTree.vue` — 管理拖拽状态（`draggedId`），向上传递 `reorder` 事件
- 修改：`frontend/src/pages/outlines/ProjectOutlinePage.vue` — 处理 `@reorder` 事件，调用 API，失败时提示中文错误
- 新增：`frontend/src/__tests__/outline-drag.spec.ts` — 10 个单元测试（树构建、后代检测、排序 payload 生成、非法操作拒绝）
- 新增：`backend/tests/test_outline_reorder.py` — 6 个后端测试（同级排序、移动为子节点、自引用拒绝、环检测、未知条目/父级拒绝）

## Implementation Notes

### DOCX 导出
- 使用 `python-docx 1.2.0`（最新稳定版）生成 DOCX
- `docx_exporter.py` 使用 lazy import 避免与 `export_service.py` 的循环依赖
- 项目标题用 heading level 0，分卷用 heading 1，章节用 heading 2，正文按 `\n` 分段

### 项目包导入
- 复用 `BackupService` 的 `_read_payload()` 和 `restore_from_payload()` 逻辑，不重复实现 ID 映射
- 预览阶段使用临时文件存储 zip（`tempfile.gettempdir()/zhangshu_package_previews/`），确认导入后自动清理
- `inspect_project_backup()` 只读操作，不写数据库
- API 路由顺序重要：`/project-package/*` 必须在 `/{import_id}/confirm` 之前定义

### 大纲拖拽
- 后端使用完整环检测：从每个被移动节点沿 proposed parent 链向上遍历，检测是否会形成环
- 前端 `buildReorderPayload()` 计算完整的 siblings 重排 payload（不只是被拖动的条目），确保 order_index 连续
- 落点判断基于鼠标在节点垂直方向的 25%/50%/25% 比例
- `draggedId` prop 在 `OutlineTreeNode` 中设为可选（默认 null），避免影响 `ChapterOutlinePanel` 等其他使用处

## Deviations from Codex Plan

- `import_service.py` 中未发现 `UNSUPPORTED_LEGACY_NOTE` 常量（计划中提到但实际不存在），不影响实现
- 未创建 `outlineDrag.spec.ts` 在 features 目录下，而是放在 `src/__tests__/outline-drag.spec.ts`（与项目测试结构一致）
- 项目包导入预览使用临时文件存储而非内存 token（更简单可靠）

## Verification Commands Run

- `npm run type-check` → ✅ 通过
- `npm run build` → ✅ 通过（247 modules，745ms）
- `npm run test:unit` → ✅ 115 passed（8 test files）
- `pytest tests/test_export_service.py` → ✅ 5 passed
- `pytest tests/test_project_package_import.py` → ✅ 5 passed
- `pytest tests/test_outline_reorder.py` → ✅ 6 passed
- `python -c "from app.main import app"` → ✅ Backend import OK

## Verification Results

全部通过。

- 后端：16/16 测试通过
- 前端：115/115 测试通过
- 类型检查：无错误
- 生产构建：成功

## Known Issues

1. **项目包导入临时文件清理**：预览文件存储在系统临时目录，如果用户只预览不确认导入，文件不会被立即清理（由操作系统 temp 清理机制处理）
2. **拖拽移动端适配**：当前仅支持鼠标拖拽，未实现触摸事件。现有父级选择和排序字段仍可作为可访问性兜底
3. **拖拽视觉反馈**：落点高亮使用 `box-shadow` inset，在某些 CSS 主题下可能不够明显

## Suggested Next Review Points for Codex

1. DOCX 导出是否需要自定义字体/样式（当前使用 python-docx 默认样式）
2. 项目包导入临时文件是否需要更主动的清理策略（如过期时间）
3. 大纲拖拽是否需要移动端触摸支持
4. `outlineDrag.ts` 中的 `flattenTree` 是否需要缓存（当前每次 reorder 重新计算）
5. 项目包导入是否需要增加"合并到当前项目"功能（V1 明确不做）
