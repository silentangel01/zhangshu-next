<!-- archived_at: 2026-05-25; archive_reason: FTS5 search and complete version management completed; preparing UI polish plan -->

# CODEX_PLAN.md

## Task Summary

本次任务规划两个能力，由 Claude Code 执行实现，Codex 不修改业务代码：

1. SQLite FTS5 全文搜索：将当前章节 LIKE 搜索升级为项目级统一全文搜索，覆盖正文、设定、人物、伏笔、大纲、知识库片段等核心写作资料，并保留未来与 RAG、向量检索、混合检索协作的边界。
2. 完整版本管理：在现有章节版本历史基础上，补齐项目级版本中心、版本筛选、版本详情、差异对比、恢复前快照、版本标记/删除/清理等能力，并为设定、人物、伏笔、大纲、知识库资料等非章节实体预留统一版本模型。

上一轮 Claude Code 执行报告已阅读并归档到：

`docs/ai-handoff/archive/2026-05-25-docx-import-outline/`

本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

## Current Codebase Findings

### 现有搜索

- `backend/app/services/search_service.py` 当前只搜索章节标题和正文，使用 `LIKE '%keyword%'`。
- `backend/app/api/search.py` 当前接口为 `GET /api/projects/{project_id}/search?q=...`，返回 `ProjectSearchResponse`。
- `backend/app/schemas/search.py` 当前结果结构只面向章节：`chapter_id`、`chapter_title`、`volume_title`、`matched_field`、`snippet`、`updated_at`。
- `frontend/src/pages/search/SearchPage.vue` 当前 UI 只显示章节结果，打开结果时跳转回写作页并选中章节。
- `docs/MVP_Phase1_Acceptance_Checklist.md` 明确记录：搜索已用 SQLite LIKE 实现，项目规模变大后可能需要 FTS5。
- 知识库检索已有独立路径：
  - `backend/app/services/knowledge_retrieval_service.py` 使用 `ilike` 在 `KnowledgeChunk` 中搜索关键词；
  - `backend/app/services/retrieval_service.py` 已支持 `keyword`、`semantic`、`hybrid`，其中 keyword 仍依赖普通关键词检索。
- 当前已有向量检索、RAG、知识库问答等模块，因此 FTS5 应定位为“本地关键词全文检索层”，不要和 embedding、向量相似度、LLM 调用混在一起。

### 数据库与迁移方式

- `backend/app/infrastructure/database.py` 当前使用 SQLAlchemy `Base.metadata.create_all()` 加若干 `_ensure_*` 函数做轻量迁移，没有 Alembic。
- SQLite 运行时由 Python sqlite 提供，FTS5 通常可用，但仍需要在实现前检测 `fts5` 和 `trigram` tokenizer 是否可用。
- 当前 `database.py` 已承担了较多 schema 兼容逻辑；新增 FTS DDL 应集中在独立 infrastructure helper 中，避免继续把大量 SQL 堆进 `database.py`。

### 现有版本管理

- `backend/app/models/chapter_version.py` 已有 `chapter_versions` 表，字段包括 `chapter_id`、`project_id`、`title`、`content`、`word_count`、`source`、`note`、`created_at`。
- `backend/app/services/chapter_version_service.py` 已支持：
  - 列出章节版本；
  - 创建手动快照；
  - 自动保存节流创建版本；
  - 恢复版本前创建 `before_restore` 快照；
  - 恢复后记录 `restore` 快照。
- `backend/app/services/chapter_service.py` 在正文内容变化时会创建 `manual` 或 `autosave` 版本，并记录写作统计。
- `frontend/src/features/chapters/ChapterVersionPanel.vue` 和 `ChapterVersionPreviewDialog.vue` 当前只在写作工作区右侧面板中服务“当前章节”的版本查看与恢复。
- `docs/开发说明.md` 明确写着当前阶段“不实现版本差异对比、完整版本管理页、云备份或同步”。
- 多数核心实体模型已有 `version` 字段，例如 `Project`、`Chapter`、`SettingItem`、`Character`、`Clue`、`OutlineItem`、`KnowledgeSource`，但目前没有统一的非章节快照表。

## Architecture Decision

### 1. FTS5 作为独立本地全文检索层

- 新增 SQLite FTS5 虚拟表作为本地全文索引，不新增外部搜索服务，不引入大型依赖。
- FTS5 不替代向量检索：
  - FTS5 负责精确关键词、中文短语、标题/正文命中；
  - embedding/向量检索负责语义相似度；
  - 后续混合检索可以把 FTS5 结果作为 keyword candidates。
- 建议使用 FTS5 `trigram` tokenizer，以更适合中文网文场景中的连续中文文本、短语和局部片段命中。
- 实现前必须检测：
  - SQLite 是否支持 FTS5；
  - 是否支持 `tokenize='trigram'`。
- 如果 `trigram` 不可用，Claude Code 不应静默降级导致中文搜索失真。应在执行报告中说明，并采用以下策略之一：
  - 若 FTS5 可用但 trigram 不可用：使用 FTS5 `unicode61` 加短词 LIKE fallback；
  - 若 FTS5 不可用：停止实现并报告环境不满足任务要求。

### 2. 统一搜索索引，不把搜索逻辑散落到各业务 Service

- 新增 `SearchIndexRepository` 负责 FTS5 raw SQL 查询、重建、删除和更新。
- 新增或重构 `SearchService`，只负责任务编排、项目校验、请求参数处理和结果归一化。
- FTS5 DDL、触发器、重建逻辑放在 infrastructure/repository 边界，不写进 UI、API 或普通业务 Service。
- 搜索结果统一为 `entity_type + entity_id`，前端根据类型跳转到对应页面或定位到章节。

### 3. FTS 索引同步策略

- 第一阶段推荐使用 SQLite triggers 自动维护索引，减少在每个业务 Service 手动调用 upsert 的遗漏风险。
- 同时提供“重建全文索引”后端能力，用于：
  - 升级旧数据库首次建立索引；
  - 项目导入/备份恢复后校正；
  - 用户搜索异常时手动修复。
- 前端搜索页可以提供一个低调的“刷新全文索引”入口，但不要把底层 FTS5 细节暴露给普通作者。

### 4. 完整版本管理采用“兼容章节版本 + 通用实体版本”的双轨结构

- 不直接废弃现有 `chapter_versions`，避免破坏章节自动保存、恢复和已有测试。
- 新增 `entity_versions` 表，承载非章节实体快照，例如：
  - 设定；
  - 人物；
  - 伏笔；
  - 大纲；
  - 知识库资料。
- 新增统一 `VersionService`，对外提供项目级版本中心 API：
  - 章节版本来自 `chapter_versions`；
  - 非章节版本来自 `entity_versions`；
  - 前端看到统一的 `version_ref`。
- 版本管理不是项目备份恢复：
  - 版本管理用于单个章节/资料条目的快照、对比和恢复；
  - 项目备份用于完整项目迁移和灾备；
  - 不要把完整项目 zip 备份塞进版本表。

### 5. 版本恢复必须可撤销

- 任何版本恢复前必须先创建 `before_restore` 快照。
- 恢复操作只覆盖该实体允许恢复的业务字段，不覆盖：
  - `id`
  - `project_id`
  - `created_at`
  - `deleted_at`
  - 外键归属
  - 本地配置
  - AI/向量索引数据
- 恢复后应更新实体 `version` 与 `updated_at`，并让 FTS5 索引同步更新。

## Files to Create or Modify

### Backend - SQLite FTS5

- Create: `backend/app/infrastructure/search_fts.py`
  - FTS5 能力检测；
  - FTS5 虚拟表 DDL；
  - triggers DDL；
  - rebuild SQL helper。
- Modify: `backend/app/infrastructure/database.py`
  - 在 `init_database()` 中调用 `ensure_search_fts_schema(engine)`；
  - 不要把所有 FTS SQL 直接写进 `database.py`。
- Create: `backend/app/repositories/search_index_repo.py`
  - `search(project_id, query, entity_types, limit, offset)`；
  - `rebuild_project(project_id)`；
  - `delete_project(project_id)`；
  - 必要的 raw SQL 封装。
- Modify: `backend/app/services/search_service.py`
  - 从章节 LIKE 搜索升级为项目级全文搜索；
  - 保留项目存在性校验；
  - 处理空查询、短查询 fallback、类型过滤、分页。
- Modify: `backend/app/schemas/search.py`
  - 新增统一搜索请求/响应结构。
- Modify: `backend/app/api/search.py`
  - 扩展 `GET /api/projects/{project_id}/search`；
  - 新增 `POST /api/projects/{project_id}/search-index/rebuild`。
- Create: `backend/tests/test_search_fts.py`
  - 覆盖 FTS5 schema、重建、搜索、更新、删除、类型过滤、短词 fallback。

### Frontend - Search

- Modify: `frontend/src/entities/search/types.ts`
  - 新增 `SearchEntityType`、`ProjectSearchResult`、`ProjectSearchResponse`。
- Modify: `frontend/src/entities/search/api.ts`
  - 支持 `types`、`limit`、`offset`；
  - 新增 `rebuildProjectSearchIndex(projectId)`。
- Modify: `frontend/src/pages/search/SearchPage.vue`
  - 从章节搜索页升级为项目级全文搜索页；
  - 增加搜索范围筛选；
  - 增加结果类型标签；
  - 支持不同实体类型的打开/跳转。
- Create if useful: `frontend/src/features/search/SearchTypeFilter.vue`
  - 搜索范围筛选 UI。
- Create if useful: `frontend/src/features/search/SearchResultList.vue`
  - 统一结果列表 UI。

### Backend - Version Management

- Create: `backend/app/models/entity_version.py`
  - 通用非章节实体快照表。
- Modify: `backend/app/models/__init__.py`
  - 确保 `entity_version` 被导入并参与 `create_all()`。
- Modify: `backend/app/models/chapter_version.py`
  - 增加完整版本管理需要的兼容字段：
    - `label`
    - `is_pinned`
    - `metadata_json`
    - `deleted_at`
- Modify: `backend/app/infrastructure/database.py`
  - 增加 `_ensure_chapter_version_management_columns()`；
  - 确保旧数据库自动补齐新增字段。
- Create: `backend/app/repositories/entity_version_repo.py`
  - 通用版本快照 CRUD。
- Modify: `backend/app/repositories/chapter_version_repo.py`
  - 支持项目级列表、软删除、pin/unpin、metadata 更新。
- Create: `backend/app/services/version_service.py`
  - 统一版本列表；
  - 创建快照；
  - 获取详情；
  - 差异对比；
  - 恢复；
  - 标记/取消标记；
  - 删除；
  - 清理未标记 autosave 版本。
- Modify: `backend/app/services/chapter_version_service.py`
  - 保持原有章节版本 API 兼容；
  - 复用或对齐新版本字段；
  - 不破坏写作工作区右侧版本面板。
- Create: `backend/app/schemas/version.py`
  - 统一版本中心 schema。
- Modify: `backend/app/schemas/chapter_version.py`
  - 增加新增字段。
- Create: `backend/app/api/versions.py`
  - 新增项目级版本中心 API。
- Modify: `backend/app/main.py`
  - include `versions_router`。
- Create: `backend/tests/test_version_service.py`
  - 覆盖通用版本快照、详情、对比、恢复前快照、软删除。
- Create: `backend/tests/test_versions_api.py`
  - 覆盖统一版本 API。
- Modify: `backend/tests/test_chapter_version_service.py` if present
  - 补充新增字段兼容测试。

### Frontend - Version Management

- Create: `frontend/src/entities/version/types.ts`
  - 统一版本类型定义。
- Create: `frontend/src/entities/version/api.ts`
  - 统一版本中心 API。
- Create: `frontend/src/pages/versions/ProjectVersionsPage.vue`
  - 项目级版本中心。
- Create: `frontend/src/features/versions/VersionListPanel.vue`
  - 版本列表、筛选、分页。
- Create: `frontend/src/features/versions/VersionDetailPanel.vue`
  - 版本详情。
- Create: `frontend/src/features/versions/VersionDiffViewer.vue`
  - 当前内容与版本内容对比。
- Create: `frontend/src/features/versions/VersionRestoreDialog.vue`
  - 恢复确认。
- Create: `frontend/src/features/versions/VersionSnapshotDialog.vue`
  - 为当前实体创建版本快照。
- Modify: `frontend/src/router/index.ts`
  - 新增路由 `/projects/:projectId/versions`。
- Modify: `frontend/src/pages/projects/ProjectDetailPage.vue`
  - 在更多菜单或工具栏增加“版本”入口；
  - 保持现有章节版本右侧面板，不要强行重写工作区布局。
- Modify: `frontend/src/features/chapters/ChapterVersionPanel.vue`
  - 可增加“打开版本中心”入口；
  - 如新增字段展示，保持兼容。
- Modify: `frontend/src/entities/chapter-version/types.ts`
  - 对齐新增字段。

## Implementation Steps for Claude Code

### Step 0 - 执行前检查

1. 执行 `git status --short`，确认当前工作区已有未提交变更时，不要回滚，不要覆盖。
2. 检查 `docs/ai-handoff/CODEX_PLAN.md` 与实际代码是否冲突。
3. 先运行 SQLite FTS5 能力检测：
   ```powershell
   .\.venv\Scripts\python.exe -c "import sqlite3; con=sqlite3.connect(':memory:'); con.execute('CREATE VIRTUAL TABLE t USING fts5(x, tokenize=''trigram'')'); print(sqlite3.sqlite_version)"
   ```
4. 如果本地命令中的 Python 路径不同，使用项目实际虚拟环境路径。
5. 如果 FTS5 或 trigram 不可用，停止并写入执行报告，不要用普通 LIKE 假装完成 FTS5。

### Step 1 - 建立 FTS5 schema 与索引维护

1. 新建 `backend/app/infrastructure/search_fts.py`。
2. 提供 `detect_fts5_support(connection) -> SearchFtsCapabilities`：
   - `supports_fts5`
   - `supports_trigram`
   - `sqlite_version`
   - `tokenizer`
3. 创建统一 FTS 表，建议结构：
   ```sql
   CREATE VIRTUAL TABLE IF NOT EXISTS search_documents_fts USING fts5(
     project_id UNINDEXED,
     entity_type UNINDEXED,
     entity_id UNINDEXED,
     title,
     body,
     tags,
     metadata_json UNINDEXED,
     updated_at UNINDEXED,
     tokenize = 'trigram'
   );
   ```
4. 如果需要记录索引状态，创建普通表：
   ```sql
   CREATE TABLE IF NOT EXISTS search_index_meta (
     project_id TEXT PRIMARY KEY,
     tokenizer TEXT NOT NULL,
     document_count INTEGER NOT NULL DEFAULT 0,
     last_rebuilt_at DATETIME,
     last_error TEXT
   );
   ```
5. 为以下实体创建 insert/update/delete triggers：
   - `chapters`
   - `setting_items`
   - `characters`
   - `clues`
   - `outline_items`
   - `knowledge_chunks`
   - `timeline_events`
   - `graph_nodes`
6. triggers 规则：
   - `deleted_at IS NOT NULL` 时从 FTS 表删除；
   - insert/update 时先删除同 `entity_type + entity_id` 的旧索引，再插入新索引；
   - 文件夹型设定目录可只索引标题，设定页索引标题、摘要、详情、标签；
   - 知识库优先索引 `knowledge_chunks.heading/content`，不要重复索引整份 source content 造成结果重复。
7. 在 `database.py` 的 `init_database()` 中调用 `ensure_search_fts_schema(engine)`。
8. 首次创建 FTS 表后，对旧数据执行一次全量 backfill。

### Step 2 - 实现后端统一全文搜索

1. 新建 `backend/app/repositories/search_index_repo.py`。
2. `SearchIndexRepository.search()` 要支持：
   - `project_id`
   - `query`
   - `entity_types`
   - `limit`
   - `offset`
3. 使用参数化 SQL，不拼接用户输入。
4. 对 FTS `MATCH` 查询做转义：
   - 去掉控制字符；
   - 处理引号；
   - 空查询直接返回空结果；
   - 过短查询使用安全 fallback，不要让 FTS 抛语法错误。
5. 使用 `bm25(search_documents_fts)` 或等价方式排序：
   - 标题命中权重大于正文；
   - 结果同时返回 `score`；
   - 不要把 SQLite 内部高亮 HTML 直接传给前端渲染。
6. 修改 `backend/app/schemas/search.py`：
   - `SearchEntityType = Literal["chapter", "setting", "character", "clue", "outline", "knowledge", "timeline", "graph"]`
   - `ProjectSearchResult` 字段建议：
     - `entity_type`
     - `entity_id`
     - `title`
     - `subtitle`
     - `matched_field`
     - `snippet`
     - `score`
     - `updated_at`
     - `metadata`
   - `ProjectSearchResponse` 字段建议：
     - `query`
     - `mode`
     - `tokenizer`
     - `total`
     - `limit`
     - `offset`
     - `results`
7. 修改 `backend/app/services/search_service.py`：
   - 校验项目存在；
   - 调用 `SearchIndexRepository`；
   - 做实体类型中文标签映射所需 metadata；
   - 保留结果数量限制，默认 50，上限 100。
8. 修改 `backend/app/api/search.py`：
   - `GET /api/projects/{project_id}/search?q=...&types=chapter,setting&limit=50&offset=0`
   - `POST /api/projects/{project_id}/search-index/rebuild`
9. 对旧的前端调用保持兼容：仍使用 `/api/projects/{project_id}/search`，但响应结构升级。

### Step 3 - 升级前端搜索页

1. 修改 `frontend/src/entities/search/types.ts` 和 `api.ts`。
2. 修改 `frontend/src/pages/search/SearchPage.vue`：
   - 搜索框仍在页面顶部；
   - 增加范围筛选按钮或分段控件：
     - 全部；
     - 正文；
     - 设定；
     - 人物；
     - 伏笔；
     - 大纲；
     - 知识库；
     - 时间线；
     - 关系图。
   - 结果列表显示实体类型标签、标题、摘要片段、更新时间。
   - 空状态文案说明“可搜索正文、设定、人物和资料”。
3. 打开结果逻辑：
   - `chapter`：写入 workspace selectedChapterId 后跳转 `/projects/{projectId}`；
   - `setting`：跳转 `/projects/{projectId}/settings`，可通过 query 传 `settingId`；
   - `character`：跳转 `/projects/{projectId}/characters`，可通过 query 传 `characterId`；
   - `clue`：跳转 `/projects/{projectId}/clues`，可通过 query 传 `clueId`；
   - `outline`：跳转 `/projects/{projectId}/outlines`，可通过 query 传 `outlineId`；
   - `knowledge`：跳转 `/projects/{projectId}/knowledge`，可通过 query 传 `chunkId` 或 `sourceId`；
   - `timeline`：跳转 `/projects/{projectId}/timeline`；
   - `graph`：跳转 `/projects/{projectId}/graph`。
4. 如果目标页面尚未支持 query 定位，不要强行大改目标页面；先跳转到对应模块，并在计划偏差或后续建议中说明。
5. 增加“刷新全文索引”入口：
   - 建议放在搜索页更多菜单或次要按钮；
   - 文案面向用户为“刷新搜索索引”，不要显示“FTS5”。

### Step 4 - 建立完整版本管理数据层

1. 修改 `backend/app/models/chapter_version.py`，新增字段：
   - `label: str | None`
   - `is_pinned: bool`
   - `metadata_json: str`
   - `deleted_at: datetime | None`
2. 在 `database.py` 中新增 `_ensure_chapter_version_management_columns()`，兼容旧数据库。
3. 新建 `backend/app/models/entity_version.py`，建议字段：
   - `id`
   - `project_id`
   - `entity_type`
   - `entity_id`
   - `entity_title`
   - `snapshot_json`
   - `content_text`
   - `word_count`
   - `source`
   - `label`
   - `note`
   - `is_pinned`
   - `metadata_json`
   - `created_at`
   - `deleted_at`
4. 支持的 `entity_type` 第一阶段包括：
   - `chapter`
   - `setting`
   - `character`
   - `clue`
   - `outline`
   - `knowledge_source`
5. 不要第一阶段就把 timeline、graph 节点做成可恢复版本；这两类关系复杂，可先只纳入 FTS 搜索，版本化留到后续。

### Step 5 - 实现统一 VersionService 与 API

1. 新建 `backend/app/services/version_service.py`。
2. 版本统一引用格式建议：
   - `chapter_version:<uuid>`
   - `entity_version:<uuid>`
3. 新建 `backend/app/schemas/version.py`，建议 schema：
   - `VersionEntityType`
   - `VersionSource`
   - `VersionListItem`
   - `VersionDetail`
   - `CreateVersionSnapshotRequest`
   - `UpdateVersionRequest`
   - `VersionCompareRequest`
   - `VersionCompareResponse`
   - `RestoreVersionRequest`
   - `RestoreVersionResponse`
4. 新增 API：
   - `GET /api/projects/{project_id}/versions`
     - 支持 `entity_type`、`entity_id`、`source`、`pinned`、`keyword`、`limit`、`offset`。
   - `POST /api/projects/{project_id}/versions/snapshots`
     - 为指定实体创建手动快照。
   - `GET /api/projects/{project_id}/versions/{version_ref}`
     - 获取版本详情。
   - `PATCH /api/projects/{project_id}/versions/{version_ref}`
     - 更新 label、note、is_pinned。
   - `DELETE /api/projects/{project_id}/versions/{version_ref}`
     - 软删除未 pin 版本；pin 版本需要先取消标记。
   - `POST /api/projects/{project_id}/versions/compare`
     - 对比版本与当前内容，或两个版本。
   - `POST /api/projects/{project_id}/versions/{version_ref}/restore`
     - 恢复版本，恢复前自动创建 `before_restore`。
   - `POST /api/projects/{project_id}/versions/cleanup`
     - 清理未标记的旧 autosave 版本，必须返回清理数量。
5. `VersionService` 中实现实体快照 adapter：
   - `chapter` 复用 `ChapterVersionService` 与 `chapter_versions`；
   - `setting` 读写 `SettingItem` 的 title、summary、detail、tags、item_type、canon_status、importance；
   - `character` 读写 name、role、summary、biography、appearance、personality、background、ability、motivation、secret、arc、notes；
   - `clue` 读写 title、description、status、visibility、importance、payoff_plan、actual_payoff、note；
   - `outline` 读写 title、content、item_type、status、importance；
   - `knowledge_source` 读写 title、source_type、source_uri、author、summary、content、tags、credibility。
6. 差异对比：
   - 后端可用 Python 标准库 `difflib` 生成 line diff，不新增依赖；
   - 同时返回 `old_text`、`new_text`，方便前端渲染；
   - 前端不要执行危险 HTML diff。
7. 恢复后：
   - 更新实体 `updated_at` 与 `version`；
   - 依赖 FTS trigger 自动刷新索引；
   - 章节恢复继续清除或提示本地恢复稿风险，不破坏现有章节恢复流程。

### Step 6 - 实现前端版本中心

1. 新建 `frontend/src/pages/versions/ProjectVersionsPage.vue`。
2. 新增路由 `/projects/:projectId/versions`。
3. 在 `ProjectDetailPage.vue` 的更多菜单中增加“版本”入口。
4. 版本中心布局建议：
   - 顶部：返回写作页、搜索版本、筛选按钮、创建快照；
   - 左侧/主区：版本列表；
   - 右侧/详情区：版本详情和差异对比；
   - 小屏幕改为上下布局。
5. 筛选项：
   - 实体类型；
   - 来源：手动、自动保存、恢复前备份、恢复记录；
   - 是否已标记；
   - 关键词。
6. 版本详情动作：
   - 查看内容；
   - 对比当前；
   - 恢复；
   - 标记/取消标记；
   - 修改备注；
   - 删除未标记版本。
7. 恢复确认文案必须明确：
   - 当前内容会被覆盖；
   - 系统会先创建恢复前快照；
   - 此操作只恢复当前实体，不恢复整个项目。
8. 保留现有 `ChapterVersionPanel.vue`：
   - 不要在本任务中重写写作工作区；
   - 可增加“打开版本中心”链接；
   - 当前章节快速创建快照和恢复仍可继续使用。

### Step 7 - 测试与执行报告

1. 增加并运行后端测试：
   - `test_search_fts.py`
   - `test_version_service.py`
   - `test_versions_api.py`
   - 现有章节版本测试。
2. 增加必要的前端单元测试：
   - 搜索类型过滤；
   - 版本引用解析；
   - diff viewer 纯函数。
3. 运行验证命令。
4. 生成 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`，记录：
   - 实际修改文件；
   - FTS5/trigram 检测结果；
   - 与本计划的偏差；
   - 已运行命令和结果；
   - 未完成项；
   - 风险和后续建议。

## Constraints

- Codex 未修改业务代码，本计划应由 Claude Code 执行。
- 不要引入 Elasticsearch、Meilisearch、Typesense 等外部搜索服务。
- 不要把 FTS5、向量检索、LLM 调用混写在同一个 service 或 UI 组件中。
- 不要把 FTS5 raw SQL 散落到多个业务 Service。
- 不要把普通 LIKE 搜索包装成“FTS5 已完成”。
- 不要把版本管理实现成完整项目备份的替代品。
- 不要删除或重建现有 `chapter_versions` 表。
- 不要破坏现有章节自动保存、恢复稿、写作统计和章节版本右侧面板。
- 不要第一阶段就给关系图、时间线做可恢复版本，避免复杂引用恢复失控。
- 不要修改与本任务无关的 Tauri 壳、导入导出、写作统计、提醒模块等文件。
- 不要提交 `data/`、`logs/`、`.env`、本地数据库、临时构建产物。

## Verification Commands

Claude Code 应根据实际项目脚本确认命令名称；以下为建议命令。

### FTS5 能力检测

```powershell
.\.venv\Scripts\python.exe -c "import sqlite3; con=sqlite3.connect(':memory:'); con.execute('CREATE VIRTUAL TABLE t USING fts5(x, tokenize=''trigram'')'); print(sqlite3.sqlite_version)"
```

### Backend

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_search_fts.py backend\tests\test_version_service.py backend\tests\test_versions_api.py
```

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests\test_chapter_version_service.py backend\tests\test_retrieval_service.py backend\tests\test_knowledge_retrieval.py
```

完整后端回归：

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
```

### Frontend

```powershell
cd frontend
npm run type-check
npm run test:unit -- search
npm run test:unit -- version
npm run build
```

如果项目没有匹配的 `test:unit` 子命令，Claude Code 应在执行报告中说明，并至少运行：

```powershell
cd frontend
npm run type-check
npm run build
```

### Manual Smoke Test

1. 启动后端和前端。
2. 打开 `/projects/{projectId}/search`。
3. 搜索一个只出现在正文中的词，确认命中章节。
4. 搜索一个只出现在设定或人物资料中的词，确认命中对应模块。
5. 搜索一个知识库片段中的词，确认命中知识库结果。
6. 修改一个章节或设定内容后再次搜索，确认索引已更新。
7. 删除或软删除一个实体后搜索，确认结果不再出现。
8. 打开 `/projects/{projectId}/versions`。
9. 创建一个章节版本快照，查看详情，对比当前内容。
10. 创建一个设定或人物版本快照，修改原实体后执行对比。
11. 恢复一个版本，确认恢复前快照已生成，且当前内容被正确恢复。
12. 标记一个版本，再尝试删除，确认系统阻止或要求先取消标记。

## Acceptance Criteria

- 搜索接口使用 SQLite FTS5，而不是原有章节 LIKE 搜索。
- 搜索范围至少覆盖：章节、设定、人物、伏笔、大纲、知识库片段。
- 搜索结果包含实体类型、标题、片段、更新时间和可跳转信息。
- 中文短语搜索在常见场景下能命中连续正文片段。
- 修改、删除、恢复实体后，全文索引能同步更新。
- 前端搜索页不再只展示章节结果。
- 搜索页提供清晰的范围筛选和“刷新搜索索引”入口。
- 现有知识库 semantic/hybrid 检索不被破坏。
- 现有章节版本历史功能不回退。
- 新增项目级版本中心页面。
- 版本中心可筛选、查看详情、对比当前、恢复、标记、删除未标记版本。
- 恢复版本前自动创建 `before_restore` 快照。
- 非章节实体至少支持设定、人物、伏笔、大纲、知识库资料的手动快照。
- 所有用户可见文案为简体中文。
- Claude Code 生成 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。

## Risks and Watchpoints

- SQLite FTS5 `trigram` tokenizer 取决于 SQLite 版本；如果不可用，中文搜索体验会明显下降。
- FTS triggers 写错会造成索引重复、漏删或更新不及时，必须用测试覆盖 insert/update/delete/soft delete。
- FTS5 表会复制部分正文和资料内容，数据库体积会增加。
- 搜索结果跨模块跳转可能需要目标页面支持 query 定位；若目标页面没有现成能力，不要在本任务中大规模重写目标页面。
- 版本管理如果试图一次覆盖所有实体和所有关系，会变成隐形备份系统；本阶段应先覆盖单实体快照。
- 非章节实体恢复时必须控制可恢复字段，不得覆盖外键归属和系统字段。
- 章节版本已有自动保存节流逻辑，不能因统一版本中心而创建大量重复快照。
- 删除版本需要软删除，避免用户误删后无法追踪。
- 版本 diff 如果用 HTML 高亮，必须避免 XSS；建议第一阶段只渲染文本 diff。
- 当前工作区 `docs/ai-handoff/` 可能是未追踪目录，Claude Code 不应误删交接文件。

## Review Checklist

- [ ] 是否读取并遵守了本计划？
- [ ] 是否只修改了本计划列出的相关文件？
- [ ] 是否检测并记录了 SQLite FTS5/trigram 支持情况？
- [ ] 搜索是否真正使用 FTS5，而不是继续使用 LIKE 主流程？
- [ ] FTS raw SQL 是否集中在 infrastructure/repository 边界？
- [ ] FTS triggers 是否覆盖 insert/update/delete/soft delete？
- [ ] 搜索结果是否支持多实体类型？
- [ ] 搜索 UI 是否能清楚区分章节、设定、人物、伏笔、大纲、知识库等结果？
- [ ] 是否没有把 FTS5 与向量检索、LLM 调用混在同一层？
- [ ] 是否保留了现有知识库 semantic/hybrid 检索？
- [ ] 是否保留并兼容现有 `chapter_versions`？
- [ ] 是否新增了统一版本中心 API 和页面？
- [ ] 版本恢复前是否自动创建 `before_restore` 快照？
- [ ] 非章节实体恢复是否只覆盖允许字段？
- [ ] 版本删除是否为软删除？
- [ ] 标记版本是否不会被清理任务删除？
- [ ] 是否补充了搜索和版本管理的后端测试？
- [ ] 是否运行了前端 type-check/build？
- [ ] 是否没有提交密钥、本地配置、数据库、日志或临时文件？
- [ ] `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md` 是否记录实际执行结果、验证命令和偏差？
