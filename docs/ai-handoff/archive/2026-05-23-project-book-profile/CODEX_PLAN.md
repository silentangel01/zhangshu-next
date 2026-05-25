# Task Summary

本任务规划 `/projects` 书籍/项目页面的信息结构升级：让一个书籍项目至少具备书名、作者、封面上传与默认封面、简介、标签库式标签 UI，以及必要的细节属性。当前 Codex 只负责规划，不实现业务代码。

本计划建议同时升级项目存储结构。原因是当前后端 `Project` 只有 `title`、`genre`、`summary`，无法可靠保存作者、封面、标签和书籍状态；如果只做前端临时展示，后续 RAG、向量检索、知识图谱、AI 总结时会缺少稳定的书籍元数据边界。

Claude Code 执行时应覆盖写入 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`，说明实际修改、验证结果和偏离点。

# Current Codebase Findings

- 已阅读 Claude 上一轮执行报告，上一任务为 `back-link-unification`，已通过 `npm run type-check`、`npm run test:unit`、`npm run build`。旧交接文件已归档到 `docs/ai-handoff/archive/2026-05-23-back-link-unification/`。
- 后端项目模型位于 `backend/app/models/project.py`，当前字段为：
  - `id`
  - `title`
  - `genre`
  - `summary`
  - `created_at`
  - `updated_at`
  - `deleted_at`
  - `version`
- 后端项目 schema 位于 `backend/app/schemas/project.py`，`ProjectCreate` / `ProjectUpdate` / `ProjectRead` 只覆盖 `title`、`genre`、`summary` 等现有字段。
- 后端项目 API 位于 `backend/app/api/projects.py`，当前只有列表、创建、详情、更新、软删除，没有封面上传或封面读取接口。
- 后端已有上传入口示例：
  - `backend/app/api/imports.py` 使用 `UploadFile` / `File`
  - `backend/app/api/backups.py` 使用 `UploadFile` 和 `StreamingResponse`
- 后端本地数据根目录由 `backend/app/infrastructure/database.py` 中的 `DATABASE_DIR` 控制，默认指向仓库根目录 `data/`。`.gitignore` 已忽略 `data/`，适合存放本地封面文件。
- `backend/app/infrastructure/database.py` 已有多处轻量列补齐函数，例如 `_ensure_setting_tree_columns()`，当前项目没有 Alembic；项目字段升级应沿用这种兼容旧 SQLite 的方式。
- 前端项目类型位于 `frontend/src/entities/project/types.ts`，当前 `Project` 只有 `title`、`genre`、`summary` 等现有字段。
- 前端项目 API 位于 `frontend/src/entities/project/api.ts`，当前只支持 JSON 请求；封面上传需要使用 `FormData` 和直接 `fetch`，不能复用会强制设置 JSON `Content-Type` 的 `apiRequest`。
- `/projects` 页面位于 `frontend/src/pages/projects/ProjectsPage.vue`，当前是项目卡片网格，卡片展示标题、类型、简介、版本、更新时间和打开/编辑/删除操作。
- `/projects/:projectId` 写作页位于 `frontend/src/pages/projects/ProjectDetailPage.vue`。当未选择章节时显示项目概览，目前概览只展示类型、更新时间、分卷数、章节数和简介。
- 创建/编辑项目弹窗位于：
  - `frontend/src/features/projects/CreateProjectDialog.vue`
  - `frontend/src/features/projects/EditProjectDialog.vue`
  当前只编辑标题、类型、简介。
- 当前工作区已有设定、伏笔、返回按钮等未提交改动；Claude Code 不得回退、覆盖或大规模格式化这些无关文件。

# Architecture Decision

采用“小步扩展 Project 元数据 + 本地封面文件存储 + 前端标签组件”的方案，不引入大型依赖，不重建项目，不把 UI、业务逻辑、数据访问和文件存储堆在同一个文件。

后端字段建议：

- 复用现有 `title` 作为书名。
- 复用现有 `summary` 作为简介，不新增 `description`，避免重复语义字段。
- 复用现有 `genre` 作为类型/题材。
- 新增 `author: String(128), nullable=True`。
- 新增 `tags: Text, nullable=False, default="[]"`，以 JSON 字符串保存字符串数组；API 层对外暴露为 `string[]`。
- 新增 `cover_image_path: String(500), nullable=True`，只保存相对 `DATABASE_DIR` 的路径，不保存绝对路径。
- 新增 `status: String(32), nullable=False, default="planning"`，建议可选值为 `planning`、`writing`、`paused`、`completed`、`archived`。
- 新增 `target_word_count: Integer, nullable=True`，用于目标字数，可为空；不在本任务中计算实际字数。

封面存储建议：

- 新建基础设施模块 `backend/app/infrastructure/project_cover_storage.py`。
- 封面文件保存到 `DATABASE_DIR / "project_covers" / project_id / cover.<ext>`。
- 只允许 `image/jpeg`、`image/png`、`image/webp`。
- 默认大小上限建议 5MB。
- 后端不信任上传文件原名，不使用用户原始文件名拼路径。
- API 提供：
  - `POST /api/projects/{project_id}/cover` 上传或替换封面，返回 `ProjectRead`。
  - `DELETE /api/projects/{project_id}/cover` 删除自定义封面并回到默认封面，返回 `ProjectRead`。
  - `GET /api/projects/{project_id}/cover` 读取自定义封面；没有自定义封面时返回 404，由前端显示默认封面。
- 默认封面建议放在前端静态资源中，例如 `frontend/src/assets/default-book-cover.svg`，这样无需为默认图新增后端文件分发逻辑。

标签库建议：

- 不新建独立 `project_tags` 表，先把项目标签作为书籍元数据的一部分存储在 `projects.tags`。
- 前端标签库由“内置常用标签 + 当前项目列表中已有标签”合并去重生成。
- 如果未来需要全局标签管理、标签颜色、标签统计，再迁移为单独表；当前不提前重构。

备份/恢复建议：

- 因封面是文件资产，不在数据库行内，Claude Code 必须处理备份边界：
  - 最低要求：在执行报告中明确本轮是否纳入备份。
  - 推荐实现：更新 `backend/app/services/backup_service.py`，导出备份时把当前项目封面写入 zip 的 `assets/project_cover/`，恢复时复制到新项目的 `data/project_covers/<new_project_id>/` 并更新 `cover_image_path`。
- 备份恢复必须兼容没有封面的旧备份。

# Files to Create or Modify

后端建议修改：

- `backend/app/models/project.py`
  - 增加作者、标签、封面路径、状态、目标字数字段。
- `backend/app/schemas/project.py`
  - 扩展 `ProjectCreate`、`ProjectUpdate`、`ProjectRead`。
  - 对 `title`、`author`、`genre`、`status`、`target_word_count`、`tags` 做基础校验。
  - `ProjectRead.tags` 对数据库 JSON 字符串做解析，向前端返回 `list[str]`。
- `backend/app/services/project_service.py`
  - 增加标签标准化/序列化逻辑。
  - 增加上传、删除封面的服务方法。
  - 更新 create/update 时的字段写入。
- `backend/app/repositories/project_repo.py`
  - 如现有通用 update 足够，可不改；如需要封面路径专用更新，可最小化增加方法。
- `backend/app/api/projects.py`
  - 增加 `UploadFile` / `File` / `FileResponse` 相关导入。
  - 增加封面上传、删除、读取接口。
- `backend/app/infrastructure/database.py`
  - 增加 `_ensure_project_book_columns()` 并在 `init_database()` 中调用。
- `backend/app/infrastructure/project_cover_storage.py`
  - 新建，封装封面目录创建、路径解析、文件写入、删除、MIME 校验。
- `backend/app/services/backup_service.py`
  - 推荐更新备份/恢复封面资产。
- `backend/tests/test_projects_book_profile.py`
  - 新增或按现有测试结构补充项目元数据、标签、封面接口测试。

前端建议修改：

- `frontend/src/entities/project/types.ts`
  - 扩展 `Project`、`CreateProjectPayload`、`UpdateProjectPayload`。
- `frontend/src/entities/project/api.ts`
  - 增加 `uploadProjectCover(projectId, file)`。
  - 增加 `deleteProjectCover(projectId)`。
  - 增加 `getProjectCoverUrl(projectId, version)` 或等价 helper。
- `frontend/src/assets/default-book-cover.svg`
  - 新增默认封面资源。
- `frontend/src/features/projects/ProjectTagInput.vue`
  - 新增标签输入与标签库选择组件。
- `frontend/src/features/projects/ProjectCoverUploader.vue`
  - 新增封面选择、预览、删除/恢复默认封面的展示组件；组件只处理 UI 事件，API 调用放在页面或弹窗父级。
- `frontend/src/features/projects/CreateProjectDialog.vue`
  - 增加作者、标签、状态、目标字数、封面选择。
- `frontend/src/features/projects/EditProjectDialog.vue`
  - 增加作者、标签、状态、目标字数、封面上传/删除。
- `frontend/src/pages/projects/ProjectsPage.vue`
  - 项目卡片升级为书籍卡片：封面、书名、作者、题材、标签、简介、状态、更新时间。
  - 生成标签库建议并传给创建/编辑弹窗。
  - 创建项目后，如用户选择封面，再调用封面上传接口。
- `frontend/src/pages/projects/ProjectDetailPage.vue`
  - 未选章节时的项目概览增加封面、作者、标签、状态、目标字数。
- `frontend/src/__tests__/projects-book-profile.spec.ts`
  - 可新增标签标准化、封面 URL helper 或项目卡片展示的轻量测试。

不应修改：

- 不要重写 `App.vue`、router、`ChapterTree`、`ChapterEditor`、`WritingAidPanel`。
- 不要改动设定、伏笔、关系图、时间线等无关业务模块。
- 不要引入大型 UI 库或图片处理依赖。

# Implementation Steps for Claude Code

1. 执行前检查
   - 读取本计划。
   - 运行 `git status --short`，确认已有未提交改动，不要回退无关文件。
   - 重点查看当前 `projects` 相关文件是否与本计划仍一致。

2. 后端扩展 Project 模型
   - 修改 `backend/app/models/project.py`。
   - 在 `Project` 中新增：
     - `author`
     - `tags`
     - `cover_image_path`
     - `status`
     - `target_word_count`
   - `tags` 数据库存储为 JSON 字符串，默认 `"[]"`。
   - `status` 默认 `"planning"`。

3. 后端补齐旧库字段
   - 修改 `backend/app/infrastructure/database.py`。
   - 新增 `_ensure_project_book_columns()`：
     - 如果 `projects` 表不存在，直接返回。
     - 如果缺少 `author`，执行 `ALTER TABLE projects ADD COLUMN author VARCHAR(128)`。
     - 如果缺少 `tags`，执行 `ALTER TABLE projects ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'`。
     - 如果缺少 `cover_image_path`，执行 `ALTER TABLE projects ADD COLUMN cover_image_path VARCHAR(500)`。
     - 如果缺少 `status`，执行 `ALTER TABLE projects ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'planning'`。
     - 如果缺少 `target_word_count`，执行 `ALTER TABLE projects ADD COLUMN target_word_count INTEGER`。
   - 在 `init_database()` 中 `Base.metadata.create_all(bind=engine)` 后调用该函数。

4. 后端 schema 和标签序列化
   - 修改 `backend/app/schemas/project.py`。
   - `ProjectCreate` 支持：
     - `title`
     - `author`
     - `genre`
     - `summary`
     - `tags: list[str]`
     - `status`
     - `target_word_count`
   - `ProjectUpdate` 对同字段使用可选值。
   - `ProjectRead` 返回同字段，并保证 `tags` 是 `list[str]`。
   - 标签规则：
     - trim 空白。
     - 过滤空字符串。
     - 去重，保持用户输入顺序。
     - 单个标签建议最长 24 字符。
     - 总标签数建议最多 20 个。
   - `target_word_count` 为空或大于等于 0。
   - `status` 只允许 `planning`、`writing`、`paused`、`completed`、`archived`。

5. 后端 service 更新
   - 修改 `backend/app/services/project_service.py`。
   - 增加标签 encode/decode 或 normalize helper。
   - `create_project()` 创建 `Project` 时写入新字段。
   - `update_project()` 使用 `exclude_unset=True`，如果 payload 包含 `tags`，先序列化为 JSON 字符串。
   - 不要把文件系统写入逻辑直接堆在 API 层。

6. 封面文件基础设施
   - 新建 `backend/app/infrastructure/project_cover_storage.py`。
   - 公开函数建议：
     - `save_project_cover(project_id: str, filename: str, content_type: str | None, content: bytes) -> str`
     - `delete_project_cover(relative_path: str | None) -> None`
     - `resolve_project_cover_path(relative_path: str | None) -> Path | None`
     - `get_project_cover_media_type(path: Path) -> str`
   - 所有路径必须限制在 `DATABASE_DIR / "project_covers"` 下。
   - 保存前删除同项目旧封面，避免残留多个旧图。
   - 不使用上传原文件名作为最终文件名，只根据 MIME/扩展确定 `.jpg`、`.png`、`.webp`。

7. 封面 API
   - 修改 `backend/app/api/projects.py`。
   - 增加：
     - `POST /api/projects/{project_id}/cover`
     - `DELETE /api/projects/{project_id}/cover`
     - `GET /api/projects/{project_id}/cover`
   - 上传接口：
     - `file: UploadFile = File(...)`
     - `await file.read()`
     - 超过 5MB 返回 400。
     - 不支持类型返回 400。
     - 项目不存在返回 404。
   - GET 接口：
     - 项目不存在返回 404。
     - 没有自定义封面或文件丢失返回 404。
     - 有文件时返回 `FileResponse`。

8. 备份/恢复封面资产
   - 修改 `backend/app/services/backup_service.py`。
   - 导出时：
     - 如果 `project.cover_image_path` 有值且文件存在，把封面写入 zip，例如 `assets/project_cover/cover.<ext>`。
     - manifest 中记录该资产路径。
   - 恢复时：
     - 如果 zip 中存在封面资产，写入新项目的 cover 目录。
     - 更新恢复后 project 的 `cover_image_path` 为新相对路径。
     - 如果旧备份没有封面资产，不报错。
   - 不要破坏当前 v1 备份恢复；若升级 manifest version，必须兼容读取旧 version。

9. 前端类型与 API
   - 修改 `frontend/src/entities/project/types.ts`。
   - `Project` 新增：
     - `author: string | null`
     - `tags: string[]`
     - `cover_image_path: string | null`
     - `status: ProjectStatus`
     - `target_word_count: number | null`
   - 新增 `ProjectStatus` union type。
   - 修改 `frontend/src/entities/project/api.ts`：
     - JSON API 继续使用 `apiRequest`。
     - 封面上传使用 `fetch` + `FormData`，不要手动设置 `Content-Type`。
     - 读取封面 URL 时拼接 `API_BASE_URL`，并带上 `?v=${project.version}` 避免浏览器缓存旧封面。

10. 默认封面资源
   - 新增 `frontend/src/assets/default-book-cover.svg`。
   - 视觉上应像书籍封面，不要使用复杂外链图片。
   - SVG 中文可使用“章枢”或“默认封面”等简体中文；确保 UTF-8。

11. 标签输入组件
   - 新建 `frontend/src/features/projects/ProjectTagInput.vue`。
   - Props：
     - `modelValue: string[]`
     - `suggestions: string[]`
     - `disabled?: boolean`
   - Emits：
     - `update:modelValue`
   - UI 要求：
     - 已选标签显示为 chip。
     - 可输入新标签，按 Enter 或点击添加。
     - 标签库建议以按钮/chip 形式展示，点击添加。
     - 已选择的建议不可重复添加。
     - 删除标签有明确按钮，文案/aria 使用简体中文。

12. 封面上传组件
   - 新建 `frontend/src/features/projects/ProjectCoverUploader.vue`。
   - Props：
     - `coverUrl: string | null`
     - `defaultCoverUrl: string`
     - `disabled?: boolean`
   - Emits：
     - `select-file: [file: File]`
     - `clear-cover: []`
   - UI 要求：
     - 显示当前封面预览。
     - 没有自定义封面时显示默认封面。
     - 文件 input 接受 `.jpg,.jpeg,.png,.webp`。
     - 前端也做一次 5MB 和 MIME 提示，但以后端校验为准。

13. 创建项目弹窗
   - 修改 `frontend/src/features/projects/CreateProjectDialog.vue`。
   - 增加字段：
     - 书名：对应 `title`。
     - 作者：对应 `author`。
     - 题材/类型：对应 `genre`。
     - 简介：对应 `summary`。
     - 标签：使用 `ProjectTagInput`。
     - 状态：select，默认“筹备中”。
     - 目标字数：number，可为空。
     - 封面：使用 `ProjectCoverUploader`，只保存在本地临时 `File`，提交后由父级在创建项目成功后上传。
   - 提交事件建议改为传出 `{ project: CreateProjectPayload, coverFile: File | null }`，并同步更新 `ProjectsPage.vue`。

14. 编辑项目弹窗
   - 修改 `frontend/src/features/projects/EditProjectDialog.vue`。
   - 同步增加上述字段。
   - 封面组件选择文件后 emit 给父级，由父级调用 `uploadProjectCover()`。
   - 点击恢复默认封面 emit 给父级，由父级调用 `deleteProjectCover()`。
   - 保存文字信息仍走 `updateProject()`。

15. `/projects` 项目列表升级为书籍卡片
   - 修改 `frontend/src/pages/projects/ProjectsPage.vue`。
   - 计算 `tagSuggestions`：
     - 内置常用标签，例如 `玄幻`、`都市`、`科幻`、`悬疑`、`历史`、`仙侠`、`奇幻`、`群像`、`长篇`、`短篇`。
     - 合并当前 `projects` 中已有 `tags`。
   - 卡片布局包含：
     - 左侧或顶部封面缩略图。
     - 书名。
     - 作者，未设置显示“未设置作者”。
     - 题材/类型。
     - 状态中文文案。
     - 标签 chip。
     - 简介摘要。
     - 更新时间。
     - 打开、编辑、删除操作。
   - 创建项目流程：
     - 调用 `createProject(payload.project)`。
     - 如果 `coverFile` 存在，再调用 `uploadProjectCover(createdProject.id, coverFile)`。
     - 最后刷新列表。
     - 如果封面上传失败但项目已创建，显示明确错误：项目已创建，但封面上传失败。
   - 编辑项目流程：
     - 保存文字字段后刷新列表。
     - 上传/删除封面成功后刷新列表，并更新当前编辑对象。

16. `/projects/:projectId` 概览区增强
   - 修改 `frontend/src/pages/projects/ProjectDetailPage.vue`。
   - 只改“未选章节时”的 `project-summary` 概览区。
   - 增加封面、作者、标签、状态、目标字数展示。
   - 不改 `ChapterTree`、`ChapterEditor`、`WritingAidPanel`，不调整写作布局主逻辑。

17. 测试
   - 后端新增或更新测试：
     - 创建项目时能保存作者、标签、状态、目标字数。
     - 更新项目时 tags 空数组可保存为 `[]`。
     - 非法 status 返回 422。
     - 上传支持的封面后 `cover_image_path` 有值，GET 能返回文件。
     - 上传超大或不支持类型返回 400。
     - 删除封面后 `cover_image_path` 为空。
     - 旧项目在缺少新增列前提下初始化不会失败。
   - 前端新增轻量测试：
     - 标签去重/建议合并逻辑。
     - cover URL 带 version。
     - 项目卡片能展示作者、标签和默认封面。

18. 执行报告
   - 完成后写入 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
   - 报告必须说明：
     - 实际修改文件。
     - 数据库新增字段。
     - 封面文件保存位置。
     - 备份/恢复是否已包含封面资产。
     - 验证命令和结果。
     - 未完成项、风险或与本计划的偏离。

# Constraints

- 不要修改与本任务无关的业务模块。
- 不要重建 Vue 项目。
- 不要重写 router、`App.vue`、`ChapterTree`、`ChapterEditor`、`WritingAidPanel`。
- 不要把封面文件读写逻辑直接写进 `app/main.py`。
- 不要把 UI、业务逻辑、数据访问、文件系统操作混在单一大文件中。
- 不要新增大型 UI 库。
- 不要新增图片处理依赖；本轮只做 MIME/扩展名/大小校验。
- 不要保存上传文件原始文件名作为最终路径。
- 不要把 `data/`、封面文件、日志、临时文件、数据库提交到 git。
- 所有用户可见文案使用简体中文。
- 所有新增文件保持 UTF-8。
- 兼容旧 SQLite 数据库和旧项目记录。
- 保持未来 RAG、向量检索、知识图谱和 AI 总结的扩展边界：书籍元数据属于 Project 层，不要混入章节、设定、伏笔或 AI 调用层。

# Verification Commands

后端：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
python -m compileall app
pytest
```

前端：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit
npm run build
```

手动联调：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd F:\zhangshu\frontend
npm run dev
```

浏览器检查：

- `/projects`
- `/projects/{projectId}`

手动验收点：

- 新建书籍时可填写书名、作者、题材、简介、标签、状态、目标字数。
- 新建书籍时不上传封面也显示默认封面。
- 新建书籍时上传封面后列表卡片显示自定义封面。
- 编辑书籍信息后 `/projects` 和 `/projects/{projectId}` 都显示最新信息。
- 删除自定义封面后恢复默认封面。
- 标签库能展示内置标签和已有项目标签。
- 非法图片类型和超大图片有错误提示。
- 刷新页面后项目元数据和封面仍存在。

# Acceptance Criteria

- `/projects` 页面以书籍卡片形式展示项目，至少包括封面、书名、作者、简介、标签和细节属性。
- 项目创建和编辑流程能保存作者、标签、状态、目标字数等新增字段。
- 自定义封面上传、读取、替换、删除可用。
- 未上传封面时显示默认封面。
- 后端 `ProjectRead` 向前端返回 `tags: string[]`，前端无需解析数据库 JSON 字符串。
- 旧项目和旧 SQLite 数据库启动后不报错，新增字段有合理默认值。
- 不破坏已有 Project / Volume / Chapter / Editor / Autosave / Version / Import / Outline / Character / Setting / Clue API。
- 不引入大型依赖。
- 前端 type-check、unit test、build 通过。
- 后端 compileall 和 pytest 通过；如 pytest 环境缺失，执行报告必须说明。
- `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md` 已写明实际执行情况。

# Risks and Watchpoints

- 封面是文件资产，如果不纳入备份/恢复，项目迁移后会丢封面。Claude Code 必须处理或明确报告未处理。
- `tags` 数据库存为 JSON 字符串，但 API 对外是数组；schema/service 任一层遗漏转换都会导致前端类型不匹配。
- `apiRequest` 会强制 JSON `Content-Type`，封面上传不能复用它直接传 `FormData`。
- 旧数据库列补齐必须可重复执行，不能在字段已存在时失败。
- `ProjectDetailPage.vue` 是核心写作页，修改范围必须限制在项目概览区，不能扰动章节编辑工作流。
- 当前工作区存在多轮未提交改动，不要格式化整个目录，不要回退已有设定/伏笔/返回按钮修改。
- PowerShell 可能显示中文乱码，但文件实际必须保持 UTF-8，浏览器 UI 文案不能乱码。
- 文件路径必须只存相对 `DATABASE_DIR` 的路径，不要保存本机绝对路径，否则迁移和备份会出问题。
- 不要把标签库过早设计成复杂知识图谱节点；项目标签只是书籍元数据，未来如需要再建立独立标签实体。

# Review Checklist

- 是否已读取 Claude 上一轮执行报告并归档旧交接文件。
- 是否只按计划修改项目/书籍页面相关代码。
- 是否没有改动无关业务模块。
- 是否新增并补齐了 Project 数据字段。
- 是否旧 SQLite 数据库可平滑启动。
- `tags` 是否在后端持久化为 JSON 字符串、API 返回为数组。
- 是否有标签 trim、去重、数量和长度限制。
- 封面上传是否限制类型和大小。
- 封面路径是否安全、相对、不会使用用户原始文件名。
- 删除封面后是否回到默认封面。
- 默认封面是否为本地前端资源。
- `/projects` 卡片是否展示书名、作者、封面、简介、标签和细节属性。
- `/projects/{projectId}` 未选章节概览是否展示新的书籍信息。
- 是否没有把文件存储逻辑写进 API 层或 `main.py`。
- 是否没有引入大型 UI 库或图片处理依赖。
- 是否考虑并报告备份/恢复封面资产。
- 是否没有提交 `data/`、数据库、日志、临时文件、封面上传文件。
- 前端 type-check/test/build 是否通过。
- 后端 compileall/pytest 是否通过。
- `CLAUDE_EXECUTION_REPORT.md` 是否完整记录实际改动、验证结果和风险。
