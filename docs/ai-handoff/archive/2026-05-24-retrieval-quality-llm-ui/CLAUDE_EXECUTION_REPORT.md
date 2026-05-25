---
archived_before_next_feature_discussion: true
date: 2026-05-24
task: 检索质量优化 + LLM 接入 + 知识库 UI 精简
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

为知识库检索新增"检索质量层"（评分、过滤、重排序）和 DashScope chat/completions LLM 接入；修复 strictness 默认值不匹配导致问答返回空结果的问题；精简知识库模块 UI，消除按钮堆砌感。

## Files Changed

### 新增（6 个）
- `backend/app/services/retrieval_quality_service.py` — 检索质量层核心实现
- `backend/app/infrastructure/dashscope_llm_provider.py` — DashScope LLM Provider
- `backend/app/infrastructure/llm_provider_factory.py` — LLM Provider 工厂
- `backend/tests/test_retrieval_quality_service.py` — 质量层测试（38 个用例）
- `backend/tests/test_llm_provider_factory.py` — 工厂测试（10 个用例）
- `backend/tests/test_dashscope_llm_provider.py` — LLM Provider 测试（15 个用例）

### 修改（后端）
- `backend/app/services/retrieval_service.py` — 集成质量层，三种搜索模式统一评分过滤
- `backend/app/services/knowledge_retrieval_service.py` — 新增 _search_candidates()
- `backend/app/services/rag_service.py` — strictness 默认改为 balanced，检索为空返回提示不调 LLM
- `backend/app/services/ai_summary_service.py` — strictness="balanced"，收集 warnings
- `backend/app/schemas/knowledge_retrieval.py` — 增加质量评分字段
- `backend/app/schemas/rag.py` — strictness 默认改为 balanced，增加 retrieval_warning/match_quality/warnings
- `backend/app/api/knowledge_retrieval.py` — strictness 查询参数，limit 默认 50→20
- `backend/app/api/rag.py` — LLM factory 注入
- `backend/app/services/app_config_service.py` — LLM 配置常量
- `backend/app/schemas/app_config.py` — LLM 配置 schema
- `backend/app/api/app_config.py` — LLM 配置端点 + test-llm

### 修改（前端）
- `frontend/src/entities/knowledge/types.ts` — KnowledgeRetrievalStrictness 类型，质量评分字段
- `frontend/src/entities/knowledge/api.ts` — strictness 参数传递
- `frontend/src/features/knowledge/KnowledgeSearchPanel.vue` — 匹配范围控件、质量标签、filtered_count 提示
- `frontend/src/features/knowledge/KnowledgeAskPanel.vue` — 新增 strictness 控件、match_quality 标签、retrieval_warning；移除资料类型/可信度/引用数量/重置筛选控件
- `frontend/src/features/knowledge/KnowledgeSummaryPanel.vue` — warnings 提示条
- `frontend/src/entities/app-config/types.ts` — LLM 配置类型
- `frontend/src/entities/app-config/api.ts` — testDashScopeLlmConnection()
- `frontend/src/features/app-config/AppSettingsDialog.vue` — AI 问答模型区块
- `frontend/src/pages/knowledge/ProjectKnowledgePage.vue` — 头部重构：视图切换移入头部行，批量导入保留为主按钮，新建空白资料和刷新索引收入"更多"下拉菜单；移除浏览模式外的"返回资料列表"按钮；工具栏仅在浏览模式显示；无选中资料时隐藏右侧索引/关联面板，详情面板自动扩展填满剩余宽度，消除三栏布局空白问题；调整三栏布局宽度比例，左侧列表 240-280px、中间编辑区 min 480px/1fr、右侧索引 240-280px，给编辑表单更多空间
- `frontend/src/pages/projects/ProjectDetailPage.vue` — 移除左上角书名标题（`<h1>`）；修复分屏模式下"搜索"和"检查"按钮被 flex `align-items: stretch` 拉伸至铺满宽度的问题（改为 `align-items: flex-start`）；"更多"下拉菜单改为向右展开（`left: 0`），避免分屏在左侧时菜单向左展开被遮挡

## Implementation Notes

### 检索质量层
1. **分数归一化**：ScoreProfile 将不同 embedding provider 的 cosine 分布映射到 [0,1]
2. **Hybrid 统一评分**：keyword + semantic 独立召回后合并候选，统一通过质量层评分排序
3. **LLM 注入**：composition root 模式，API 路由层 factory 创建 provider 注入 service

### Strictness 修复
- 降低阈值：strict 0.70→0.55，balanced 0.40→0.35
- Q&A 默认 strictness 从 strict 改为 balanced，与检索面板对齐
- AskPanel 新增匹配范围控件，用户可手动调为精准/宽泛

### UI 精简
1. **头部整合**：将视图模式切换（浏览/检索/问答/摘要）移入头部 actions-row，与操作按钮同行。消除之前头部标题 + 下方工具栏两行按钮堆砌问题。
2. **更多菜单**：低频操作（新建空白资料、刷新知识索引）收入"更多 ▾"下拉菜单，只保留"批量导入"作为主要 CTA。
3. **移除冗余导航**：删除非浏览模式下的"← 返回资料列表"按钮（头部切换已足够）。
4. **问答面板精简**：移除问答面板的资料类型、可信度、引用数量、重置四个筛选控件。搜索模式和匹配范围是问答质量的主要控制项，细粒度筛选已在专用检索面板提供。
5. **工具栏条件化**：搜索/筛选工具栏仅在浏览模式下显示。
6. **右栏条件渲染**：无选中资料时隐藏右侧"索引片段/关联"面板，布局从三栏（列表+详情+右栏）收缩为两栏（列表+详情），详情面板通过 `:not(.no-right-panel)` CSS 选择器自动扩展占满剩余宽度，消除大面积空白。选中资料后右栏出现，恢复三栏。
7. **写作工作区分屏修复**：`≤1099px` 断点下 `.page-header` 和 `.header-actions` 使用 `align-items: stretch` 导致 `toolbar-link` RouterLink 按钮被拉伸到铺满整行。改为 `align-items: flex-start`，按钮保持自然宽度。同时移除左上角 `<h1>` 书名显示，精简头部。

## Deviations from Codex Plan

- Step A3 中 knowledge_retrieval_service.py 的 _search_candidates() 实际未独立拆分，在 RetrievalService 内部处理。
- Strictness 阈值和默认值在实现后根据用户反馈做了调整（计划中 strict≥0.70/balanced≥0.40，实际 strict≥0.55/balanced≥0.35）。
- UI 精简为计划外追加工作，基于用户反馈"按钮堆砌"问题。

## Verification Commands Run

- `python -m pytest tests/ -v` → ✅ 307 passed (244 existing + 63 new)
- `npm run type-check` → ✅ 无错误
- `npm run build` → ✅ 构建成功（223 modules，619ms）

## Verification Results

- 后端：307/307 测试通过
- 前端：TypeScript 类型检查通过，Vite 生产构建成功

## Known Issues

- 质量层阈值（strict≥0.55, balanced≥0.35, broad≥0.15）已下调一次，实际效果仍需用户数据验证。
- CJK anchor 提取对连续中文不做分词，可能影响 keyword_score 精度。
- DashScope LLM Provider 的 MAX_CONTEXT_CHARS=8000 为保守值。

## Suggested Next Review Points for Codex

1. 质量层阈值是否需要进一步基于实际使用数据校准
2. CJK anchor 提取是否需要分词支持
3. "更多"下拉菜单的交互模式是否适合移动端（当前为 click 触发）
4. 问答面板移除细粒度筛选后，是否需要提供"高级选项"折叠区域保留可扩展性
