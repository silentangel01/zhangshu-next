# Task Summary

整理“知识库模块”的分阶段执行计划。知识库用于外部资料、灵感素材、参考内容和研究材料，与“设定集”的本书内部 canon 信息保持边界。后续 RAG、向量检索、AI 总结/梳理应建立在知识库资料源、分块、元数据和引用边界之上，而不是直接混入设定、正文或普通资料模块。

本计划是知识库模块路线图和第一期实施边界说明。Codex 未修改业务代码。本计划交由 Claude Code 在用户确认具体阶段后执行。

# Current Codebase Findings

1. 已阅读 Claude Code 最新执行报告：
   - 上一任务为 `Creative Reminder Module Upgrade - Structured Reminders with Reason/Suggestion`。
   - Claude 已完成规则提醒结构化升级、前后端字段同步、后端测试和验证。
2. 旧交接文件已按生命周期规则归档到：
   - `docs/ai-handoff/archive/2026-05-23-creative-reminder-upgrade/CODEX_PLAN.md`
   - `docs/ai-handoff/archive/2026-05-23-creative-reminder-upgrade/CLAUDE_EXECUTION_REPORT.md`
3. `docs/开发说明.md` 明确写到：
   - 知识库是后续模块，用于外部资料、灵感素材、参考内容和研究材料。
   - 不要把外部素材混入设定集。
   - 当前暂不导入人物、关系图、时间线、知识库等复杂资料。
   - 当前不做 AI、语义或关键词匹配。
4. 当前代码中没有独立知识库模块：
   - 没有 `backend/app/api/knowledge.py`
   - 没有 `backend/app/models/knowledge*.py`
   - 没有 `backend/app/services/knowledge*.py`
   - 没有 `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`
   - 没有 `frontend/src/entities/knowledge/`
5. 当前已有可复用边界：
   - 后端 API / Service / Repository / Model / Schema 分层已存在。
   - 资料间显式关联已有 `material_links` 体系，但目前主要覆盖大纲、时间线与人物/设定/伏笔等关系。
   - 导入模块已有 txt/md/docx 基础文本解析能力，可作为后续知识库导入参考，但本阶段不要直接复用成复杂导入器。
   - 搜索模块当前是 SQLite LIKE；未来知识库可先走 LIKE，再扩展到 chunk 检索和向量检索。
6. 当前设定页已有边界文案：
   - 设定集保存本书内部设定。
   - 外部素材和参考资料后续放入知识库模块。

# Architecture Decision

1. 知识库分阶段建设，不建议一次性实现 RAG、向量库、AI 总结和自动抽取。
2. 第一阶段只建设“可信资料层”：
   - 资料源 source。
   - 正文 content。
   - 标签、来源、可信度、状态。
   - 自动或手动分块 chunk 的基础结构。
   - 与项目/章节/人物/设定/伏笔/时间线/关系图节点的参考关联。
3. 第二阶段建设“检索层”：
   - 标题、正文、标签搜索。
   - chunk 级结果。
   - 引用定位。
   - 不做模型调用。
4. 第三阶段建设“向量与 RAG 准备层”：
   - embedding provider 抽象。
   - vector store 抽象。
   - chunk embedding 状态。
   - 重建索引任务边界。
   - 仍不让 AI 自动修改业务数据。
5. 第四阶段再接入 RAG / AI 总结：
   - 回答必须带引用。
   - AI 结果默认是草稿或建议。
   - AI 结果不得直接覆盖设定、正文、人物、伏笔等核心数据。
6. 知识库与设定集必须保持语义边界：
   - 知识库是 reference。
   - 设定是 canon。
   - RAG 检索时必须能区分 reference 与 canon。

# Files to Create or Modify

本计划先给出完整阶段路线。Claude Code 执行时应只实现用户指定阶段，不要一次性完成所有阶段。

## Phase K1: 知识库资料管理基础

后端建议新增：

- `backend/app/models/knowledge_source.py`
- `backend/app/models/knowledge_chunk.py`
- `backend/app/models/knowledge_link.py`
- `backend/app/schemas/knowledge.py`
- `backend/app/repositories/knowledge_repo.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/api/knowledge.py`
- 修改 `backend/app/main.py` 注册 router
- 修改 `backend/app/infrastructure/database.py` 做启动时兼容建表或列补齐
- 新增 `backend/tests/test_knowledge_service.py`

前端建议新增：

- `frontend/src/entities/knowledge/types.ts`
- `frontend/src/entities/knowledge/api.ts`
- `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`
- 修改 `frontend/src/router/index.ts` 增加 `/projects/:projectId/knowledge`
- 视需要修改 `frontend/src/pages/projects/ProjectDetailPage.vue`，增加知识库入口
- 可选新增 `frontend/src/__tests__/knowledge.spec.ts`

## Phase K2: 知识库导入与检索增强

后端可能新增或修改：

- `backend/app/services/knowledge_import_service.py`
- `backend/app/api/knowledge.py`
- `backend/app/utils/import_parsers.py`，仅复用文本解析 helper，不要破坏作品导入
- `backend/tests/test_knowledge_import.py`

前端可能新增或修改：

- `frontend/src/features/knowledge/KnowledgeImportDialog.vue`
- `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`

## Phase K3: Chunk 检索与引用定位

后端可能新增：

- `backend/app/services/knowledge_retrieval_service.py`
- `backend/app/schemas/knowledge_retrieval.py`
- `backend/app/api/knowledge_retrieval.py`

前端可能新增：

- `frontend/src/features/knowledge/KnowledgeSearchPanel.vue`
- `frontend/src/features/knowledge/KnowledgeChunkList.vue`

## Phase K4: 向量检索基础设施

后端可能新增：

- `backend/app/models/knowledge_embedding.py`
- `backend/app/infrastructure/embedding_provider.py`
- `backend/app/infrastructure/vector_store.py`
- `backend/app/services/knowledge_embedding_service.py`
- `backend/app/services/retrieval_service.py`

注意：K4 才允许讨论 embedding 和 vector store；K1/K2 不接真实 AI。

## Phase K5: RAG / AI 总结与梳理

后端可能新增：

- `backend/app/services/rag_service.py`
- `backend/app/services/ai_summary_service.py`
- `backend/app/schemas/rag.py`
- `backend/app/api/rag.py`

前端可能新增：

- `frontend/src/features/knowledge/KnowledgeAskPanel.vue`
- `frontend/src/features/knowledge/KnowledgeSummaryPanel.vue`

# Implementation Steps for Claude Code

## 总体阶段规划

1. Phase K1: 知识库资料管理基础
   - 目标：先让用户能保存、编辑、搜索和关联外部资料。
   - 不做 AI。
   - 不做向量。
   - 不做自动总结。
   - 不做网页爬取。
   - 建议作为第一个真正执行阶段。

2. Phase K2: 导入与基础检索
   - 目标：支持 txt/md/docx 基础文本导入到知识库，生成资料源和 chunk。
   - 检索仍以 SQLite LIKE 和结构化筛选为主。
   - 不做 embedding。

3. Phase K3: Chunk 检索与引用定位
   - 目标：把检索结果从 source 级升级到 chunk 级。
   - 支持结果定位、上下文展示、引用复制。
   - 为 RAG 提供 clean context。

4. Phase K4: 向量检索基础
   - 目标：加入 embedding 和 vector store 抽象。
   - 允许生成 chunk embedding。
   - 支持向量相似度检索。
   - 必须隔离在 infrastructure/service 层。

5. Phase K5: RAG / AI 总结
   - 目标：基于检索结果回答问题或生成总结。
   - 回答必须带引用。
   - AI 输出只能作为建议或草稿。
   - 不得自动覆盖正文、设定或其他业务数据。

## Phase K1 详细建议

1. 数据模型
   - 新增 `KnowledgeSource`：
     - `id`
     - `project_id`
     - `title`
     - `source_type`: `note` / `file` / `webpage` / `book` / `quote` / `custom`
     - `source_uri`
     - `author`
     - `summary`
     - `content`
     - `tags`
     - `status`: `active` / `archived`
     - `credibility`: `low` / `normal` / `high`
     - `created_at`
     - `updated_at`
     - `deleted_at`
     - `version`
   - 新增 `KnowledgeChunk`：
     - `id`
     - `project_id`
     - `source_id`
     - `chunk_index`
     - `heading`
     - `content`
     - `token_count`
     - `metadata_json`
     - `created_at`
     - `updated_at`
     - `deleted_at`
   - 新增 `KnowledgeLink`：
     - `id`
     - `project_id`
     - `source_id`
     - `chunk_id`
     - `target_type`: `project` / `chapter` / `character` / `setting` / `clue` / `timeline_event` / `graph_node`
     - `target_id`
     - `relation_type`: `reference` / `inspiration` / `evidence` / `background` / `related`
     - `note`
     - `created_at`
     - `deleted_at`

2. 后端 API
   - `GET /api/projects/{project_id}/knowledge-sources`
     - 支持 query：`keyword`、`source_type`、`status`、`tag`、`credibility`
   - `POST /api/projects/{project_id}/knowledge-sources`
   - `GET /api/knowledge-sources/{source_id}`
   - `PATCH /api/knowledge-sources/{source_id}`
   - `DELETE /api/knowledge-sources/{source_id}`
   - `GET /api/knowledge-sources/{source_id}/chunks`
   - `POST /api/knowledge-sources/{source_id}/rebuild-chunks`
   - `GET /api/knowledge-sources/{source_id}/links`
   - `POST /api/knowledge-sources/{source_id}/links`
   - `DELETE /api/knowledge-links/{link_id}`

3. Chunk 策略
   - K1 可使用简单规则：
     - 按标题或空行分段。
     - 每个 chunk 约 800-1200 中文字符。
     - 超长段落按长度切分。
   - 保存 chunk 时保留 `chunk_index` 和 `heading`。
   - 重新分块时软删除旧 chunk 或直接替换，需要在计划中明确。建议 K1 采用删除旧 active chunk 后重建，embedding 尚未引入，不涉及向量同步。

4. 前端页面
   - 路由：`/projects/:projectId/knowledge`
   - 页面布局：
     - 顶部：返回写作页、搜索框、筛选按钮、新建资料。
     - 左侧：资料源列表，显示标题、类型、标签、状态、可信度。
     - 中间：资料详情编辑，包括标题、来源、摘要、正文、标签。
     - 右侧：关联对象与 chunk 预览。
   - 页面文案必须明确：
     - `知识库用于保存外部参考资料，不会自动写入本书设定。`

5. 项目入口
   - 在 `ProjectDetailPage.vue` 中增加“知识库”入口。
   - 不要把知识库塞进写作页右侧面板作为完整管理页。
   - 后续可在写作页右侧增加“相关参考摘要”，但 K1 不做。

## Phase K2 详细建议

1. 支持导入：
   - 手动粘贴文本。
   - `.txt`
   - `.md`
   - `.docx` 基础段落文本。
2. 导入后创建 `KnowledgeSource`，并自动生成 chunk。
3. 导入报告应列出：
   - 成功资料数。
   - 失败文件。
   - 编码或解析警告。
4. 不要把作品导入和知识库导入混成同一个流程。

## Phase K3 详细建议

1. 新增 chunk 级检索接口。
2. 搜索结果展示：
   - 来源标题。
   - chunk heading。
   - 命中片段。
   - 上下文。
   - 打开 source。
   - 复制引用。
3. 这一步开始为 RAG 准备“可引用上下文”。

## Phase K4 详细建议

1. 新增 embedding 抽象，但不要直接把模型调用写进 API 或 UI。
2. `EmbeddingProvider` 只负责把文本变成向量。
3. `VectorStore` 只负责写入和相似度查询。
4. `RetrievalService` 组合关键词、metadata 和向量结果。
5. 向量检索必须带 metadata：
   - `project_id`
   - `source_id`
   - `chunk_id`
   - `source_type`
   - `credibility`
   - `tags`
6. 如果用户未明确要求真实模型，K4 只能做接口和边界，不接外部 API。

## Phase K5 详细建议

1. RAG 回答必须包含引用 source/chunk。
2. AI 总结结果应保存为草稿或建议，不自动写入设定。
3. 如果要把知识库内容转为设定，必须经过用户确认。
4. AI 结果应标记：
   - `created_from: "ai"`
   - 来源 chunk 列表。
   - 生成时间。

# Constraints

1. 不要把外部参考资料写入 `setting_items`。
2. 不要把知识库第一期做成 AI 问答。
3. 不要在 K1/K2 接入真实 embedding、RAG 或外部模型。
4. 不要把 embedding/vector 逻辑写入 Vue 组件、API router 或普通 Repository。
5. 不要让 AI 自动覆盖正文、设定、人物、伏笔、时间线或关系图数据。
6. 不要新增大型依赖，除非用户确认进入向量检索阶段并明确选型。
7. 不要破坏已有 Project / Volume / Chapter / Import / Setting / Character / Clue / Timeline / Graph API。
8. 所有用户可见文案必须为简体中文。
9. 所有软删除表使用 `deleted_at`。
10. 知识库资料必须按 `project_id` 隔离，不能跨项目泄漏。

# Verification Commands

Claude Code 执行具体阶段后，应至少运行：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
pytest
```

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit -- --run
npm run build
```

Phase K1 额外建议：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
pytest tests/test_knowledge_service.py
```

手动检查建议：

```text
/projects/:projectId/knowledge
新建知识资料
编辑知识资料
删除或归档知识资料
搜索标题/正文/标签
重建 chunks
关联到章节、人物、设定、伏笔、时间线事件
确认知识库文案没有暗示 AI 已启用
```

# Acceptance Criteria

## Phase K1 验收

1. 项目下存在独立知识库页面入口。
2. 用户可以创建、编辑、软删除或归档知识资料。
3. 知识资料支持标题、类型、来源、摘要、正文、标签、状态、可信度。
4. 知识资料自动生成基础 chunk。
5. 用户可以查看 chunk 列表。
6. 用户可以将知识资料或 chunk 关联到章节、人物、设定、伏笔、时间线事件或关系图节点。
7. 知识库不会写入或覆盖设定集。
8. 后端测试覆盖创建、更新、删除、搜索、分块、关联。
9. 前端 type-check、unit test、build 通过。

## Phase K2 验收

1. 支持 txt/md/docx 基础文本导入知识库。
2. 导入不会创建章节或项目正文。
3. 导入报告清楚展示成功和失败。
4. 导入后自动生成 chunk。

## Phase K3 验收

1. 支持 chunk 级搜索。
2. 搜索结果能定位到 source 和 chunk。
3. 结果可复制引用。

## Phase K4 验收

1. embedding provider 和 vector store 边界清晰。
2. 向量索引不混入普通业务表操作。
3. 检索结果携带引用 metadata。

## Phase K5 验收

1. RAG 回答必须带引用。
2. AI 输出不会自动覆盖业务数据。
3. 用户可以明确区分 AI 建议、外部资料和本书设定。

# Risks and Watchpoints

1. 最大风险是把知识库做成设定集的另一个版本，导致 reference 和 canon 混淆。
2. 如果第一期就做 AI/RAG，容易在数据结构未稳定前产生技术债。
3. Chunk 设计如果缺少 source_id、chunk_index、metadata，后续向量检索会很难补。
4. 知识库关联如果复用现有 material links，需要谨慎评估字段和 target 类型，不要硬塞造成语义混乱。
5. SQLite 文本搜索可先满足 MVP，但未来大规模资料需要 FTS5 或向量检索。
6. DOCX 解析只能作为基础文本提取，不应承诺保留复杂 Word 样式。
7. 知识库导入文件可能很大，K2 需要限制大小和处理失败报告。
8. 后续 embedding 若使用外部 API，必须考虑密钥、本地配置、网络失败和成本控制。

# Review Checklist

Codex 复审时应检查：

1. 是否遵守知识库与设定集边界。
2. 是否只执行用户确认的阶段，没有一次性扩展到 RAG/AI。
3. 是否符合后端 API / Service / Repository / Model / Schema 分层。
4. 是否出现 UI、业务逻辑、数据访问、AI 调用混杂。
5. 是否新增无理由依赖。
6. 是否所有知识库数据按 `project_id` 隔离。
7. 是否所有软删除表使用 `deleted_at`。
8. 是否为未来 RAG 保留 source、chunk、metadata、link 边界。
9. 是否没有自动写入或覆盖设定、正文和其他业务数据。
10. 是否补充必要测试。
11. 是否有不该提交的密钥、本地配置、临时文件、数据库或日志。
12. 最终建议应明确为 Accept、Minor Revision 或 Rework。
