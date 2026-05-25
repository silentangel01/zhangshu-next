<!-- Archived after Claude execution before next-feature discussion on 2026-05-24. -->

# Task Summary

本计划用于优化知识库语义检索质量。当前已接入阿里 DashScope embedding 后，仍出现“向量匹配不精准、似乎把所有匹配都列出来”的问题。判断如下：

- 是的，必须把匹配度纳入考量；
- 不能只按 `top_k` 返回向量相似度最高的前 N 条；
- 需要先召回候选，再进行相似度阈值过滤、简单规则判断、结果重排和数量控制；
- 对问答、摘要使用的检索结果也要应用同一套质量过滤，否则低相关片段会进入 RAG 上下文。

本轮目标是新增“检索质量层”，不更换 embedding 模型，不新增重依赖，不改知识库资料存储结构。

同时需要把知识库问答/摘要中的“AI 模型尚未接入，当前使用 stub 模式”纳入本计划。建议让 Claude Code 评估并实现与向量 API Key 类似的配置方式：通过应用设置 UI 输入、加密存储到本地 SQLite，并由后端 LLM provider 读取配置。注意：embedding provider 和 LLM provider 是两个独立能力，不应混在同一个模块里。

Codex 未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

已阅读 Claude Code 最新执行报告：

- 最新报告任务是“API Key 设置 UI — 加密存储 + 应用设置弹窗”；
- 报告显示 DashScope API Key 已支持 env → DB 回退链；
- 该报告不是当前检索质量问题的实现报告，但会影响 DashScope provider 可用性；
- 活跃交接文件已归档到：

`docs/ai-handoff/archive/2026-05-24-app-config-vector-review-mixed/`

当前检索相关代码发现如下：

- `backend/app/infrastructure/vector_store.py`
  - `SqliteVectorStore.search()` 当前计算 cosine similarity 后直接 `np.argsort(similarities)[::-1][:top_k]`；
  - 没有 `min_score` 阈值；
  - 没有过滤低相关结果；
  - 只要存在向量，就会返回“最相似的前 N 个”，即使最低分已经不相关。
- `backend/app/services/retrieval_service.py`
  - semantic 模式调用 `VectorStore.search(..., top_k=limit)`；
  - 默认 `limit=50`；
  - semantic 结果只使用向量分数，没有规则过滤、关键词锚点判断或二次重排；
  - hybrid 模式是 keyword 结果优先，再追加 semantic 结果；没有统一评分，也没有去除低相关 semantic 结果。
- `backend/app/services/knowledge_retrieval_service.py`
  - keyword 模式只按 `ILIKE` 命中，排序为资料更新时间和 chunk_index；
  - 没有给 keyword 结果生成可比较的 relevance score。
- `backend/app/schemas/knowledge_retrieval.py`
  - `KnowledgeRetrievalChunkResult` 只有 `relevance_score`，没有 `vector_score`、`keyword_score`、`final_score`、`match_quality`、`match_reason`；
  - `KnowledgeRetrievalResponse` 只有 `total` 和 `results`，没有候选数、过滤数、阈值或 warnings。
- `backend/app/api/knowledge_retrieval.py`
  - 搜索 API 暴露 `limit`，最大到 200；
  - 没有 `min_score`、`strictness` 或用户可理解的“匹配范围”参数。
- `backend/app/services/rag_service.py`
  - 问答默认 `top_k=10`，直接使用 retrieval 结果；
  - 如果 retrieval 给了低相关结果，这些片段会进入上下文。
- `backend/app/infrastructure/llm_provider.py`
  - 当前只有 `LLMProvider` 协议和 `StubLLMProvider`；
  - `StubLLMProvider.generate()` 会返回“AI 模型尚未接入”的提示；
  - `StubLLMProvider.summarize()` 同样只返回模板化摘要；
  - 说明知识库问答和摘要目前没有真实 LLM 调用。
- `backend/app/services/app_config_service.py`
  - 当前已支持敏感配置加密存储；
  - 但敏感 key 目前只覆盖 DashScope API Key；
  - 可以复用为 LLM API Key / 模型配置的存储基础。
- `backend/app/api/app_config.py`
  - 当前只有 DashScope embedding 测试连接；
  - `GET /api/app-config` 和 `PUT /api/app-config` 目前只处理 `dashscope_api_key`。
- `backend/app/services/ai_summary_service.py`
  - 指定 topic 时使用 retrieval 搜索，`limit=20`；
  - 同样会受低相关结果影响。
- `frontend/src/features/knowledge/KnowledgeSearchPanel.vue`
  - 语义/混合模式会显示 `relevance_score` 百分比；
  - 但前端没有匹配质量提示；
  - 默认没有控制“精准/均衡/宽泛”的入口；
  - 搜索结果摘要写“找到 N 个匹配结果”，容易让用户误以为所有返回结果都相关。
- `frontend/src/features/knowledge/KnowledgeAskPanel.vue`
  - 用户可选引用数量 5/10/20；
  - 没有相关度门槛；
  - 低相关片段可能进入引用列表。
- `frontend/src/features/knowledge/KnowledgeSummaryPanel.vue`
  - 摘要不展示检索质量，也没有提示“相关资料不足”。
- `frontend/src/features/app-config/AppSettingsDialog.vue`
  - 当前只提供 DashScope API Key 输入、保存和测试连接；
  - UI 文案明确写着“用于知识索引的云端向量模型服务”；
  - 还没有问答/摘要 LLM 模型的配置入口。

# Architecture Decision

## 总体方案

新增一个独立的检索质量判断层，建议命名：

`backend/app/services/retrieval_quality_service.py`

该层位于 Service 层，负责对候选片段做：

1. 向量相似度阈值过滤；
2. 简单规则判断；
3. 关键词/标题/标签等锚点加分；
4. 低质量结果剔除；
5. 结果重排；
6. 输出面向前端和 RAG 的匹配质量信息。

不要把这些逻辑写入：

- Vue 组件；
- API/router；
- Repository；
- `VectorStore` 之外的大段 SQL；
- DashScope provider。

## 检索链路调整

建议链路：

1. Candidate Retrieval
   - semantic 模式：向量库先召回较多候选，例如 `candidate_limit = min(max(limit * 4, 40), 120)`；
   - keyword 模式：关键词搜索也生成候选；
   - hybrid 模式：keyword + semantic 分别召回，再统一进入质量层。

2. Quality Evaluation
   - 对每个候选计算：
     - `vector_score`
     - `keyword_score`
     - `rule_score`
     - `final_score`
     - `match_quality`: `high` / `medium` / `low`
     - `match_reason`: 中文简短原因，例如“标题命中”“正文包含关键设定词”“语义相似度较高”。

3. Filtering
   - 低于阈值的结果不返回；
   - 没有任何关键词锚点且向量分数偏低的结果不返回；
   - 空片段、过短片段、重复片段应剔除；
   - RAG/问答默认只允许 high/medium 质量进入上下文。

4. Ranking
   - semantic 模式按 `final_score` 排序；
   - hybrid 模式不要再简单“keyword 优先”；应使用统一评分或 Reciprocal Rank Fusion；
   - 结果数量最终限制为用户请求的 `limit`。

## 默认匹配策略

不要直接把原始阈值暴露给普通作者。前端建议使用“匹配范围”：

- `精准`：只返回高度相关片段，适合问答和摘要；
- `均衡`：默认值，兼顾召回和相关性；
- `宽泛`：用于资料探索，允许更多弱相关结果。

后端可以用 `strictness` 表示：

- `strict`
- `balanced`
- `broad`

建议默认：

- 知识库检索：`balanced`
- 问答：`strict`
- 摘要指定 topic：`balanced`

阈值应集中放在 `RetrievalQualityPolicy`，不要散落在代码里。初始阈值可以保守设定，执行后通过测试数据再校准。

建议初始规则：

- `strict`: semantic 最低 `final_score >= 0.62`
- `balanced`: semantic 最低 `final_score >= 0.48`
- `broad`: semantic 最低 `final_score >= 0.35`

注意：这是最终综合分，不一定等于 cosine score。DashScope embedding 的 cosine 分布需要真实数据校准，阈值应可集中调整。

## 简单规则判断

本轮不引入 jieba、BM25、LLM rerank 或新数据库索引。先做轻量规则：

- 标准化 query 和 chunk：
  - 去首尾空格；
  - 中文标点归一；
  - 英文转小写；
  - 连续空白合并。
- 提取 query anchors：
  - 连续中文词组；
  - 英文/数字 token；
  - 长度大于等于 2 的关键片段；
  - 去掉常见泛词，例如“什么”“如何”“介绍”“设定”“资料”“内容”。
- 规则分：
  - 标题命中 query anchor：强加分；
  - chunk heading 命中：加分；
  - 正文命中：加分；
  - source title / tag 命中：小幅加分；
  - 高可信资料可小幅加分，但不得替代相关性；
  - 内容过短、空内容、重复内容：降权或剔除。
- 拒绝规则：
  - `vector_score` 低于硬下限且没有任何 anchor 命中；
  - query 中有明确专名/术语，但 chunk 没有任何 anchor 命中，且 vector_score 不高；
  - chunk 内容长度过短，无法作为有效回答上下文。

## 用户体验原则

- 不在 UI 中暴露“embedding”“cosine”“阈值”等底层术语；
- 搜索结果展示“相关度：高 / 中 / 低”比单纯百分比更容易理解；
- 可在二级信息中显示百分比；
- 当过滤掉低相关结果时，显示提示：
  - “已隐藏低相关片段，可切换为宽泛匹配查看更多。”
- 问答如果没有足够相关资料，应提示：
  - “没有找到足够相关的知识库片段，建议补充资料或切换为宽泛匹配。”

## 问答/摘要真实 LLM 接入策略

知识库问答有两个独立阶段：

1. 检索：从知识库找相关片段；
2. 回答：把相关片段交给 LLM 生成回答。

本计划前半部分解决检索质量问题；后半部分需要规划真实 LLM 接入。建议如下：

- 新增独立 `LLMProviderFactory`，不要让 `RagService` 固定使用 `StubLLMProvider`；
- `StubLLMProvider` 保留为离线/未配置兜底；
- 优先支持 DashScope OpenAI-compatible chat/completions 作为云端问答模型；
- 不要默认启用云端 LLM，必须由用户在设置中显式配置并开启；
- LLM API Key 可先复用现有 `dashscope_api_key`，但 UI 上要说明“同一个 DashScope Key 可同时用于云端索引和 AI 问答”；
- 如果后续需要区分 embedding key 和 chat key，应在 app_config 中使用独立 key，例如 `dashscope_llm_api_key`；
- 模型名、base_url、是否启用云端问答应作为配置项，不要硬编码在 `RagService` 中；
- 所有 LLM 请求都不得写入日志，尤其是知识库上下文、用户问题、API key。

推荐第一阶段配置项：

- `llm_provider`: `stub` / `dashscope`
- `enable_cloud_llm`: boolean
- `dashscope_llm_model`: 默认由后端配置，允许用户在设置中调整
- `dashscope_llm_base_url`: 默认走 DashScope OpenAI-compatible base URL
- `dashscope_api_key`: 先复用现有加密字段

前端设置建议：

- 在“应用设置”中拆分两个区块：
  - “云端向量索引”：用于知识索引；
  - “AI 问答模型”：用于问答和摘要；
- 如果使用同一个 DashScope Key，UI 应明确说明；
- 增加“测试 AI 问答模型”按钮，发送极短测试请求，不携带用户知识库内容；
- 未配置或未启用时，问答面板继续显示 stub 提示，但要附带“前往应用设置配置 AI 模型”的行动入口。

# Files to Create or Modify

Claude Code 需要新增或修改以下文件。Codex 不修改这些业务文件。

## Backend

- 新增 `backend/app/services/retrieval_quality_service.py`
  - 定义 `RetrievalStrictness`
  - 定义 `RetrievalQualityPolicy`
  - 定义 `RetrievalCandidate`
  - 定义 `RetrievalQualityResult`
  - 实现 query anchor 提取、规则打分、综合分、过滤和重排。
- 修改 `backend/app/infrastructure/vector_store.py`
  - 可选：为 `search()` 增加 `min_score` 参数；
  - 或保持 vector store 只负责候选召回，把阈值过滤放在 quality service；
  - 推荐先保持 vector store 简洁，仅增加返回候选上限，不做复杂规则。
- 修改 `backend/app/services/retrieval_service.py`
  - semantic 模式改为“召回候选 → 加载 chunk/source → quality service 过滤重排 → 返回”；
  - hybrid 模式改为 keyword 与 semantic 候选统一进入质量层；
  - 不再直接返回 `top_k` 向量结果。
- 修改 `backend/app/services/knowledge_retrieval_service.py`
  - keyword 结果需要产生基础 `keyword_score`；
  - 或新增内部方法返回 keyword candidates，供 `RetrievalService` 统一重排。
- 修改 `backend/app/schemas/knowledge_retrieval.py`
  - 扩展 request/response 字段：
    - `strictness`
    - `min_score`
    - `candidate_count`
    - `filtered_count`
    - `warnings`
    - result 内增加 `vector_score`、`keyword_score`、`final_score`、`match_quality`、`match_reason`。
- 修改 `backend/app/api/knowledge_retrieval.py`
  - 增加 query 参数：
    - `strictness: strict | balanced | broad`
    - 可选 `min_score`，仅作为高级参数，默认不由 UI 直接暴露。
- 修改 `backend/app/services/rag_service.py`
  - 默认使用 `strictness="strict"`；
  - 没有 high/medium 质量片段时，返回无足够资料提示，不要把低相关上下文交给 LLM。
- 修改 `backend/app/services/ai_summary_service.py`
  - topic 搜索使用 `strictness="balanced"`；
  - 如果 topic 搜索结果不足，返回提示或 warnings。
- 修改 `backend/app/schemas/rag.py`
  - 问答 request 可增加 `strictness`；
  - response 可增加 `warnings` 或 `retrieval_warning`。
- 修改 `backend/app/infrastructure/llm_provider.py`
  - 保留 `LLMProvider` 协议和 `StubLLMProvider`；
  - 新增真实 provider 所需的 message/context 调用边界；
  - 或保持协议不变，将真实 provider 适配到现有 `generate()` / `summarize()`。
- 新增 `backend/app/infrastructure/llm_provider_factory.py`
  - 根据 app config 创建 `StubLLMProvider` 或 DashScope LLM provider；
  - 负责判断云端 LLM 是否启用、配置是否完整。
- 新增 `backend/app/infrastructure/dashscope_llm_provider.py`
  - 通过 HTTP 调用 DashScope OpenAI-compatible chat/completions；
  - 不在日志中输出 prompt、context、response 全文或 key。
- 修改 `backend/app/services/app_config_service.py`
  - 增加 well-known config keys：
    - `llm_provider`
    - `enable_cloud_llm`
    - `dashscope_llm_model`
    - `dashscope_llm_base_url`
  - 如果决定使用独立 LLM Key，则增加 `dashscope_llm_api_key` 并加入敏感 key。
- 修改 `backend/app/infrastructure/config_crypto.py`
  - 如果新增独立 `dashscope_llm_api_key`，必须加入敏感 key 集合。
- 修改 `backend/app/schemas/app_config.py`
  - 扩展配置读写 schema；
  - 增加测试 AI 问答模型 request/response。
- 修改 `backend/app/api/app_config.py`
  - 扩展 GET/PUT app-config；
  - 新增 `POST /api/app-config/test-dashscope-llm`。

## Frontend

- 修改 `frontend/src/entities/knowledge/types.ts`
  - 增加 `KnowledgeRetrievalStrictness`
  - 增加结果字段 `vector_score`、`keyword_score`、`final_score`、`match_quality`、`match_reason`
  - 增加 response 字段 `candidate_count`、`filtered_count`、`warnings`。
- 修改 `frontend/src/entities/knowledge/api.ts`
  - `searchKnowledgeChunks()` 支持传 `strictness`；
  - `askKnowledgeBase()` 支持传 `strictness`。
- 修改 `frontend/src/features/knowledge/KnowledgeSearchPanel.vue`
  - 增加“匹配范围”：精准 / 均衡 / 宽泛；
  - 默认均衡；
  - 结果展示“相关度：高 / 中 / 低”；
  - 如果 response 有 filtered_count，展示“已隐藏 X 个低相关片段”。
- 修改 `frontend/src/features/knowledge/KnowledgeAskPanel.vue`
  - 增加“引用匹配范围”，默认精准；
  - 引用列表展示 match_quality；
  - 当后端 warnings 提示资料不足时展示中文提示。
- 修改 `frontend/src/features/knowledge/KnowledgeSummaryPanel.vue`
  - 可选增加匹配范围，默认均衡；
  - 展示相关资料不足提示。
- 修改 `frontend/src/entities/app-config/types.ts`
  - 增加 LLM provider、模型名、是否启用云端问答、测试结果类型。
- 修改 `frontend/src/entities/app-config/api.ts`
  - 增加 `testDashScopeLlmConnection()`。
- 修改 `frontend/src/features/app-config/AppSettingsDialog.vue`
  - 增加“AI 问答模型”设置区块；
  - 支持选择 stub / DashScope；
  - 支持填写或复用 DashScope Key；
  - 支持配置模型名；
  - 支持测试连接；
  - 保存敏感值后仍只展示 masked preview。

## Tests

- 新增 `backend/tests/test_retrieval_quality_service.py`
- 修改 `backend/tests/test_retrieval_service.py`
- 修改 `backend/tests/test_knowledge_retrieval.py`
- 修改 `backend/tests/test_rag_service.py`
- 修改 `backend/tests/test_ai_summary_service.py`
- 新增 `backend/tests/test_llm_provider_factory.py`
- 新增 `backend/tests/test_dashscope_llm_provider.py`
- 修改 `backend/tests/test_app_config.py` 或新增 app config 相关测试
- 修改前端知识库相关测试，如现有测试框架允许。

# Implementation Steps for Claude Code

1. 执行前检查
   - 读取当前 `git diff`，确认不要覆盖用户或其他 agent 的变更；
   - 特别注意当前工作区可能包含多个前序任务残留变更；
   - 本轮只围绕检索质量优化修改文件。

2. 新增检索质量服务
   - 创建 `backend/app/services/retrieval_quality_service.py`；
   - 定义：

```python
RetrievalStrictness = Literal["strict", "balanced", "broad"]
MatchQuality = Literal["high", "medium", "low"]
```

   - 实现 `evaluate_candidates(query, candidates, strictness, limit, min_score=None)`；
   - 输出排序后的 accepted results、candidate_count、filtered_count、warnings。

3. 设计候选结构
   - candidate 至少包含：
     - `chunk_id`
     - `source_id`
     - `chunk_heading`
     - `chunk_content`
     - `source_title`
     - `source_type`
     - `source_credibility`
     - `source_tags`
     - `vector_score`
     - `keyword_score`
   - 不要在 quality service 内直接查数据库；数据库查询仍由 retrieval service 完成。

4. 实现 query anchor 提取
   - 不引入新依赖；
   - 使用正则提取中文连续片段、英文数字 token；
   - 过滤泛词；
   - 对短 query 保留完整 query 作为 anchor。

5. 实现打分与过滤
   - `vector_score` 来自 embedding cosine；
   - `keyword_score` 根据 title/heading/content/tag 是否命中 anchor；
   - `rule_score` 用于标题命中、正文命中、可信度、过短内容等；
   - `final_score` 由三者加权，例如：
     - semantic: `0.78 * vector_score + 0.17 * keyword_score + 0.05 * rule_score`
     - hybrid: `0.55 * vector_score + 0.35 * keyword_score + 0.10 * rule_score`
   - 具体权重集中在 policy，不要散落。

6. 修改 semantic 检索
   - 在 `RetrievalService._search_semantic()` 中：
     - 先用 vector store 召回 `candidate_limit`；
     - 加载完整 chunk/source；
     - 调用 quality service；
     - 只返回 accepted results；
     - `matched_snippet` 优先围绕命中的 anchor，否则取 chunk 开头。

7. 修改 hybrid 检索
   - 不再简单 keyword 优先；
   - keyword 候选和 semantic 候选合并后去重；
   - 同一 chunk 同时被 keyword 和 semantic 命中时合并分数；
   - 调用 quality service 统一排序。

8. 修改 response schema
   - `KnowledgeRetrievalChunkResult` 增加：
     - `vector_score: float | None`
     - `keyword_score: float | None`
     - `final_score: float | None`
     - `match_quality: str | None`
     - `match_reason: str | None`
   - `KnowledgeRetrievalResponse` 增加：
     - `candidate_count: int`
     - `filtered_count: int`
     - `warnings: list[str]`
   - 保持旧字段兼容，避免前端已有展示崩溃。

9. 修改 API
   - `GET /api/projects/{project_id}/knowledge/search` 增加：
     - `strictness=balanced`
     - `min_score: float | None = None`
   - 限制 `min_score` 范围 `0.0 <= min_score <= 1.0`；
   - `limit` 默认建议从 50 调整为 20，最大仍可保留 200，但前端不默认请求大值。

10. 修改 RAG 问答
    - `RagService.ask()` 调 retrieval 时传 `strictness="strict"`；
    - 如果 accepted results 为空：
      - 返回空 citations；
      - answer 使用固定提示：“没有找到足够相关的知识库片段，建议补充资料或切换匹配范围。”；
      - 不把低相关内容交给 LLM provider。

11. 修改摘要
    - `AISummaryService._gather_from_search()` 调 retrieval 时传 `strictness="balanced"`；
    - 如果 topic 有值但结果为空，返回空 summary 或明确 warning；
    - 不要为了凑数量使用低相关片段。

12. 修改前端检索 UI
    - 在检索面板增加“匹配范围”分段控件：
      - 精准；
      - 均衡；
      - 宽泛。
    - 默认 `balanced`；
    - 显示结果时用 `match_quality` 生成中文标签：
      - high: 高相关；
      - medium: 中相关；
      - low: 弱相关。
    - 如果 `filtered_count > 0`，显示“已隐藏 X 个低相关片段”。

13. 修改问答/摘要 UI
    - 问答默认精准；
    - 引用结果展示相关度标签；
    - warnings 用提示条展示；
    - 摘要若 topic 检索不足，提示用户换关键词或切换匹配范围。

14. 规划并接入真实 LLM provider
    - 新增 `dashscope_llm_provider.py`，通过 DashScope OpenAI-compatible chat/completions 生成回答；
    - 新增 `llm_provider_factory.py`；
    - `RagService` 和 `AISummaryService` 不再直接固定 `StubLLMProvider()`，改为通过 factory 获取 provider；
    - 如果用户未启用云端 LLM 或配置不完整，继续使用 stub；
    - 如果启用云端 LLM，但测试/调用失败，返回中文错误，不静默降级为 stub；
    - 所有真实 LLM 请求必须只在后端发生。

15. 扩展应用设置
    - 在 `app_config` schema/API/service 中增加 LLM 配置；
    - 优先复用现有 `dashscope_api_key`，避免用户重复输入；
    - 如果实现独立 LLM Key，必须加入敏感 key 集合并加密存储；
    - 增加“测试 AI 问答模型”接口，测试 prompt 必须是短文本，不携带知识库内容；
    - 前端 `AppSettingsDialog.vue` 增加“AI 问答模型”区块。

16. 修改问答面板提示
    - 未启用真实 LLM 时，问答面板应清楚提示“当前为本地占位回答”；
    - 提供“前往应用设置配置 AI 模型”的入口或说明；
    - 启用真实 LLM 后，回答区域不再显示 stub 提示；
    - 保留“AI 回答仅供参考，不会自动修改任何内容”。

17. 补充测试
    - `test_retrieval_quality_service.py` 覆盖：
      - 高 vector_score 通过；
      - 低 vector_score 且无 anchor 被过滤；
      - 标题命中会加分；
      - strict/balanced/broad 返回数量不同；
      - 重复 chunk 去重。
    - `test_retrieval_service.py` 覆盖：
      - semantic 不再返回所有低相关结果；
      - hybrid 合并 keyword 和 semantic 分数；
      - response 包含 candidate_count / filtered_count / match_quality。
    - `test_rag_service.py` 覆盖：
      - 低相关检索为空时不构造引用；
      - 返回用户可理解提示。
      - 未配置真实 LLM 时使用 stub；
      - 启用真实 LLM 时调用 factory 返回的 provider。
    - `test_dashscope_llm_provider.py` 必须 mock HTTP，不得真实联网。
    - app config 测试覆盖 LLM 配置加密、masked 返回、删除配置。
    - 前端测试或 type-check 覆盖新字段。

18. 生成执行报告
    - 完成后写 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`；
    - 报告需要说明阈值取值、规则逻辑、测试结果、真实 LLM 配置方式、仍需真实数据校准的部分。

# Constraints

- 不要修改 embedding provider 的模型调用逻辑；
- 不要为了本轮优化引入 jieba、BM25、Elasticsearch、向量数据库或 LLM reranker；
- 不要把规则判断写进 Vue 组件；
- 不要在 API 层写复杂检索逻辑；
- 不要让 Repository 负责打分；
- 不要把用户资料正文写入日志；
- 不要默认返回大量弱相关片段；
- 不要让 RAG 问答为了凑引用数量使用低相关片段；
- 不要在未启用云端 LLM 时自动调用真实模型；
- 不要把 LLM API Key、prompt、知识库上下文、模型响应全文写入日志；
- 不要把 LLM 调用写进前端；
- 不要把 LLM provider 和 embedding provider 混成一个类；
- 不要直接删除现有 keyword / semantic / hybrid 模式；
- 保持中文 UI 文案；
- 保持旧 API 字段兼容，新增字段应为可选或有默认值。

# Verification Commands

后端：

```powershell
cd backend
python -m pytest tests/test_retrieval_quality_service.py
python -m pytest tests/test_retrieval_service.py
python -m pytest tests/test_knowledge_retrieval.py
python -m pytest tests/test_rag_service.py
python -m pytest tests/test_ai_summary_service.py
python -m pytest tests/test_llm_provider_factory.py
python -m pytest tests/test_dashscope_llm_provider.py
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

- 使用语义检索搜索一个明确专名，只返回真正相关片段；
- 搜索一个模糊问题，精准模式结果少，宽泛模式结果更多；
- 低相关片段不再显示为普通匹配结果；
- 搜索结果显示“高相关 / 中相关 / 弱相关”；
- 问答没有足够相关片段时不会硬凑引用；
- 未启用真实 AI 模型时，问答仍显示 stub/占位提示；
- 在应用设置中配置并启用 DashScope LLM 后，问答不再使用 stub；
- 测试 AI 问答模型不会携带知识库内容；
- 摘要指定主题时不会使用明显不相关片段；
- DashScope 云端 provider 与本地基础 provider 都能走同一质量层；
- 控制台和后端日志不出现知识库正文或 API key。

# Acceptance Criteria

- 语义检索不再仅凭 `top_k` 返回前 N 个向量结果；
- 检索链路有统一的质量判断层；
- semantic / hybrid / RAG / summary 均使用同一套质量过滤策略；
- 返回结果包含可解释的相关度信息；
- 前端提供“匹配范围”而不是暴露底层阈值；
- 默认检索结果数量和质量更符合作者预期；
- 低相关结果会被过滤，并在 UI 中提示已隐藏；
- RAG 问答在未配置真实 LLM 时继续 stub，但能引导用户配置；
- 真实 LLM API Key 通过加密 app_config 存储或复用已有 DashScope Key；
- App 设置中能区分“云端向量索引”和“AI 问答模型”；
- 不新增重依赖；
- 后端 pytest、前端 type-check、前端 build 通过；
- Claude Code 生成执行报告。

# Risks and Watchpoints

- DashScope embedding 的 cosine 分布需要真实资料校准，初始阈值可能过严或过松；
- 本地基础 hash provider 的分数不是真实语义分，不能套用和云端相同阈值；
- 规则过滤过严可能漏掉隐喻、别名和跨语言表达；
- 规则过滤过松会继续返回弱相关结果；
- hybrid 模式如果权重设计不好，可能让关键词命中压过语义相关；
- RAG 如果过滤过严，可能经常提示资料不足；
- 不要把“低相关”完全等同于“错误”，宽泛模式仍应允许用户探索；
- 后续如要进一步提升质量，可再规划 BM25、中文分词、cross-encoder rerank 或 LLM rerank，但不是本轮范围。
- 真实 LLM 接入后会把检索到的知识库片段发送给云端模型，必须有清晰启用开关和隐私提示；
- 复用同一个 DashScope API Key 体验更简单，但长期可能需要区分 embedding 与 chat 的模型、额度和权限；
- DashScope chat/completions 的响应格式需要 mock 测试和真实 Key 手动验证；
- StubLLMProvider 必须保留，保证离线状态和未配置状态仍可用。

# Review Checklist

Codex 复审 Claude Code 执行结果时重点检查：

- 是否新增了独立 `retrieval_quality_service.py`；
- 是否避免把规则打分写进 UI/API/Repository；
- `VectorStore.search()` 是否仍保持基础召回职责；
- semantic 是否先召回候选再过滤重排；
- hybrid 是否不再简单 keyword 优先；
- 是否有 `strictness` 或等价匹配范围；
- 是否有相似度阈值和低相关过滤；
- 是否有规则判断：标题、heading、正文、tag、专名 anchor；
- response 是否包含 `candidate_count`、`filtered_count`、`match_quality`、`match_reason`；
- RAG 是否避免使用低相关片段凑上下文；
- `RagService` / `AISummaryService` 是否通过 LLM provider factory 获取模型；
- 未配置真实 LLM 时是否保留 stub；
- 启用真实 LLM 是否需要用户明确配置；
- LLM API Key 是否加密存储或安全复用；
- 是否没有记录 prompt/context/key；
- 前端是否用作者能理解的“精准/均衡/宽泛”“高相关/中相关/弱相关”；
- 前端是否清楚区分“云端向量索引”和“AI 问答模型”；
- 是否未新增重依赖；
- 是否未提交密钥、本地数据库、日志或模型文件；
- 测试和构建是否通过；
- 最终建议应根据结果判断为 Accept、Minor Revision 或 Rework。
