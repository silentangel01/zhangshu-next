<!-- archived_at: 2026-05-25; archive_reason: DOCX export, project package import, and outline drag sorting completed; preparing SQLite FTS5 and version management plan -->

# CODEX_PLAN.md

## Task Summary

本次任务规划三项能力，由 Claude Code 执行实现，Codex 不修改业务代码：

1. 实现 DOCX 正文导出：当前正文导出已有 `txt`、`md`，`docx` 在前后端均为占位/禁用状态，需要补齐真实 DOCX 文件生成与下载。
2. 作品导入复杂资料：当前作品导入主要面向项目、分卷、章节；人物、关系图、时间线、知识库等复杂资料暂不导入。建议将复杂资料导入定义为“章枢完整项目包迁移/导入映射”，优先复用现有备份恢复能力，而不是把通用正文导入扩展成任意复杂资料解析器。
3. 大纲拖拽排序：当前大纲支持树形展示、父级选择和 `order_index` 手动编辑，但缺少拖拽调整同级顺序和父子层级的交互，需要前后端共同支持。

本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

## Current Codebase Findings

### DOCX 正文导出

- `backend/app/schemas/export.py` 中 `ExportFormat` 已包含 `docx`。
- `backend/app/services/export_service.py` 中 `export_manuscript()` 已构造 `ManuscriptDocument`，但当格式为 `docx` 时直接抛出 `ExportUnsupportedFormatError()`。
- `backend/app/api/exports.py` 当前将不支持格式转换为 400，错误文案为 `DOCX 导出暂未支持`。
- `frontend/src/entities/project/exportTypes.ts` 已包含 `ManuscriptExportFormat = 'txt' | 'md' | 'docx'`。
- `frontend/src/entities/project/exportApi.ts` 已具备下载导出文件的通用逻辑。
- `frontend/src/pages/imports/ProjectBackupPage.vue` 当前在用户选择 `docx` 时前端主动阻止导出，并提示 `DOCX 导出暂未支持，请先选择 TXT 或 Markdown。`
- `backend/requirements.txt` 当前未发现 `python-docx`，如果采用成熟库生成 DOCX，需要新增后端依赖。

### 作品导入复杂资料

- `backend/app/services/import_service.py` 当前导入流程以正文导入为主，`preview_import()`、`preview_external_files()` 和 `confirm_import()` 主要处理项目、分卷、章节。
- `backend/app/utils/import_parsers.py` 中 `UNSUPPORTED_LEGACY_NOTE` 明确提示人物、关系图、时间线、知识库等复杂资料后续支持。
- `backend/app/schemas/imports.py` 的预览和确认响应结构主要围绕文件数、分卷数、章节数、字数、警告、未支持文件设计。
- `frontend/src/pages/imports/ImportPage.vue`、`frontend/src/features/imports/ImportPreviewPanel.vue`、`frontend/src/features/imports/ImportReportPanel.vue` 当前 UI 也主要服务正文导入。
- `backend/app/services/backup_service.py` 已存在完整项目备份与恢复能力，备份格式为 `zhangshu.project_backup`，并包含人物、设定、伏笔、时间线、关系图、大纲、章节链接等多类实体。
- `backup_service.py` 中已有 `ENTITY_MODELS`、`RESTORE_ORDER`、`REFERENCE_FIELDS`、`BOUND_TYPE_TO_ENTITY` 等 ID 映射和引用重建逻辑，是复杂资料迁移的最佳基础。

### 大纲拖拽排序

- `backend/app/services/outline_service.py` 已支持创建、更新、删除、读取大纲条目，并可更新 `parent_id` 与 `order_index`。
- 当前后端只阻止 `parent_id == outline.id` 的直接自引用，尚未发现完整的祖先/后代环检测。
- `backend/app/api/outlines.py` 当前没有批量排序或拖拽重排接口。
- `backend/app/repositories/outline_repo.py` 当前按 `parent_id`、`order_index`、`created_at` 排序读取大纲，但没有批量更新排序方法。
- `frontend/src/features/outlines/OutlineTree.vue` 基于 `parent_id` 组装树，并按 `order_index` 排序展示。
- `frontend/src/features/outlines/OutlineTreeNode.vue` 当前只负责递归展示节点，没有拖拽交互。
- `frontend/src/features/outlines/OutlineEditor.vue` 当前提供父级和排序值的表单式编辑，可作为拖拽失败或移动端场景下的兜底入口。

## Architecture Decision

### 1. DOCX 正文导出

- 后端保持导出业务入口在 `ExportService`，但 DOCX 文件渲染逻辑不要堆进 API 层。
- 建议新增 `backend/app/infrastructure/docx_exporter.py`，专门负责把 `ManuscriptDocument` 渲染为 DOCX bytes。
- `ExportService` 负责：
  - 读取项目、分卷、章节；
  - 组装 `ManuscriptDocument`；
  - 根据格式调用 TXT、MD 或 DOCX 渲染器；
  - 返回统一的 `ManuscriptExportResult`。
- DOCX 生成建议使用 `python-docx`。这是小型、成熟、用途明确的依赖，理由充分；如本地无法安装依赖，Claude Code 应停止并在执行报告中说明，不要改用脆弱的手写二进制或临时 hack。
- 前端移除 DOCX 禁用逻辑，复用现有下载 API。

### 2. 作品导入复杂资料

- 不建议把现有正文导入流程扩展为任意复杂资料解析器；人物、关系图、时间线、知识库的结构差异较大，强行混入 `ImportService` 会导致导入层职责过重。
- 建议新增“章枢项目包导入/完整迁移”路径：
  - 正文导入继续由 `ImportService` 负责；
  - 完整项目包导入复用 `BackupService` 的备份格式、ID 映射和引用重建逻辑；
  - 如需要预览能力，可新增 `ProjectPackageImportService` 或在 `BackupService` 中补充只读预览方法。
- 第一阶段只支持章枢原生备份包：`manifest.format == "zhangshu.project_backup"`。
- 第一阶段默认“导入为新项目”，不要做复杂的“合并到当前项目”。合并导入涉及重名冲突、章节覆盖、关系图节点归并、知识库去重，应留到后续任务。
- 导入预览应展示复杂资料数量和风险提示，而不直接执行恢复。

### 3. 大纲拖拽排序

- 前端负责拖拽交互和预览移动结果，后端负责最终校验和持久化。
- 新增后端批量重排接口，避免前端逐条调用 update 导致部分成功、部分失败。
- 后端必须校验：
  - 所有被移动条目属于当前项目；
  - 新父级存在且属于当前项目；
  - 不允许移动到自身或自身后代下；
  - 重新计算后的同级 `order_index` 连续、稳定；
  - 批量更新在同一事务内完成。
- 前端拖拽建议支持三类落点：
  - 拖到节点上：作为该节点的最后一个子节点；
  - 拖到节点前：作为同级前置节点；
  - 拖到节点后：作为同级后置节点。

## Files to Create or Modify

### Backend - DOCX Export

- Modify: `backend/requirements.txt`
  - 新增 `python-docx`，建议固定兼容版本，例如 `python-docx>=1.1,<2.0`。
- Create: `backend/app/infrastructure/docx_exporter.py`
  - 新增 `render_manuscript_docx(document: ManuscriptDocument) -> bytes`。
- Modify: `backend/app/services/export_service.py`
  - 移除 `docx` 的 unsupported 分支；
  - 调用 `docx_exporter`；
  - 设置正确文件名、扩展名和 MIME。
- Modify: `backend/app/api/exports.py`
  - 保留错误处理，但 DOCX 正常情况下不应再进入 unsupported 分支。
- Create or Modify: `backend/tests/test_export_service.py` 或 `backend/tests/test_docx_export.py`
  - 增加 DOCX 导出单元测试。

### Frontend - DOCX Export

- Modify: `frontend/src/pages/imports/ProjectBackupPage.vue`
  - 移除 DOCX 禁用判断；
  - 保留格式选择和下载流程；
  - 如 UI 有说明文案，将 `DOCX 暂未支持` 改为正常支持说明。
- Modify only if needed: `frontend/src/entities/project/exportTypes.ts`
  - 当前已有 `docx`，原则上不需要改。
- Modify only if needed: `frontend/src/entities/project/exportApi.ts`
  - 当前下载逻辑通用，原则上不需要改。

### Backend - Full Project Package Import

- Create: `backend/app/services/project_package_import_service.py`
  - 负责项目包预览、校验、确认导入的编排。
  - 可调用或复用 `BackupService` 的读取、校验、恢复逻辑。
- Modify: `backend/app/services/backup_service.py`
  - 抽出只读解析/统计方法，例如 `inspect_project_backup(file_bytes)`；
  - 避免把预览逻辑重复写在新 service 中。
- Modify or Create: `backend/app/schemas/imports.py` 或 `backend/app/schemas/project_package_import.py`
  - 新增项目包导入预览和确认响应 schema。
- Modify: `backend/app/api/imports.py`
  - 新增项目包预览/确认接口，或新增独立 router 后在主路由中挂载。
- Create: `backend/tests/test_project_package_import.py`
  - 覆盖合法备份包预览、确认导入、非法 manifest、缺失数据文件、引用映射基本正确性。

### Frontend - Full Project Package Import

- Modify: `frontend/src/pages/imports/ImportPage.vue`
  - 将导入页区分为“导入正文”和“导入章枢项目包/完整迁移”两个入口，可使用 tabs 或分段按钮。
  - 项目包导入应提示：适用于从章枢备份包迁移完整项目，导入后默认创建新项目。
- Modify: `frontend/src/entities/import/types.ts`
  - 新增项目包预览、确认响应类型。
- Modify: `frontend/src/entities/import/api.ts`
  - 新增 `previewProjectPackageImport()`、`confirmProjectPackageImport()`。
- Modify: `frontend/src/features/imports/ImportPreviewPanel.vue`
  - 支持展示复杂资料数量：人物、设定、伏笔、时间线、关系图、大纲、知识库或其他可统计实体。
- Modify: `frontend/src/features/imports/ImportReportPanel.vue`
  - 展示完整迁移结果：新项目 ID、项目标题、导入实体数量、警告信息。

### Backend - Outline Drag Sorting

- Modify: `backend/app/schemas/outline.py`
  - 新增 `OutlineReorderItem`、`OutlineReorderRequest`、`OutlineReorderResponse`。
- Modify: `backend/app/api/outlines.py`
  - 新增接口：`PATCH /api/projects/{project_id}/outlines/reorder`。
- Modify: `backend/app/services/outline_service.py`
  - 新增 `reorder_outlines(project_id, items)`；
  - 增加完整环检测和同项目校验；
  - 使用事务批量更新 `parent_id` 与 `order_index`。
- Modify: `backend/app/repositories/outline_repo.py`
  - 新增批量读取和批量更新方法，避免 service 直接拼 SQL。
- Create: `backend/tests/test_outline_reorder.py`
  - 覆盖同级排序、移动为子节点、跨父级移动、移动到后代下失败、跨项目父级失败。

### Frontend - Outline Drag Sorting

- Modify: `frontend/src/entities/outline/types.ts`
  - 新增重排请求/响应类型。
- Modify: `frontend/src/entities/outline/api.ts`
  - 新增 `reorderOutlines(projectId, items)`。
- Create: `frontend/src/features/outlines/outlineDrag.ts`
  - 放置纯函数：树扁平化、判断是否后代、计算移动后的 sibling order、生成 reorder payload。
- Modify: `frontend/src/features/outlines/OutlineTree.vue`
  - 管理拖拽状态；
  - 接收拖拽结果；
  - 调用重排 API；
  - 成功后刷新大纲并保持选中项。
- Modify: `frontend/src/features/outlines/OutlineTreeNode.vue`
  - 增加可拖拽节点、落点高亮、drop 前/后/内部区域。
- Modify: `frontend/src/pages/outlines/ProjectOutlinePage.vue`
  - 传入重排回调；
  - 显示保存中、失败提示；
  - 保留现有编辑器作为手动兜底。
- Create: `frontend/src/features/outlines/outlineDrag.spec.ts` 或现有测试目录下对应测试
  - 测试纯函数，不依赖浏览器拖拽事件。

## Implementation Steps for Claude Code

### Step 0 - 执行前检查

1. 执行 `git status --short`，确认当前工作区已有 Tauri、统计仪表盘或其他未提交改动时，不要回滚，不要覆盖。
2. 阅读本计划涉及文件的当前版本，确认路径和函数名仍一致。
3. 如果发现本计划与实际代码冲突，停止执行并写入 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。

### Step 1 - 实现 DOCX 正文导出

1. 在 `backend/requirements.txt` 添加 `python-docx>=1.1,<2.0`。
2. 新建 `backend/app/infrastructure/docx_exporter.py`：
   - 输入 `ManuscriptDocument`；
   - 生成 `Document()`；
   - 项目标题使用标题样式；
   - 分卷标题使用一级标题；
   - 章节标题使用二级标题；
   - 正文按段落拆分，空段落不要生成大量空白；
   - 输出 `bytes`。
3. 修改 `backend/app/services/export_service.py`：
   - 保留 TXT/MD 逻辑；
   - `format == ExportFormat.docx` 时调用 `render_manuscript_docx()`；
   - MIME 设置为 `application/vnd.openxmlformats-officedocument.wordprocessingml.document`；
   - 文件名扩展名为 `.docx`。
4. 修改 `frontend/src/pages/imports/ProjectBackupPage.vue`：
   - 移除选择 DOCX 时的前端阻断；
   - 确认 DOCX 选项文案与实际支持状态一致。
5. 添加后端测试：
   - 构造包含项目、分卷、章节、正文的导出请求；
   - 断言返回文件名 `.docx`；
   - 断言 MIME 正确；
   - 使用 `zipfile` 检查返回 bytes 是合法 DOCX zip；
   - 读取 `word/document.xml`，断言包含项目名、分卷名、章节名、正文关键文本。

### Step 2 - 设计并实现章枢完整项目包导入

1. 不要改动现有正文导入语义；正文导入继续只负责项目、分卷、章节。
2. 在 `backend/app/services/backup_service.py` 中抽出项目包只读检查能力：
   - 校验 zip；
   - 读取 `manifest.json`；
   - 校验 `format == "zhangshu.project_backup"`；
   - 统计 `data/*.json` 中各实体数量；
   - 检查封面等 assets 是否存在；
   - 返回预览数据，不写数据库。
3. 新建 `backend/app/services/project_package_import_service.py`：
   - `preview_package(file)`：调用 backup inspect，生成预览 token 或临时文件记录；
   - `confirm_package(preview_id)`：调用现有 restore 流程，默认创建新项目；
   - 不在该 service 中重复实现 ID 映射。
4. 新增 schema：
   - `ProjectPackageImportPreviewResponse`：
     - `preview_id`
     - `project_title`
     - `source_version`
     - `entity_counts`
     - `has_cover`
     - `warnings`
   - `ProjectPackageImportConfirmResponse`：
     - `project_id`
     - `project_title`
     - `entity_counts`
     - `warnings`
5. 新增 API：
   - `POST /api/imports/project-package/preview`
     - multipart file；
     - 返回项目包预览。
   - `POST /api/imports/project-package/confirm`
     - 请求 `preview_id`；
     - 返回新项目信息。
6. 前端在 `ImportPage.vue` 增加两个导入入口：
   - `导入正文`：保留现有流程；
   - `导入章枢项目包`：上传 `.zip` 备份包，展示复杂资料预览，用户确认后导入为新项目。
7. 预览 UI 展示至少以下数量：
   - 分卷；
   - 章节；
   - 人物；
   - 设定；
   - 伏笔；
   - 时间线；
   - 关系图；
   - 大纲；
   - 章节关联或其他可统计链接。
8. 确认导入完成后，提供跳转到新项目的入口。
9. 明确暂不支持：
   - 任意第三方复杂资料格式；
   - 与当前项目合并；
   - 自动去重；
   - 冲突字段交互式映射。

### Step 3 - 实现大纲拖拽排序

1. 后端先补齐安全接口：
   - 在 `backend/app/schemas/outline.py` 增加 reorder schema；
   - 在 `backend/app/services/outline_service.py` 增加 `reorder_outlines()`；
   - 在 `backend/app/repositories/outline_repo.py` 增加批量更新方法；
   - 在 `backend/app/api/outlines.py` 增加 `PATCH /api/projects/{project_id}/outlines/reorder`。
2. `reorder_outlines()` 的请求建议：
   ```json
   {
     "items": [
       {
         "outline_id": "outline-id",
         "parent_id": "new-parent-id-or-null",
         "order_index": 0
       }
     ]
   }
   ```
3. 后端处理要求：
   - 读取项目下所有未删除大纲条目；
   - 将请求中的 `parent_id` 合并到当前树结构；
   - 检查任何节点是否会形成环；
   - 检查父级是否属于同项目；
   - 在同一事务中批量写入；
   - 返回更新数量。
4. 前端先创建 `outlineDrag.ts` 纯函数：
   - `buildOutlineTree()`
   - `isDescendant()`
   - `moveOutlineNode()`
   - `buildReorderPayload()`
5. 修改 `OutlineTree.vue`：
   - 维护当前拖拽节点；
   - 处理 drop 结果；
   - 调用重排 API；
   - 成功后刷新；
   - 失败时展示中文错误提示并恢复原树。
6. 修改 `OutlineTreeNode.vue`：
   - `draggable="true"`；
   - 增加拖拽开始、拖拽经过、放下事件；
   - 对“放到前面/后面/作为子节点”给出清晰视觉反馈；
   - 不要让高亮区域导致布局抖动。
7. 移动端或键盘操作暂不强制实现拖拽，但保留现有父级选择和排序字段作为可访问性兜底。

### Step 4 - 测试与执行报告

1. 按本计划的验证命令运行测试。
2. 如果新增依赖导致本地环境需要安装，记录安装命令和结果。
3. 如果某些验证命令因本地环境缺失无法执行，在执行报告中明确说明原因。
4. 生成 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`，包括：
   - 实际修改文件；
   - 实际实现内容；
   - 与本计划的偏差；
   - 已运行命令和结果；
   - 未完成项；
   - 风险和建议。

## Constraints

- Codex 未修改业务代码，本计划应由 Claude Code 执行。
- 不要将 DOCX 渲染逻辑写入 API/router。
- 不要将项目包复杂导入逻辑混进现有正文导入解析器。
- 不要重复实现 `BackupService` 已有的 ID 映射和引用恢复逻辑。
- 第一阶段复杂资料导入只支持章枢原生备份包，不支持任意第三方复杂资料格式。
- 第一阶段完整项目包导入默认创建新项目，不做合并导入。
- 不要为了拖拽排序引入大型拖拽库；优先使用原生 HTML5 drag/drop 和小型纯函数。
- 不要重写大纲模块页面结构，只做必要的树节点交互增强。
- 不要修改与本任务无关的 Tauri 壳、写作统计仪表盘、知识库、提醒模块等文件。
- 不要提交 `data/`、`logs/`、`.env`、本地数据库、临时构建产物。

## Verification Commands

Claude Code 应根据实际项目脚本确认命令名称；以下为建议命令：

### Backend

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest tests\test_export_service.py tests\test_project_package_import.py tests\test_outline_reorder.py
```

如项目虚拟环境路径为 `.venv` 且位于仓库根目录，请使用：

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_export_service.py backend\tests\test_project_package_import.py backend\tests\test_outline_reorder.py
```

完整后端回归：

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
```

### Frontend

```powershell
cd frontend
npm run type-check
npm run test:unit -- outlineDrag
npm run build
```

如果项目没有 `test:unit` 脚本，Claude Code 应在执行报告中说明，并至少运行 `npm run type-check` 与 `npm run build`。

### Manual Smoke Test

1. 启动后端和前端。
2. 在导出页选择 DOCX，导出全书/分卷/单章，确认浏览器下载 `.docx` 文件且 Word/WPS 可打开。
3. 使用现有章枢备份 zip 进入“导入章枢项目包”，确认预览显示复杂资料数量，确认后生成新项目。
4. 在大纲页拖动节点：
   - 同级前后排序；
   - 移动为另一个节点的子节点；
   - 尝试移动到自身后代下，确认被阻止并提示。

## Acceptance Criteria

- DOCX 导出不再提示暂未支持。
- DOCX 导出的文件扩展名、MIME、内容结构正确，至少包含项目标题、分卷标题、章节标题、正文段落。
- TXT/MD 导出行为不回退。
- 作品正文导入流程不被破坏。
- 新增“章枢项目包/完整迁移”入口，能预览并导入章枢原生备份包。
- 完整项目包导入默认创建新项目，并正确恢复复杂资料和引用关系。
- 大纲支持拖拽同级排序和跨父级移动。
- 大纲后端拒绝跨项目父级、移动到自身、移动到后代等非法请求。
- 前端拖拽失败时不会留下错误的本地树状态。
- 所有用户可见文案为简体中文。
- Claude Code 生成 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。

## Risks and Watchpoints

- `python-docx` 是新增依赖，可能影响离线环境安装；若当前项目对离线安装有要求，需要补充依赖缓存或安装说明。
- DOCX 中文字体设置如果过度复杂，可能引入跨平台兼容问题；第一阶段优先保证文档可打开和内容完整。
- 完整项目包导入若直接复用恢复逻辑，必须确保预览阶段不写数据库。
- 备份包恢复已有 ID 映射逻辑，不要在新 service 中复制一份，否则后续模型变化会造成双重维护。
- 复杂资料“合并到当前项目”暂不做；如果误做，极易引入重名冲突和引用错乱。
- 大纲拖拽的前端树变换容易出现 order_index 不连续、移动后选中项丢失、折叠状态丢失等问题。
- 后端只检查直接自引用不够，必须补充完整环检测。
- 如果当前工作区已有未提交 Tauri 壳改动，Claude Code 不得覆盖或回滚。

## Review Checklist

- [ ] 是否只修改了本计划列出的相关文件？
- [ ] DOCX 渲染是否位于 infrastructure 或专门渲染模块，而不是 API/router？
- [ ] `ExportService` 是否仍保持统一导出入口？
- [ ] DOCX 导出是否有自动化测试验证合法 docx zip 和正文内容？
- [ ] TXT/MD 导出是否仍通过测试？
- [ ] 复杂资料导入是否复用了 `BackupService` 的备份/恢复映射，而非重复实现？
- [ ] 项目包预览是否不写数据库？
- [ ] 项目包导入是否默认创建新项目，而不是合并到当前项目？
- [ ] 现有正文导入是否未被破坏？
- [ ] 大纲重排接口是否批量事务更新？
- [ ] 大纲移动是否有完整环检测？
- [ ] 前端拖拽失败是否能恢复并提示？
- [ ] 是否没有引入大型 UI/拖拽库？
- [ ] 是否没有提交密钥、本地配置、数据库、日志或临时文件？
- [ ] `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md` 是否记录了实际执行结果、验证命令和偏差？
