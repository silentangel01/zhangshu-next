<!-- Archived before planning knowledge-retrieval-quality-tuning on 2026-05-24. -->

# Codex Review

## Review Scope

本次复审读取了：

- `docs/ai-handoff/CODEX_PLAN.md`
- `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`
- 当前 `git diff`
- 关键实现文件：知识库向量 provider、profile、刷新索引、语义检索、前端刷新弹窗。

本轮 Codex 未修改业务代码。

## Overall Judgment

最终建议：**Rework**

理由：Claude Code 的总体方向符合原计划，provider factory、DashScope provider、profile 表、vector store 模型过滤等核心边界基本建立起来了。但当前前端“全部资料刷新”仍然逐条调用 `scope: "source"`，没有走后端 `refresh_project()`。这会绕开项目级 profile 写入逻辑，导致“云端索引已生成但语义检索仍使用默认本地 provider”的高风险问题，直接违反原计划的“索引向量和查询向量必须一致”验收标准。

## Compliance With Original Plan

基本符合：

- DashScope provider 放在 `backend/app/infrastructure/`，没有写进 UI 或 API 层；
- provider factory 已建立；
- `VectorStore.search()` 已增加 `model_name` / `vector_dim` 过滤；
- cloud provider 需要隐私确认；
- 未配置 DashScope key 时 provider 不可用；
- bge 本地模型暂作为不可用占位，没有引入重依赖；
- 测试中 mock 了 DashScope，不真实联网。

存在偏差：

- `KnowledgeIndexProfile` 未包含原计划建议的 `provider_type`、`display_name`、`chunk_size`、`status`、`last_refreshed_at`、`last_error`。
- `IndexStatusResponse` / `IndexProfileResponse` 未返回 `profile_status`、`chunk_size`、最近刷新时间等状态信息。
- `embedding_settings.py` 未读取 `ZHANGSHU_LOCAL_EMBEDDING_MODEL_PATH`。
- DashScope 未用真实 API Key 做人工验证，这一点可以接受为待验证项，但必须保留在后续执行报告中。
- 前端 project scope 刷新实现与后端 project scope 设计不一致，是本次最主要偏差。

## Findings

### P1 - 前端“全部资料刷新”绕开后端 project refresh，导致 profile 不写入

相关位置：

- `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue:203`
- `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue:236`
- `backend/app/services/knowledge_index_refresh_service.py:147`
- `backend/app/services/retrieval_service.py:297`

前端 `refreshProjectScope()` 当前先 `listKnowledgeSources()`，然后逐个 source 调用：

```ts
refreshKnowledgeIndex(projectId, {
  scope: 'source',
  source_id: source.id,
  ...
})
```

但后端只有 `refresh_project()` 成功后才 `profile_repo.upsert(...)`。`refresh_source()` 不会更新 profile。

结果：

- 用户首次选择“云端精准索引”并刷新“全部资料”时，前端实际发出多次 source scope 请求；
- 后端会生成 DashScope embeddings，但项目 profile 可能仍为空；
- 后续语义检索进入 `RetrievalService._resolve_query_provider()`，profile 为空时会回到默认 provider；
- 查询向量与索引向量不在同一个向量空间，语义检索可能直接失效或命中异常。

这违反原计划的向量一致性规则，必须优先修复。

### P1 - 已有 profile 时，前端无法通过“全部资料刷新”切换 provider

相关位置：

- `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue:236`
- `backend/app/services/knowledge_index_refresh_service.py:185`

原计划要求：provider 变更时，用户选择“全部资料”应允许全量切换模型。

当前前端即使用户选的是“全部资料”，仍逐条发 source scope 请求；一旦 `provider_id` 与已有 profile 不一致，后端会按 source-scope 冲突规则返回 409。这意味着 UI 上的“全部资料刷新”无法完成 provider 切换。

### P2 - profile 状态字段缺失，无法表达 ready / stale / error / not_configured

相关位置：

- `backend/app/models/knowledge_index_profile.py:19`
- `backend/app/api/knowledge_embedding.py:230`
- `backend/app/services/knowledge_embedding_service.py:172`

原计划要求 profile 能表达 `status`、`chunk_size`、`last_refreshed_at`、`last_error`。当前 profile 只记录 `provider_id`、`model_name`、`vector_dim`。

影响：

- 前端无法判断索引是已就绪、未配置、过期还是失败；
- 用户看到的索引状态仍偏“计数展示”，不能清楚提示“需要刷新”；
- 后续接入 RAG、AI 总结时，无法可靠判断当前知识索引是否可用。

### P2 - 索引状态计数没有按当前 profile 过滤

相关位置：

- `backend/app/services/knowledge_embedding_service.py:190`

`get_index_status()` 当前统计所有 `KnowledgeEmbedding.project_id == project_id` 的 embeddings。既然系统已经引入 provider/model 过滤，状态统计也应按当前 profile 的 `model_name` / `vector_dim` 统计，否则混入历史 embeddings 时会误报“已索引”。

### P2 - 旧 embedding API 仍可绕开 profile 体系

相关位置：

- `backend/app/api/knowledge_embedding.py:61`
- `backend/app/api/knowledge_embedding.py:80`

旧接口：

- `POST /api/projects/{project_id}/knowledge/embeddings/rebuild`
- `POST /api/knowledge-sources/{source_id}/embeddings`

仍然直接调用 `KnowledgeEmbeddingService.rebuild_project_index()` / `index_source()`，不会显式处理 provider_id、privacy_confirmed，也不会更新或校验 profile。虽然前端已不使用这些按钮，但 API 仍存在，未来调用方可能绕开新的一致性规则。

### P2 - 当前 diff 中存在本轮向量计划外的文件变更

当前 `git diff --name-status` 中仍包含知识库导入、知识库 UI、章节编辑器等文件变更，例如：

- `backend/app/api/knowledge.py`
- `backend/app/services/knowledge_import_service.py`
- `backend/app/utils/import_parsers.py`
- `frontend/src/features/chapters/ChapterEditor.vue`
- `frontend/src/features/knowledge/KnowledgeImportDialog.vue`
- `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`

这些可能是前序任务残留，不一定是本轮 Claude 造成的偏差。但提交前需要按任务拆分确认，避免把多个任务的变更混在一个提交里。

## Architecture Boundary Check

整体边界判断：

- UI 没有直接调用 DashScope；
- DashScope 调用在 infrastructure 层；
- vector store 保持在 infrastructure 层；
- profile 持久化有 repository；
- API 层主要做错误映射；
- 未看到密钥写入或日志输出正文内容。

需要修正的边界点：

- 刷新 orchestration 的真实主路径应统一走后端 project refresh service，不应由前端拆成多次 source refresh 来模拟 project refresh；
- 旧 embedding API 应纳入新 profile 体系，或明确标记为内部/废弃接口。

## Potential Bugs

- 首次云端全量刷新后 profile 为空，语义搜索回到默认本地 provider；
- 已有本地 profile 时，用户无法通过 UI 切换到云端 provider；
- 索引状态可能把历史模型的 embeddings 计入当前模型；
- 旧 rebuild/source embeddings API 可能制造 profile 与 embeddings 不一致；
- profile 缺少 error/stale 状态，失败后前端无法准确提示。

## Test Gaps

需要补充测试：

- 前端 project scope 刷新必须只调用一次 `scope: "project"`，而不是 N 次 `scope: "source"`；
- API project scope refresh 成功后必须创建/更新 profile；
- 通过 API project scope 使用 cloud provider 后，retrieval 必须使用同 provider；
- 已有 profile 时，source scope 不允许 provider 切换，project scope 允许 provider 切换；
- `get_index_status()` 在存在混合 embeddings 时只统计当前 profile 模型；
- 旧 `/embeddings/rebuild` 和 `/knowledge-sources/{source_id}/embeddings` 的行为必须被测试为：要么走新 profile 流程，要么返回废弃提示。

## Secret / Local File Check

未在已读 diff 中发现 API key、token、`.env`、本地数据库、日志或模型文件被提交。

`git diff --check` 通过，没有发现尾随空格或常见 patch 格式问题。

## Next Step Plan for Claude Code

### Task Summary

修正知识库向量升级实现中的 profile 一致性偏差，使“刷新知识索引”的前端主路径、后端 project refresh、profile、语义检索完全一致。

### Files to Create or Modify

优先修改：

- `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue`
- `backend/app/services/knowledge_embedding_service.py`
- `backend/app/services/knowledge_index_refresh_service.py`
- `backend/app/models/knowledge_index_profile.py`
- `backend/app/repositories/knowledge_index_profile_repo.py`
- `backend/app/schemas/knowledge_embedding.py`
- `backend/app/api/knowledge_embedding.py`
- `backend/tests/test_knowledge_index_refresh_service.py`
- `backend/tests/test_retrieval_service.py`
- `backend/tests/test_vector_store.py`

按需修改：

- `frontend/src/entities/knowledge/types.ts`
- `frontend/src/entities/knowledge/api.ts`
- `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`
- 前端知识库相关测试文件，如现有测试框架允许。

### Implementation Steps for Claude Code

1. 修正前端 project scope 刷新主路径
   - 在 `KnowledgeIndexRefreshDialog.vue` 中，`scope === "project"` 时直接调用一次：
     - `refreshKnowledgeIndex(projectId, { scope: "project", chunk_size, provider_id, privacy_confirmed })`
   - 不要再把 project scope 拆成多个 source scope 请求。
   - 若仍希望保留进度条，本轮可展示“正在刷新全部资料”的 indeterminate/单阶段进度；不要为了进度破坏后端一致性。
   - `scope === "source"` 时继续调用 source scope。

2. 修正 provider 切换交互
   - 当 `selectedProviderId !== currentProviderId` 且用户选择“当前资料”时：
     - 禁止提交，并提示“切换索引模式需要刷新全部资料”；或
     - 自动切换到“全部资料”。
   - 不要让用户点击后才收到 409。

3. 扩展 `KnowledgeIndexProfile`
   - 新增字段：
     - `provider_type`
     - `display_name`
     - `chunk_size`
     - `status`
     - `last_refreshed_at`
     - `last_error`
   - 对已有 SQLite 数据库补兼容逻辑。项目当前没有 Alembic，建议在 `database.py` 中新增最小 `_ensure_knowledge_index_profile_columns()`。
   - 新增字段默认值应保证旧库可启动。

4. 扩展 profile repository
   - `upsert()` 接收 provider descriptor、chunk_size、status；
   - 新增 `mark_error(project_id, error)`；
   - 新增 `mark_stale(project_id)`，供后续资料变更时调用；
   - 暂时不强制所有资料编辑都调用 `mark_stale`，但接口先准备好。

5. 扩展 refresh service
   - `refresh_project()` 成功后写入：
     - provider_id
     - provider_type
     - display_name
     - model_name
     - vector_dim
     - chunk_size
     - status = `"ready"`
     - last_refreshed_at
     - last_error = None
   - cloud provider 调用失败时，记录 `status = "error"` 和简短错误，不记录正文或 key。
   - source scope 成功时：
     - 如果 profile 存在且 provider 一致，可以保持 profile ready；
     - 如果 profile 不存在，允许使用默认 provider 建立 profile，或明确要求用户先执行 project scope；二选一并写测试。

6. 修正 index status
   - `get_index_status()` 如果 profile 存在，应只统计当前 `model_name` / `vector_dim` 的 embeddings；
   - response 增加：
     - `profile_status`
     - `provider_display_name`
     - `chunk_size`
     - `last_refreshed_at`
     - `last_error`
   - 如果 profile 不存在，返回 `profile_status = "not_configured"`。

7. 处理旧 embedding API
   - 推荐方案：保留兼容端点，但内部改为调用 `KnowledgeIndexRefreshService.refresh_project()` 或 `refresh_source()`；
   - 如果不支持 provider 参数，则默认使用当前 profile provider；无 profile 时使用默认 provider 并创建 profile；
   - 不要让旧端点直接写 embeddings 而不更新 profile。

8. 补测试
   - 增加后端测试覆盖：
     - project scope API 刷新创建 profile；
     - project scope provider 切换允许；
     - source scope provider 切换拒绝；
     - index status 按 profile 过滤 embeddings；
     - 旧 endpoints 不绕开 profile。
   - 增加前端测试或最小组件测试：
     - project scope 只发送一次 project refresh payload；
     - provider 改变时 source scope 不能提交。

9. 更新 Claude 执行报告
   - 完成后更新 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`；
   - 明确说明上述 Rework 项是否全部处理；
   - 说明是否仍未真实验证 DashScope API。

### Verification Commands

后端：

```powershell
cd backend
python -m pytest tests/test_knowledge_index_refresh_service.py
python -m pytest tests/test_knowledge_embedding_service.py
python -m pytest tests/test_retrieval_service.py
python -m pytest tests/test_vector_store.py
python -m pytest tests/test_embedding_provider_factory.py
python -m pytest tests/test_dashscope_embedding_provider.py
python -m pytest
```

前端：

```powershell
cd frontend
npm run type-check
npm run test:unit -- --run
npm run build
```

手动验证：

- 无 profile 时，选择本地基础并刷新全部资料后，profile 创建成功；
- 无 profile 时，选择云端精准并刷新全部资料后，profile 创建成功，语义检索使用云端 provider；
- 已有本地 profile 时，选择云端精准 + 当前资料不能提交；
- 已有本地 profile 时，选择云端精准 + 全部资料可以提交；
- 刷新后知识库页面显示当前索引模式和状态；
- 云端 API key 未配置时，云端精准模式仍不可选；
- 日志和控制台不出现 key 或知识库正文。

### Acceptance Criteria

- project scope 前端请求不再拆成 source scope；
- profile 与 embeddings 在 project refresh 后一致；
- semantic / hybrid 检索使用当前 profile provider；
- provider 切换只允许通过 project scope；
- index status 能表达 ready / stale / error / not_configured；
- 旧 embedding API 不再绕开 profile；
- 全部新增/修改测试通过；
- 未提交密钥、本地数据库、日志、模型文件。
