---
archived_at: 2026-05-25
archive_reason: FTS5 search and complete version management completed; preparing UI polish plan
date: 2026-05-25
task: FTS5 全文搜索 + 完整版本管理
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

实现 SQLite FTS5 全文搜索（替代原有 LIKE 搜索）和完整版本管理系统（项目级版本中心，支持多实体类型快照、对比、恢复）。

## Files Changed

### Backend - FTS5 全文搜索

- 新增：`backend/app/infrastructure/search_fts.py` — FTS5 能力检测、DDL、triggers、backfill
- 新增：`backend/app/repositories/search_index_repo.py` — FTS5 raw SQL 查询封装
- 修改：`backend/app/infrastructure/database.py` — init_database() 中调用 ensure_search_fts_schema
- 修改：`backend/app/services/search_service.py` — 从 LIKE 搜索升级为 FTS5 调用 SearchIndexRepository
- 修改：`backend/app/schemas/search.py` — 新增统一搜索响应结构、实体类型、rebuild 响应
- 修改：`backend/app/api/search.py` — 扩展搜索 API 参数 (types/limit/offset)、新增 rebuild 端点

### Backend - 版本管理

- 新增：`backend/app/models/entity_version.py` — 通用非章节实体快照表
- 新增：`backend/app/repositories/entity_version_repo.py` — 实体版本 CRUD
- 新增：`backend/app/services/version_service.py` — 统一版本管理服务（含实体适配器）
- 新增：`backend/app/schemas/version.py` — 统一版本中心 schema
- 新增：`backend/app/api/versions.py` — 项目级版本中心 API（8 个端点）
- 修改：`backend/app/models/chapter_version.py` — 新增 label/is_pinned/metadata_json/deleted_at 字段
- 修改：`backend/app/repositories/chapter_version_repo.py` — 支持项目级列表、软删除、pin、cleanup
- 修改：`backend/app/schemas/chapter_version.py` — 新增 label/is_pinned 字段
- 修改：`backend/app/infrastructure/database.py` — 新增 _ensure_chapter_version_management_columns()
- 修改：`backend/app/main.py` — 注册 versions_router

### Frontend - 搜索

- 修改：`frontend/src/entities/search/types.ts` — 新增 SearchEntityType、ProjectSearchResult 等
- 修改：`frontend/src/entities/search/api.ts` — 支持 types/limit/offset 参数，新增 rebuild API
- 修改：`frontend/src/pages/search/SearchPage.vue` — 升级为项目级全文搜索页（范围筛选、类型标签、实体跳转、刷新索引）

### Frontend - 版本中心

- 新增：`frontend/src/entities/version/types.ts` — 统一版本类型定义
- 新增：`frontend/src/entities/version/api.ts` — 版本中心 API 客户端
- 新增：`frontend/src/pages/versions/ProjectVersionsPage.vue` — 项目级版本中心页面
- 修改：`frontend/src/router/index.ts` — 新增 /projects/:projectId/versions 路由
- 修改：`frontend/src/pages/projects/ProjectDetailPage.vue` — 更多菜单中新增"版本中心"入口

### Tests

- 新增：`backend/tests/test_search_fts.py` — 11 个测试
- 新增：`backend/tests/test_version_service.py` — 16 个测试

## Implementation Notes

### FTS5 搜索

- 使用 trigram tokenizer（SQLite 3.50.4，支持 FTS5 + trigram）
- trigram 要求最少 3 个字符；少于 3 字符的查询自动降级为 LIKE fallback
- 为 8 个实体表创建了 insert/update/delete triggers 自动维护索引
- bm25 权重：title=10, body=1, tags=1
- FTS5 column numbering 包含 UNINDEXED 列（project_id=0, entity_type=1, entity_id=2, title=3, body=4, tags=5, metadata_json=6, updated_at=7）
- 每次应用启动时 drop+recreate FTS 表并 backfill，确保 schema 一致性
- 搜索结果为 phrase matching（连续字符序列匹配），非分词搜索

### 版本管理

- 双轨结构：chapter_versions（兼容现有） + entity_versions（新增）
- 统一版本引用格式：`chapter_version:<uuid>` / `entity_version:<uuid>`
- 恢复操作前自动创建 before_restore 快照
- 实体恢复只覆盖允许字段，不覆盖 id/project_id/created_at/deleted_at/外键
- 差异对比使用 Python difflib，文本级 line diff
- 软删除版本，标记版本不可删除
- cleanup 清理 30 天前未标记的 autosave 版本

### 已知限制

- FTS5 trigram 搜索为精确短语匹配，不支持分词后 OR 搜索（如搜索"测试统计"只匹配连续出现"测试统计"的文档）
- 2 字符及以下查询使用 LIKE fallback，性能较差但功能正确
- 搜索结果跨模块跳转时，目标页面可能不支持 query 参数定位（如设定页、人物页不自动选中 query 中的 ID）
- 版本中心创建快照需要手动输入实体 ID（后续可从各实体页面添加快捷入口）

## Deviations from Codex Plan

- 未创建 `search_index_meta` 表（FTS 表每次启动重建，不需要额外状态跟踪）
- 未创建独立的 `SearchTypeFilter.vue` 和 `SearchResultList.vue` 组件（功能内联在 SearchPage.vue 中）
- 未创建独立的 `VersionListPanel.vue`、`VersionDetailPanel.vue`、`VersionDiffViewer.vue`、`VersionRestoreDialog.vue`、`VersionSnapshotDialog.vue` 组件（功能集成在 ProjectVersionsPage.vue 中，减少文件数量）
- 未创建 `test_versions_api.py`（API 层通过 service 测试覆盖）

## Verification Commands Run

- `npm run type-check` → ✅ 通过
- `npm run build` → ✅ 通过（253 modules, 685ms）
- `pytest tests/test_search_fts.py` → ✅ 11 passed
- `pytest tests/test_version_service.py` → ✅ 16 passed
- `pytest tests/` → ✅ 383 passed（全量回归，无失败）
- FTS5 capability detection → ✅ FTS5 + trigram, SQLite 3.50.4

## Verification Results

全部通过，无回归。

## Known Issues

1. FTS5 搜索为精确短语匹配，中文搜索体验受限于 trigram tokenizer 的最小 3 字符要求
2. 目标页面（设定、人物、伏笔等）暂不支持 query 参数自动定位到搜索结果对应条目
3. 版本中心创建快照需要手动输入实体 ID，暂无从各实体详情页直接创建快照的快捷入口
4. 现有 `ChapterVersionPanel.vue`（写作工作区右侧面板）未修改，仍使用原有章节版本 API

## Suggested Next Review Points for Codex

1. FTS5 trigram 的精确匹配策略是否满足用户需求，是否需要实现分词 OR 搜索
2. 版本中心 UI 是否需要拆分为独立组件以提升可维护性
3. 是否需要在各实体详情页添加"创建快照"快捷入口
4. 搜索结果跳转后，目标页面是否需要支持 query 参数自动定位
5. 是否需要在 ChapterVersionPanel 中增加"打开版本中心"链接
