---
archived_for_next_task: knowledge-ui-layout-progress
date: 2026-05-24
task: 知识库索引刷新 UX 改造
codex_plan: docs/ai-handoff/CODEX_PLAN.md (knowledge index refresh UX)
---

## Task Summary
移除知识库页面中的技术按钮（重建分块、生成向量、向量索引、重建全部索引），改为面向作者的"刷新知识索引"入口。支持选择分块大小（小/中/大）并在操作前提供风险说明。

## Files Changed

### 新增
- `backend/app/services/knowledge_index_refresh_service.py` — 索引刷新编排 service，协调分块重建和嵌入更新
- `backend/tests/test_knowledge_index_refresh_service.py` — 刷新 service 的测试（10 个用例）
- `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue` — 刷新知识索引对话框组件

### 修改
- `backend/app/services/knowledge_service.py` — 参数化分块大小：新增 `KnowledgeChunkSize` 类型、`CHUNK_SIZE_PROFILES`（small: 350-600, medium: 800-1200, large: 1500-2200）、`rebuild_chunks()` 和内部函数接收 `chunk_size` 参数
- `backend/app/schemas/knowledge_embedding.py` — 新增 `RefreshKnowledgeIndexRequest` 和 `RefreshKnowledgeIndexResponse`
- `backend/app/api/knowledge_embedding.py` — 新增 `POST /api/projects/{project_id}/knowledge/index/refresh` 端点
- `backend/tests/test_knowledge_service.py` — 新增 `TestChunkSizeParameterization` 测试类（5 个用例）
- `frontend/src/entities/knowledge/types.ts` — 新增 `KnowledgeChunkSize`、`KnowledgeIndexRefreshScope`、`RefreshKnowledgeIndexPayload`、`RefreshKnowledgeIndexResponse`、label 和 description map
- `frontend/src/entities/knowledge/api.ts` — 新增 `refreshKnowledgeIndex()` API 函数
- `frontend/src/pages/knowledge/ProjectKnowledgePage.vue` — 移除技术按钮，添加"刷新知识索引"入口，改造索引片段标签和空状态文案，集成刷新对话框
- `frontend/src/features/knowledge/KnowledgeSearchPanel.vue` — "分块"→"片段"，"向量索引"→"知识索引"等用户文案更新
- `frontend/src/features/knowledge/KnowledgeAskPanel.vue` — "检索相关分块"→"检索相关片段"

### 未修改（保留）
- 旧技术 API（`POST .../embeddings/rebuild`、`POST .../embeddings`、`GET .../embeddings/status`）全部保留
- RAG、AI 总结、向量检索核心逻辑未触碰
- 数据库模型和迁移未改动

## Implementation Notes

### 分块大小配置
| 选项 | 字符范围 | 说明 |
|---|---|---|
| 小 | 350–600 | 更容易命中细节，但内容更碎 |
| 中（默认） | 800–1200 | 与原默认值一致，保持行为不变 |
| 大 | 1500–2200 | 上下文更完整，细节命中可能下降 |

- `create_source()` 和 `update_source()` 仍使用默认 `medium`，不影响现有自动分块行为
- `metadata_json` 记录 `{"chunk_size": "small"}` 等信息便于排障

### 刷新流程
- 项目级：获取所有活跃资料 → 逐个重建分块 → 删除旧项目嵌入 → 重建项目索引
- 资料级：重建当前资料分块 → 删除旧资料嵌入 → 重建资料索引
- 空内容资料不报错，返回 warning

### 页面改造细节
移除的作者可见技术按钮和文案：
- "重建分块"按钮
- "生成向量"按钮
- "向量索引：x / y"状态
- "重建全部索引"链接按钮
- "分块预览"标签名

新增/替代：
- 页面 header 操作区新增"刷新知识索引"按钮（secondary 样式）
- 右侧标签改为"索引片段"
- 状态文案改为"索引状态：已准备 x / y 个片段"
- 空状态改为"暂无索引片段。保存或导入资料后系统会自动整理；如果搜索不到新内容，可以刷新知识索引。"
- `token_count` 显示改为"约 N 字"

### 对话框特性
- 范围选择：全部资料 / 当前资料（未选中资料时禁用"当前资料"）
- 分块大小选择：小 / 中（推荐） / 大，风险说明随选择变化
- 未保存变更检测：表单有未保存改动时禁止刷新并显示警告
- 防重复提交：刷新进行中禁用按钮
- 完成后自动刷新索引状态、分块列表和资料列表

### 用户分块大小选择不持久化
用户选择的 chunk_size 仅用于当次刷新操作，不保存到数据库或 localStorage。下次刷新时仍默认 medium。如果未来需要项目级永久配置，可新增设置表或 localStorage 记忆。

## Deviations from Codex Plan
无。完全按照 Codex Plan 实现。

## Verification Commands Run
- `pytest tests/test_knowledge_service.py tests/test_knowledge_index_refresh_service.py` → ✅ 37 passed
- `pytest`（完整后端测试） → ✅ 189 passed
- `npm run type-check` → ✅
- `npm run test:unit -- --run` → ✅ 80 passed
- `npm run build` → ✅

## Verification Results
全部通过。后端 189 个测试、前端 80 个单元测试均通过。类型检查和生产构建无错误。

## Known Issues
1. 用户分块大小选择不持久化 — 每次刷新默认 medium，符合 Codex Plan 设计
2. `isIndexing` 状态变量从页面中移除（旧 handler 函数已删除，不再需要）
3. `link-button` CSS 类从页面样式中移除（旧"重建全部索引"链接按钮不再使用）

## Suggested Next Review Points for Codex
1. 分块大小字符范围是否合理（small: 350-600, medium: 800-1200, large: 1500-2200）
2. 搜索面板和问答面板的"分块"→"片段"文案替换是否完整
3. 刷新对话框的 UX 流程是否流畅
4. 是否需要将 chunk_size 选择持久化到 localStorage
