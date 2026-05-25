---
date: 2026-05-24
task: Knowledge Base Module Phase K5 - RAG / AI Summary
codex_plan: docs/ai-handoff/CODEX_PLAN.md (Phase K5 section in plan file)
---

## Task Summary

实现知识库模块 Phase K5：RAG 问答与 AI 总结功能。建立 LLM provider 抽象层，实现 RAG 服务（检索 + 生成回答 + 引用）和 AI 摘要服务（收集 chunk + 生成草稿摘要），前端新增问答面板和摘要面板。当前使用 StubLLMProvider 返回模板化回答，所有 AI 输出标注为草稿/建议，不自动修改任何业务数据。

## Files Changed

### 后端新增（8 个文件）

- 新增：`backend/app/infrastructure/llm_provider.py` — LLMProvider Protocol + StubLLMProvider（模板化回答，标注 "[AI 模型尚未接入]"）
- 新增：`backend/app/schemas/rag.py` — KnowledgeAskRequest/Response、RagCitation、KnowledgeSummaryRequest/Response
- 新增：`backend/app/services/rag_service.py` — RAG 服务：检索相关 chunk → 组装上下文 → 调用 LLM → 返回带引用的回答
- 新增：`backend/app/services/ai_summary_service.py` — AI 摘要服务：收集 chunk（按 source_ids/topic/全部） → 调用 LLM → 返回草稿摘要
- 新增：`backend/app/api/rag.py` — POST `/api/projects/{pid}/knowledge/ask` + POST `/api/projects/{pid}/knowledge/summary`
- 新增：`backend/tests/test_llm_provider.py` — 7 个测试
- 新增：`backend/tests/test_rag_service.py` — 11 个测试
- 新增：`backend/tests/test_ai_summary_service.py` — 9 个测试

### 后端修改（1 个文件）

- 修改：`backend/app/main.py` — 注册 rag_router

### 前端新增（2 个文件）

- 新增：`frontend/src/features/knowledge/KnowledgeAskPanel.vue` — 问答面板：问题输入 + 检索模式切换 + AI 回答显示 + 引用列表
- 新增：`frontend/src/features/knowledge/KnowledgeSummaryPanel.vue` — 摘要面板：主题输入 + 草稿摘要显示 + 引用资料列表

### 前端修改（3 个文件）

- 修改：`frontend/src/entities/knowledge/types.ts` — 新增 KnowledgeAskRequest、RagCitation、KnowledgeAskResponse、KnowledgeSummaryRequest、KnowledgeSummaryResponse 类型
- 修改：`frontend/src/entities/knowledge/api.ts` — 新增 askKnowledgeBase() 和 summarizeKnowledge() API 函数
- 修改：`frontend/src/pages/knowledge/ProjectKnowledgePage.vue` — viewMode 扩展为 'browse'|'search'|'ask'|'summary'，工具栏新增"问答"和"摘要"按钮，条件渲染新面板

## Implementation Notes

1. **LLM Provider 设计**：`LLMProvider` 使用 `@runtime_checkable Protocol`，定义 `generate(prompt, context)` 和 `summarize(texts, instruction)` 两个核心方法。`StubLLMProvider` 返回包含 "[AI 模型尚未接入]" 标记的模板文本，展示检索到的上下文前 500 字符（generate）或每段文本前 100 字符（summarize）。
2. **RAG 服务流程**：验证项目存在 → 空问题返回空结果 → 通过 RetrievalService 检索 → 组装上下文 → 调用 LLM → 构建 RagCitation 列表 → 返回 KnowledgeAskResponse。
3. **AI 摘要服务流程**：验证项目存在 → 按 source_ids/topic/全部收集 chunk → 调用 LLM summarize → 返回 KnowledgeSummaryResponse（is_draft=True）。
4. **Codex 约束遵守**：RAG 回答带引用（source/chunk 列表）；AI 输出只作为建议或草稿（is_draft=True），不自动覆盖正文或设定；用户可明确区分 AI 建议与本书内容。
5. **前端面板设计**：复用搜索面板 CSS 模式（search-panel、search-mode-toggle、mode-button），包含黄色 AI 警告提示，摘要面板显示"草稿"徽章，引用点击可跳转浏览模式。
6. **测试覆盖**：后端新增 27 个测试（总计 154 个），覆盖正常流程、边界条件、错误处理。

## Deviations from Codex Plan

无偏差。

## Verification Commands Run

- `pytest tests/` → ✅ 154 passed (2.28s)
- `npm run type-check` → ✅
- `npm run test:unit -- --run` → ✅ 51 passed (1.05s)
- `npm run build` → ✅ (215 modules, 184.86KB CSS + 419.28KB JS, 552ms)

## Verification Results

全部通过。后端 154 个测试（较 K4 新增 27 个），前端 51 个单元测试，type-check 和生产构建均成功。

## Known Issues

1. **Stub LLM**：StubLLMProvider 返回纯模板文本，不具备真实 AI 能力。接入真实 LLM 需要实现新的 LLMProvider 子类。
2. **向量索引依赖**：RAG 和摘要的 semantic/hybrid 模式依赖 K4 向量索引，未建立索引时只有 keyword 结果。
3. **摘要 chunk 上限**：`_gather_all` 限制 50 条 chunk，大型知识库可能需要分页或配置上限。
4. **无对话历史**：问答面板每次提问独立，不支持多轮对话上下文。

## Suggested Next Review Points for Codex

1. LLMProvider Protocol 接口是否需要扩展（system prompt、temperature、max_tokens 等参数）。
2. 是否需要在前端增加"复制回答"和"复制摘要"按钮。
3. 是否需要支持多轮对话（对话历史管理）。
4. AI 摘要服务的 chunk 收集上限是否需要用户可配置。
5. 是否需要在写作页右侧面板集成"相关参考推荐"（基于当前编辑章节的语义检索）。
