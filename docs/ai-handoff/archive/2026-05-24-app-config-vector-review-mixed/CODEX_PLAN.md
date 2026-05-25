<!-- Archived before planning knowledge-retrieval-quality-tuning on 2026-05-24. -->

# Task Summary

本计划用于升级章枢知识库的向量功能：从当前的伪向量 `bigram-hash-v1` 逐步升级为“本地离线可用 + 联网高精度 API 可选”的真实向量体系。

目标不是把技术细节暴露给网文作者，而是在“刷新知识索引”入口中提供清晰的人类可理解选项：

- 本地基础/离线模式：无网络、资料不上传，可作为兼容兜底；
- 本地高质量模式：后续通过本地模型文件实现，适合离线但质量更高的检索；
- 云端精准模式：优先接入阿里云百炼 DashScope `text-embedding-v4`，联网、精度更高，但必须明确告知资料片段会发送给服务商；
- 未来可扩展 OpenAI、Voyage、Cohere 或其他向量模型，但本轮不要一次性堆太多供应商。

Codex 未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

已阅读 Claude Code 上一轮执行报告，并已将旧交接文件归档到：

`docs/ai-handoff/archive/2026-05-24-knowledge-ui-polish/`

当前代码库发现如下：

- 前端知识库模块位于 `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`、`frontend/src/features/knowledge/`、`frontend/src/entities/knowledge/`。
- 当前刷新索引入口是 `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue`，已有：
  - 刷新范围：全部资料 / 当前资料；
  - 索引片段大小：小 / 中 / 大；
  - 刷新进度条；
  - 刷新结果展示。
- 前端类型与 API 位于：
  - `frontend/src/entities/knowledge/types.ts`
  - `frontend/src/entities/knowledge/api.ts`
- 后端知识索引接口位于 `backend/app/api/knowledge_embedding.py`，当前接口包括：
  - `POST /api/projects/{project_id}/knowledge/embeddings/rebuild`
  - `POST /api/knowledge-sources/{source_id}/embeddings`
  - `GET /api/projects/{project_id}/knowledge/embeddings/status`
  - `POST /api/projects/{project_id}/knowledge/index/refresh`
- 后端请求/响应 Schema 位于 `backend/app/schemas/knowledge_embedding.py`，当前 `RefreshKnowledgeIndexRequest` 只有 `scope`、`source_id`、`chunk_size`。
- 当前向量 Provider 位于 `backend/app/infrastructure/embedding_provider.py`：
  - `EmbeddingProvider` 协议包含 `encode()`、`encode_batch()`、`model_name`、`vector_dim`；
  - `BigramHashEmbeddingProvider` 是 256 维哈希伪向量，`model_name = "bigram-hash-v1"`；
  - 该 provider 不是真实语义向量，只适合开发/兼容兜底。
- 当前向量存储位于 `backend/app/infrastructure/vector_store.py`：
  - `SqliteVectorStore` 使用 `knowledge_embeddings.vector_json` 存 JSON；
  - 通过 numpy 进行暴力 cosine similarity；
  - 当前搜索没有按 `model_name` / `vector_dim` 过滤，未来混用不同模型时有风险。
- 当前向量数据模型位于 `backend/app/models/knowledge_embedding.py`：
  - 字段已有 `model_name` 和 `vector_dim`；
  - 没有记录项目当前启用的 provider/profile 状态；
  - 没有记录云端/本地模式、隐私提示确认状态、最后刷新状态。
- `KnowledgeEmbeddingService` 位于 `backend/app/services/knowledge_embedding_service.py`：
  - 默认直接实例化 `BigramHashEmbeddingProvider()`；
  - 索引来源、单个 chunk、整项目重建都走该 provider。
- `RetrievalService` 位于 `backend/app/services/retrieval_service.py`：
  - 语义搜索和混合搜索会用 provider 给查询文本生成 query vector；
  - 当前同样默认实例化 `BigramHashEmbeddingProvider()`；
  - 如果只升级索引 provider、不升级查询 provider，会导致查询向量和索引向量不在同一向量空间。
- `KnowledgeIndexRefreshService` 位于 `backend/app/services/knowledge_index_refresh_service.py`：
  - 负责重建 chunks 并刷新 embeddings；
  - 当前构造时直接创建 `KnowledgeEmbeddingService(db)`。
- 后端依赖 `backend/requirements.txt` 已有 `httpx`、`numpy`，没有 `sentence-transformers`、`onnxruntime` 或云厂商 SDK。
- 当前数据库初始化位于 `backend/app/infrastructure/database.py`：
  - 使用 SQLAlchemy `Base.metadata.create_all(bind=engine)`；
  - 现有兼容升级通过 `_ensure_*` 手写函数完成；
  - 未发现标准 Alembic 迁移目录。

# Architecture Decision

## 总体方向

采用“Provider 抽象 + 项目级索引 Profile + 本地 SQLite 向量存储”的渐进升级。

本轮不建议直接把 DashVector、AnalyticDB 或其他云端向量数据库接进来。章枢当前是本地写作辅助软件，知识库资料通常包含作者私有设定、剧情和人物信息。第一阶段应保持向量存储在本地 SQLite，只把 embedding 计算能力抽象出来。

阿里云相关建议：

- 优先接入阿里云百炼 / DashScope 的文本向量模型，例如 `text-embedding-v4`，作为“云端精准模式”；
- 暂不接入 DashVector 作为主存储；
- DashVector 或 AnalyticDB 向量检索服务可作为未来云同步、多设备、团队协作阶段的独立 VectorStore adapter，而不是现在直接替换 SQLite。

## Provider 分层

新增独立 Provider 工厂，不要让 API、Service 或 UI 直接知道每个供应商的调用细节。

建议 provider id：

- `local_basic_hash`：当前 `BigramHashEmbeddingProvider`，兼容兜底，必须在 UI 中标注为“基础索引/兼容模式”，不要宣传为真实语义向量；
- `local_bge_small_zh`：后续本地离线轻量真实模型，推荐候选 `bge-small-zh-v1.5`；
- `local_bge_m3`：后续本地高质量模型，适合更强机器，体积和耗时更高；
- `dashscope_text_embedding_v4`：本轮优先实现的云端真实向量 provider；
- `openai_text_embedding_3_small` / `openai_text_embedding_3_large`：保留接口扩展，不要求本轮实现。

## 索引 Profile

新增项目级知识索引状态表，用于记录当前项目使用的向量配置。不要只依赖 embeddings 表里的 `model_name`，否则 UI 不知道当前项目应该用哪个 provider 生成 query vector。

建议新增模型：`backend/app/models/knowledge_index_profile.py`

建议字段：

- `id: str`
- `project_id: str`，唯一索引；
- `provider_id: str`，如 `dashscope_text_embedding_v4`；
- `provider_type: str`，如 `local` / `cloud` / `compat`；
- `display_name: str`，用户可见名称；
- `model_name: str`，真实模型名，如 `text-embedding-v4`；
- `vector_dim: int`
- `chunk_size: str`
- `status: str`，如 `ready` / `stale` / `error` / `not_configured`；
- `last_refreshed_at: datetime | None`
- `last_error: str | None`
- `created_at: datetime`
- `updated_at: datetime`

数据库初始化：

- 在 `backend/app/infrastructure/database.py` 的 `init_database()` 中导入新 model；
- 因为是新增表，`Base.metadata.create_all()` 可以创建；
- 如 Claude 发现现有数据库升级策略要求 `_ensure_*`，再新增 `_ensure_knowledge_index_profile_table()`，但不要改动无关表结构。

## 向量一致性规则

必须保证同一项目的活跃知识索引只使用一种 provider/model/dim 组合。

- 当用户选择新的 provider 并刷新“全部资料”时：
  - 删除该项目旧 embeddings；
  - 用新 provider 全量重建；
  - 更新 `KnowledgeIndexProfile`。
- 当用户只刷新“当前资料”时：
  - 如果请求 provider 与项目当前 profile 一致，允许刷新该资料；
  - 如果请求 provider 与项目当前 profile 不一致，后端返回 409，提示必须刷新全部资料，避免不同模型向量混用。
- 语义搜索、混合搜索必须使用项目当前 profile 对应的 provider 生成 query vector；
- `VectorStore.search()` 必须过滤当前 profile 的 `model_name` 和 `vector_dim`，避免不同维度向量混入 cosine 计算。

## 云端隐私与错误处理

云端精准模式必须是显式选择，不允许默认打开。

- API key 只从环境变量或后端本地配置读取，不在前端保存；
- 不要把 API key、请求正文、知识库片段写入日志；
- 前端选择云端模式时必须显示隐私提示：
  - “将把知识库片段发送到所选服务商用于生成向量”；
  - 用户必须勾选确认后才能开始；
- 云端请求失败时不要静默 fallback 到本地模式，否则用户会误以为已使用高精度索引；
- 需要区分未配置密钥、网络错误、限流、余额不足、模型不可用等错误，返回可理解的中文提示。

# Files to Create or Modify

Claude Code 需要新增或修改以下文件。Codex 不修改这些业务文件。

## Backend - Infrastructure

- 修改 `backend/app/infrastructure/embedding_provider.py`
  - 保留 `EmbeddingProvider` 协议；
  - 保留 `BigramHashEmbeddingProvider`，但将其定位为兼容 fallback；
  - 如需要，新增 provider metadata 数据结构。
- 新增 `backend/app/infrastructure/embedding_provider_factory.py`
  - 负责列出可用 provider；
  - 负责按 `provider_id` 创建 provider；
  - 负责检查 provider 是否可用、缺少什么配置。
- 新增 `backend/app/infrastructure/embedding_settings.py`
  - 从环境变量读取 embedding 配置；
  - 不读取或写入 `.env` 文件；
  - 不打印密钥。
- 新增 `backend/app/infrastructure/dashscope_embedding_provider.py`
  - 实现阿里云百炼 / DashScope 文本向量 provider；
  - 使用已有 `httpx` 直接调用 HTTP API；
  - 不新增阿里云 SDK 依赖，除非 Claude 确认 HTTP 调用无法满足。
- 可选新增 `backend/app/infrastructure/local_embedding_provider.py`
  - 本轮建议只做接口占位和清晰错误；
  - 不要自动下载模型；
  - 不要未经确认引入 `sentence-transformers` 或 `onnxruntime` 这类重依赖。

## Backend - Model / Repository / Schema

- 新增 `backend/app/models/knowledge_index_profile.py`
  - 保存项目当前知识索引 provider/profile 状态。
- 修改 `backend/app/infrastructure/database.py`
  - 在 `init_database()` 中导入 `knowledge_index_profile`；
  - 如需要，补充最小兼容建表逻辑。
- 新增 `backend/app/repositories/knowledge_index_profile_repo.py`
  - `get_by_project(project_id)`
  - `upsert_profile(...)`
  - `mark_error(project_id, error)`
  - `mark_stale(project_id)`
- 修改 `backend/app/schemas/knowledge_embedding.py`
  - 新增 provider/profile 相关请求与响应字段；
  - 扩展 `RefreshKnowledgeIndexRequest`；
  - 扩展 `IndexStatusResponse` 和 `RefreshKnowledgeIndexResponse`。

建议类型结构：

```python
EmbeddingProviderId = Literal[
    "local_basic_hash",
    "local_bge_small_zh",
    "local_bge_m3",
    "dashscope_text_embedding_v4",
]

class EmbeddingProviderOption(BaseModel):
    provider_id: str
    display_name: str
    provider_type: Literal["local", "cloud", "compat"]
    model_name: str
    vector_dim: int
    available: bool
    unavailable_reason: str | None = None
    requires_network: bool
    requires_privacy_confirmation: bool
    quality_label: str
    description: str

class RefreshKnowledgeIndexRequest(BaseModel):
    scope: KnowledgeRefreshScope = "project"
    source_id: str | None = None
    chunk_size: KnowledgeChunkSizeField = "medium"
    provider_id: str | None = None
    privacy_confirmed: bool = False
```

## Backend - Service / API

- 修改 `backend/app/services/knowledge_embedding_service.py`
  - 不再默认硬编码 `BigramHashEmbeddingProvider()`；
  - 接收 provider 或通过 factory/profile 获取 provider；
  - 写入 embeddings 时保留 `model_name`、`vector_dim`；
  - 当 provider 变更时配合 profile 进行全量重建。
- 修改 `backend/app/services/knowledge_index_refresh_service.py`
  - 接收 `provider_id`、`privacy_confirmed`；
  - 校验 cloud provider 是否已配置、是否已确认隐私；
  - 处理 source scope 下 provider 不一致时返回可识别错误；
  - 刷新成功后更新 `KnowledgeIndexProfile`。
- 修改 `backend/app/services/retrieval_service.py`
  - 语义搜索和混合搜索必须读取项目当前 profile；
  - query vector 必须使用当前 profile 对应 provider；
  - 如果 profile 缺失或索引未就绪，应返回可理解错误或降级到 keyword，并由 API 明确告知前端。
- 修改 `backend/app/infrastructure/vector_store.py`
  - `search()` 增加 `model_name`、`vector_dim` 过滤参数；
  - 查询 embeddings 时只使用当前 profile 对应向量；
  - 避免不同维度 vector 进入同一次 numpy 相似度计算。
- 修改 `backend/app/api/knowledge_embedding.py`
  - 扩展刷新索引接口；
  - 新增 provider options 接口：
    - `GET /api/projects/{project_id}/knowledge/embedding-providers`
  - 状态接口返回当前 profile、可用 provider、是否需要刷新。
- 修改 `backend/app/api/knowledge_retrieval.py`
  - 捕获 profile 缺失、provider 未配置、cloud 调用失败等错误；
  - 返回中文错误信息，不泄露密钥或原始资料片段。

## Frontend

- 修改 `frontend/src/entities/knowledge/types.ts`
  - 增加 provider option、profile、刷新请求字段类型。
- 修改 `frontend/src/entities/knowledge/api.ts`
  - 新增 `getKnowledgeEmbeddingProviders(projectId)`；
  - 扩展 `refreshKnowledgeIndex(projectId, payload)` payload。
- 修改 `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue`
  - 在现有“刷新知识索引”弹窗中增加“索引模式”选择；
  - 本地基础模式默认可用；
  - 云端精准模式仅在后端报告可用时可选；
  - 云端模式必须显示隐私确认复选框；
  - provider 变更且 scope 为当前资料时，提示需要刷新全部资料。
- 修改 `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`
  - 加载并展示当前索引状态；
  - 不要把 provider 技术名作为主要 UI 文案；
  - 可以在状态区显示“本地基础索引 / 云端精准索引 / 需刷新”等作者能理解的提示。

## Tests

- 新增 `backend/tests/test_embedding_provider_factory.py`
- 新增 `backend/tests/test_dashscope_embedding_provider.py`
  - 必须 mock `httpx`，不得真实联网。
- 新增 `backend/tests/test_knowledge_index_profile.py`
- 修改 `backend/tests/test_knowledge_embedding_service.py`
- 修改 `backend/tests/test_knowledge_index_refresh_service.py`
- 修改 `backend/tests/test_retrieval_service.py`
- 修改前端相关测试，如项目已有知识库组件测试则补充；没有则至少保证类型检查和构建通过。

# Implementation Steps for Claude Code

1. 执行前检查
   - 确认当前工作区 diff，避免覆盖用户或其他 agent 的改动。
   - 重新阅读本计划提到的后端和前端文件。
   - 不要修改本计划未列出的业务文件，除非实现中发现强依赖，并在 `CLAUDE_EXECUTION_REPORT.md` 中说明。

2. 后端新增 provider metadata 与配置读取
   - 在 `embedding_settings.py` 中读取：
     - `ZHANGSHU_EMBEDDING_PROVIDER`
     - `ZHANGSHU_DASHSCOPE_API_KEY`
     - `ZHANGSHU_DASHSCOPE_EMBEDDING_MODEL`
     - `ZHANGSHU_DASHSCOPE_EMBEDDING_DIM`
     - `ZHANGSHU_DASHSCOPE_BASE_URL`
     - `ZHANGSHU_LOCAL_EMBEDDING_MODEL_PATH`
   - 默认 provider 使用 `local_basic_hash`，确保离线可用。
   - 不写 `.env`，不提交任何密钥。

3. 后端实现 provider factory
   - `list_provider_options()` 返回前端所需选项；
   - `create_provider(provider_id)` 返回具体 provider；
   - 当 cloud provider 缺少 API key 时，`available = False`，并返回中文 `unavailable_reason`；
   - 当本地真实模型文件不存在时，`available = False`，不要自动下载。

4. 后端实现 DashScope provider
   - 使用 `httpx` 调用阿里云百炼 / DashScope embedding HTTP API；
   - `encode_batch()` 应优先批量请求，如 API 限制不允许，再内部拆批；
   - 空文本返回零向量或由上层跳过，但行为必须与测试一致；
   - 处理超时、401/403、429、余额不足、响应格式异常；
   - 日志中不得出现 API key、原始资料正文、完整请求 body。

5. 后端新增项目级索引 profile
   - 新增 model、repo；
   - 在数据库初始化导入新 model；
   - profile 以 `project_id` 唯一；
   - 刷新成功后 upsert；
   - 刷新失败时记录 `status = "error"` 和简短错误摘要。

6. 后端改造索引刷新链路
   - 扩展 `RefreshKnowledgeIndexRequest`，允许传 `provider_id` 和 `privacy_confirmed`；
   - cloud provider 且 `privacy_confirmed = False` 时返回 422；
   - provider 不可用时返回 400；
   - scope 为 `source` 且 provider 与当前 profile 不一致时返回 409，提示需要刷新全部资料；
   - scope 为 `project` 且 provider 变更时，删除旧项目 embeddings 并全量重建；
   - 返回 `provider_id`、`display_name`、`model_name`、`vector_dim`、`profile_status`。

7. 后端改造语义检索链路
   - `RetrievalService` 读取 `KnowledgeIndexProfile`；
   - query vector 使用 profile 指定 provider；
   - `VectorStore.search()` 增加 `model_name` 和 `vector_dim` 限定；
   - 如果 profile 缺失、索引未就绪或 provider 不可用：
     - keyword 模式照常可用；
     - semantic / hybrid 返回明确错误，或 hybrid 明确降级 keyword，并在响应中带 warning；
   - 不允许 silent fallback 导致用户误判检索质量。

8. 后端保留兼容行为
   - 旧测试显式传入 `BigramHashEmbeddingProvider()` 时仍应通过；
   - 未配置任何云端密钥时，原有知识库导入、刷新、本地基础检索仍可用；
   - 不要破坏知识库批量上传、刷新进度、问答、摘要已有入口。

9. 前端扩展类型和 API
   - 在 `types.ts` 添加 provider/profile 类型；
   - 在 `api.ts` 添加获取 provider options 的函数；
   - 扩展刷新 payload 和 response 类型；
   - 保持字段名与后端一致。

10. 前端改造刷新弹窗
    - 在“索引片段大小”附近增加“索引模式”区域；
    - 推荐 UI 文案：
      - `本地基础`：离线可用，不上传资料，检索质量较基础；
      - `本地高质量`：需要安装本地模型后可用，不上传资料；
      - `云端精准`：联网生成更准确索引，会发送资料片段到服务商；
    - cloud provider 未配置时禁用，并显示“需要在后端配置服务密钥”；
    - cloud provider 可用时，用户必须勾选隐私确认才能点击开始刷新；
    - 当选择的 provider 与当前索引不同且 scope 为当前资料时，自动切换或提示必须选择“全部资料”。

11. 前端状态展示
    - 在知识库页面索引状态区域显示：
      - 当前索引模式；
      - 模型显示名；
      - 是否需要刷新；
      - 最近刷新时间，如后端提供；
    - 不展示“重建分块”“生成向量”等偏技术按钮；
    - 继续把用户动作统一为“刷新知识索引”。

12. 测试实现
    - provider factory 测试：
      - 默认本地基础 provider 可用；
      - 未配置 API key 时 DashScope 不可用；
      - 配置 API key 后 DashScope 可创建。
    - DashScope provider 测试：
      - mock 成功响应；
      - mock 401/429/timeout；
      - 验证不会真实联网。
    - profile 测试：
      - 首次刷新创建 profile；
      - provider 变更时 project scope 允许；
      - provider 变更时 source scope 拒绝。
    - retrieval 测试：
      - semantic 使用 profile provider；
      - vector_store search 按 `model_name` / `vector_dim` 过滤；
      - 不同模型向量不会混算。
    - 前端测试或类型检查：
      - provider options 加载；
      - cloud 隐私确认按钮状态；
      - provider 不可用时禁用。

13. 执行报告
    - 完成后生成 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`；
    - 报告必须列出实际修改文件、验证命令结果、未完成项、风险和建议。

# Constraints

- 不要把 AI 调用写进 Vue 组件；
- 不要把 provider HTTP 调用写进 API/router 层；
- 不要把 provider 选择逻辑散落在多个 Service 中；
- 不要在 Repository 层写业务判断；
- 不要在 `backend/app/main.py` 写业务逻辑；
- 不要引入大型 UI 库；
- 不要为了接入本地模型自动下载模型文件；
- 不要未经用户明确确认引入 `sentence-transformers`、`onnxruntime`、`torch` 等重依赖；
- 不要提交 `.env`、API key、token、本地模型文件、数据库、日志；
- 不要把资料正文或云端请求 body 写入日志；
- 不要默认启用云端 provider；
- 不要在 cloud provider 失败时静默 fallback 到本地 provider；
- 不要让不同 provider/model/dim 的向量在同一项目活跃索引中混用；
- 不要把 DashVector / AnalyticDB 作为本阶段必需项；
- 继续保持 UI 文案为简体中文，代码标识符和 API 路径为英文。

# Verification Commands

Claude Code 完成后至少运行以下命令。

后端：

```powershell
cd backend
python -m pytest tests/test_embedding_provider.py
python -m pytest tests/test_embedding_provider_factory.py
python -m pytest tests/test_dashscope_embedding_provider.py
python -m pytest tests/test_knowledge_embedding_service.py
python -m pytest tests/test_knowledge_index_refresh_service.py
python -m pytest tests/test_retrieval_service.py
python -m pytest tests/test_vector_store.py
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

- 未配置云端密钥时，知识库仍能使用本地基础模式刷新索引；
- 未配置云端密钥时，云端精准模式不可选，并有明确提示；
- 配置云端密钥后，云端精准模式可选；
- 选择云端精准模式但未勾选隐私确认时，不能开始刷新；
- 切换 provider 时，当前资料范围不允许混用模型，应提示刷新全部资料；
- 刷新完成后，索引状态显示正确 provider/model；
- 语义检索和混合检索使用当前 profile 的 provider；
- 搜索、问答、摘要不出现明显回归；
- 控制台和日志中不出现 API key 或知识库正文。

# Acceptance Criteria

- `docs/ai-handoff/CODEX_PLAN.md` 已由 Codex 写入，本轮 Codex 未修改业务代码；
- Claude Code 实现后，知识库向量能力有清晰 provider 边界；
- 当前伪向量只作为本地基础/兼容 fallback，不再被误称为高质量语义向量；
- 阿里云百炼 / DashScope embedding provider 有独立基础设施模块和 mock 测试；
- 未配置云端密钥时，系统仍可离线使用；
- 云端模式必须显式选择并完成隐私确认；
- 项目级索引 profile 能记录当前 provider/model/vector_dim/chunk_size/status；
- 刷新索引和语义检索使用同一个 profile，不会出现索引向量和查询向量不一致；
- `VectorStore.search()` 不会混算不同模型或不同维度的向量；
- 前端只暴露“刷新知识索引”和“索引模式”等作者可理解概念；
- 不引入未经确认的重依赖；
- 不提交密钥、本地配置、模型文件、数据库、日志或临时文件；
- 后端 pytest、前端 type-check、前端 build 通过。

# Risks and Watchpoints

- 云端隐私风险：知识库片段可能包含未公开剧情、设定、人名和商业创意，必须显式确认；
- 云端成本风险：大批量资料刷新可能产生 API 调用费用；
- 云端稳定性风险：网络中断、限流、余额不足会导致刷新失败；
- 向量维度风险：不同模型维度不同，必须过滤并避免混算；
- 模型切换风险：切换 provider 后必须全量刷新，不能只刷新单条资料；
- 本地模型依赖风险：`sentence-transformers` / `torch` 依赖重，Windows 桌面安装成本高；
- 本地模型分发风险：模型文件体积大，不应自动下载或提交；
- 检索质量风险：中文网文资料包含专有名词，模型需要适合中文语义检索；
- 性能风险：SQLite JSON 向量 + numpy 暴力搜索适合当前阶段，但资料量大后需要独立 VectorStore；
- API 兼容风险：阿里云 DashScope 响应格式、模型名或维度可能随版本变化，provider 要集中封装；
- UI 认知风险：不要把“embedding”“向量”“分块”等术语直接暴露给普通作者。

# Review Checklist

Codex 复审 Claude Code 执行结果时重点检查：

- 是否读取并遵循本计划；
- 是否只修改了本计划列出的相关文件；
- 是否存在 UI、业务逻辑、数据访问、AI 调用混杂；
- provider HTTP 调用是否只在 infrastructure 层；
- API/router 是否只做参数校验、依赖注入和错误映射；
- Service 是否负责业务编排，而不是直接拼接复杂 SQL；
- Repository 是否只处理 profile 持久化；
- 语义搜索是否使用项目当前 profile 的 provider；
- `VectorStore.search()` 是否过滤 `model_name` 和 `vector_dim`；
- provider 变更时 source scope 是否被拒绝或引导全量刷新；
- cloud provider 是否需要隐私确认；
- cloud provider 是否不会记录 API key 或资料正文；
- DashScope 测试是否 mock 网络；
- 未配置密钥时是否仍可本地离线使用；
- 是否引入了未经说明的新依赖；
- 是否提交了 `.env`、密钥、本地模型、数据库、日志、临时文件；
- 前端文案是否面向作者，而不是暴露底层技术；
- 后端和前端验证命令是否通过；
- 最终建议应根据结果判断为 Accept、Minor Revision 或 Rework。
