<!-- Archived before planning knowledge-ui-layout-progress on 2026-05-24. -->

# Task Summary

规划知识库模块的索引维护体验调整：不要在作者面向 UI 中暴露“重建分块”“生成向量”“重建全部索引”等技术按钮；改为一个用户可理解的“刷新知识索引”入口。刷新时允许用户选择分块大小：小 / 中 / 大，并在操作前用简体中文明确说明不同选择的后果和风险，例如分块太细会让内容更碎、结果可能重复、刷新更慢、占用更多索引空间；分块太大可能导致细节不容易被检索命中。

Codex 本轮未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

1. 已阅读 Claude Code 最新执行报告：
   - 上一任务为“写作工作区排版体验升级”。
   - Claude 新增了写作区规则排版、撤销排版、对齐按钮图标，并通过 `npm run type-check`、`npm run test:unit -- --run`、`npm run build`。
   - 报告还记录了知识库 `.doc` 导入支持：新增 `olefile` 解析旧版 Word 文档，并通过后端知识库导入相关测试。
2. 旧交接文件已归档到：
   - `docs/ai-handoff/archive/2026-05-24-writing-workspace-formatting/CODEX_PLAN.md`
   - `docs/ai-handoff/archive/2026-05-24-writing-workspace-formatting/CLAUDE_EXECUTION_REPORT.md`
3. 当前知识库主页面：
   - 文件：`frontend/src/pages/knowledge/ProjectKnowledgePage.vue`
   - 直接导入了 `rebuildKnowledgeChunks`、`rebuildKnowledgeIndex`、`buildSourceEmbeddings`、`getKnowledgeIndexStatus`。
   - 右侧 `chunks` tab 中直接展示：
     - `重建分块`
     - `生成向量`
     - `向量索引：x / y`
     - `重建全部索引`
     - 空状态文案：`暂无分块。填写正文内容后点击"重建分块"自动生成。`
   - 这些文案对网文作者过于技术化，不应作为主 UI。
4. 当前前端知识库 API：
   - 文件：`frontend/src/entities/knowledge/api.ts`
   - 已有：
     - `rebuildKnowledgeChunks(sourceId)`
     - `getKnowledgeIndexStatus(projectId)`
     - `rebuildKnowledgeIndex(projectId)`
     - `buildSourceEmbeddings(sourceId)`
   - 当前 API 命名和页面调用都以技术概念为中心。
5. 当前前端知识库类型：
   - 文件：`frontend/src/entities/knowledge/types.ts`
   - 已有 `KnowledgeIndexStatus`、`KnowledgeRebuildIndexResponse`、`KnowledgeBuildSourceEmbeddingsResponse`。
   - 没有 `chunk_size`、`refresh scope` 或“刷新知识索引”的业务化 request/response 类型。
6. 当前后端分块逻辑：
   - 文件：`backend/app/services/knowledge_service.py`
   - 固定常量：
     - `CHUNK_MIN_CHARS = 800`
     - `CHUNK_MAX_CHARS = 1200`
   - `KnowledgeService.rebuild_chunks(source_id)` 调用 `_rebuild_chunks_for_source(source)`，没有接收分块大小参数。
   - `create_source()` 和 `update_source()` 在创建或正文变更时自动重建分块。
7. 当前后端向量/索引逻辑：
   - API 文件：`backend/app/api/knowledge_embedding.py`
   - Service 文件：`backend/app/services/knowledge_embedding_service.py`
   - Schema 文件：`backend/app/schemas/knowledge_embedding.py`
   - 已有接口：
     - `POST /api/projects/{project_id}/knowledge/embeddings/rebuild`
     - `POST /api/knowledge-sources/{source_id}/embeddings`
     - `GET /api/projects/{project_id}/knowledge/embeddings/status`
   - 这些接口可以保留作为内部兼容接口，但不应由作者 UI 直接暴露技术动作。
8. 当前后端没有一个“刷新知识索引”的业务编排层。
   - 重建分块和生成 embeddings 是两个不同 service 的动作。
   - 新需求需要一个协调入口：先按用户选择的分块大小整理资料片段，再刷新检索索引。
9. 当前测试：
   - 后端已有 `backend/tests/test_knowledge_service.py`、`backend/tests/test_knowledge_embedding_service.py`、`backend/tests/test_knowledge_import.py`、`backend/tests/test_knowledge_retrieval.py`。
   - 前端当前没有知识库 UI 相关单元测试文件。

# Architecture Decision

1. 面向作者的 UI 使用“知识索引 / 刷新索引 / 索引片段 / 检索准备度”等表达，不再直接展示“向量”“embedding”“重建分块”“生成向量”。
2. 后端保留现有技术接口以降低破坏风险，但新增一个用户语义更清晰的刷新入口，供前端主 UI 使用：
   - 建议：`POST /api/projects/{project_id}/knowledge/index/refresh`
   - 可选参数：
     - `scope`: `project` 或 `source`
     - `source_id`: 当 scope 为 `source` 时必填
     - `chunk_size`: `small`、`medium`、`large`
3. 新增后端业务编排 service，避免把跨 service 逻辑堆进 API 层：
   - 建议新增 `backend/app/services/knowledge_index_refresh_service.py`
   - 职责：校验项目/资料、按分块大小重建资料片段、刷新索引、返回用户可理解的统计。
4. 分块大小先作为“刷新索引时的操作参数”，不在本任务强制新增数据库字段。
   - 默认使用 `medium`，对应当前 800-1200 字符区间，保持现有行为。
   - 前端可用 localStorage 记住用户上次选择，提升体验。
   - 如果未来需要项目级永久索引配置，再单独规划 `knowledge_index_settings` 表或项目配置字段。
5. `KnowledgeService` 应支持参数化分块策略：
   - 当前创建/更新资料时仍使用默认 `medium`。
   - 刷新索引时可传入 `small`、`medium`、`large`。
   - 分块算法继续留在 knowledge service，embedding 逻辑继续留在 embedding service。
6. 刷新索引流程建议：
   - 按 scope 找到目标资料。
   - 对目标资料按 `chunk_size` 重建 chunks。
   - 删除对应旧 embeddings。
   - 为新 chunks 生成 embeddings。
   - 返回刷新结果。
7. 不新增真实外部 AI 调用，不改变 RAG 问答和 AI 总结逻辑。
8. 不把技术细节完全隐藏到无法排障：
   - 默认 UI 不显示“向量 / embedding”。
   - 可以在折叠的“索引片段预览”里查看片段内容和数量。
   - 风险说明必须面向用户说人话。

# Files to Create or Modify

建议新增：

- `backend/app/services/knowledge_index_refresh_service.py`
- `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue`

建议修改：

- `backend/app/services/knowledge_service.py`
- `backend/app/services/knowledge_embedding_service.py`
- `backend/app/api/knowledge_embedding.py`
- `backend/app/schemas/knowledge_embedding.py`
- `backend/tests/test_knowledge_service.py`
- `backend/tests/test_knowledge_embedding_service.py`
- `frontend/src/entities/knowledge/api.ts`
- `frontend/src/entities/knowledge/types.ts`
- `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`

可选新增或修改：

- `frontend/src/__tests__/knowledge-index-refresh.spec.ts`

不建议修改：

- `backend/app/models/knowledge_source.py`
- `backend/app/models/knowledge_chunk.py`
- `backend/app/models/knowledge_embedding.py`
- 数据库迁移文件
- RAG / AI 总结相关 service：
  - `backend/app/services/rag_service.py`
  - `backend/app/services/ai_summary_service.py`
  - `backend/app/api/rag.py`

执行完成后必须创建：

- `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`

# Implementation Steps for Claude Code

1. 执行前检查
   - 阅读本计划。
   - 执行 `git status --short`，记录当前工作区状态。
   - 注意当前工作区可能已有上一轮 Claude 对 `ChapterEditor.vue`、知识库导入、`.doc` 支持等改动，不要回滚。
   - 本任务只处理知识库索引维护体验，不修改写作工作区、不修改设定/人物/伏笔/关系图。

2. 设计分块大小配置
   - 在 `backend/app/services/knowledge_service.py` 中新增分块大小类型和配置。
   - 建议配置：

```python
KnowledgeChunkSize = Literal["small", "medium", "large"]

CHUNK_SIZE_PROFILES = {
    "small": {"min_chars": 350, "max_chars": 600},
    "medium": {"min_chars": 800, "max_chars": 1200},
    "large": {"min_chars": 1500, "max_chars": 2200},
}
DEFAULT_CHUNK_SIZE: KnowledgeChunkSize = "medium"
```

   - `medium` 必须保持当前 800-1200 字符区间，避免默认行为变化过大。
   - 如果 Claude Code 判断具体数值需要微调，必须在执行报告中说明理由。

3. 参数化 KnowledgeService 分块逻辑
   - 修改 `KnowledgeService.rebuild_chunks()`：
     - 接收可选 `chunk_size: KnowledgeChunkSize = DEFAULT_CHUNK_SIZE`。
   - 修改 `_rebuild_chunks_for_source()`：
     - 接收 `chunk_size`。
     - 读取 `min_chars`、`max_chars`。
     - 调用参数化 split helper。
   - 修改 `_split_content()`、`_merge_small_sections()`、`_split_large_text()`：
     - 不再直接依赖全局 `CHUNK_MIN_CHARS`、`CHUNK_MAX_CHARS`。
     - 改为显式接收 `min_chars`、`max_chars`。
   - `create_source()` 和 `update_source()` 保持默认 `medium`。
   - `metadata_json` 可选记录 `{"chunk_size": "small"}` 等信息，便于排障；但不要依赖数据库新字段。

4. 支持按资料删除旧索引
   - `KnowledgeEmbeddingService` 已有 `remove_source_embeddings(source_id)`。
   - 如当前 project 级刷新只能全部删除 project embeddings，建议保留。
   - 新增或确认：
     - source 级刷新时先 `remove_source_embeddings(source_id)`。
     - project 级刷新时可以先删除整个 project embeddings，再统一重建。
   - 不要在 API 层直接操作数据库删除 embeddings。

5. 新增知识索引刷新编排 service
   - 新增 `backend/app/services/knowledge_index_refresh_service.py`。
   - 建议定义异常：
     - `KnowledgeIndexRefreshProjectNotFoundError`
     - `KnowledgeIndexRefreshSourceNotFoundError`
     - `KnowledgeIndexRefreshInvalidScopeError`
   - 建议方法：

```python
class KnowledgeIndexRefreshService:
    def refresh_project(self, project_id: str, chunk_size: KnowledgeChunkSize) -> KnowledgeIndexRefreshResult: ...
    def refresh_source(self, source_id: str, chunk_size: KnowledgeChunkSize) -> KnowledgeIndexRefreshResult: ...
```

   - project 级逻辑：
     - 确保项目存在。
     - 获取项目下所有 active sources。
     - 对每个 source 调用 `KnowledgeService.rebuild_chunks(source.id, chunk_size=chunk_size)`。
     - 删除 project 旧 embeddings。
     - 重建 project embeddings。
     - 返回 source_count、chunk_count、indexed_count、chunk_size、warnings。
   - source 级逻辑：
     - 确保 source 存在。
     - 调用 `KnowledgeService.rebuild_chunks(source.id, chunk_size=chunk_size)`。
     - 删除该 source 旧 embeddings。
     - 调用 `KnowledgeEmbeddingService.index_source(source.id)`。
     - 返回 source_count=1、chunk_count、indexed_count、chunk_size、warnings。
   - 对空内容资料：
     - 不报错。
     - warnings 中提示有空资料不会进入索引。

6. 新增或扩展后端 schema
   - 修改 `backend/app/schemas/knowledge_embedding.py`。
   - 建议新增：

```python
KnowledgeRefreshScope = Literal["project", "source"]
KnowledgeChunkSize = Literal["small", "medium", "large"]

class RefreshKnowledgeIndexRequest(BaseModel):
    scope: KnowledgeRefreshScope = "project"
    source_id: str | None = None
    chunk_size: KnowledgeChunkSize = "medium"

class RefreshKnowledgeIndexResponse(BaseModel):
    source_count: int
    chunk_count: int
    indexed_count: int
    chunk_size: KnowledgeChunkSize
    model_name: str
    warnings: list[str] = []
```

   - `model_name` 可以返回给前端，但默认 UI 不必展示。
   - 如用户只需要“刷新结果”，前端显示 `已刷新 N 条资料，生成 M 个索引片段。`

7. 新增用户语义 API
   - 修改 `backend/app/api/knowledge_embedding.py`。
   - 新增：

```text
POST /api/projects/{project_id}/knowledge/index/refresh
```

   - 请求体：

```json
{
  "scope": "project",
  "source_id": null,
  "chunk_size": "medium"
}
```

   - 如果 `scope === "source"`，必须校验 `source_id` 不为空且属于当前 project。
   - 返回 `RefreshKnowledgeIndexResponse`。
   - 现有技术接口可保留，不要为了本任务删接口导致已有测试或功能破坏。
   - 但前端作者 UI 不再调用 `rebuildKnowledgeChunks()`、`buildSourceEmbeddings()`、`rebuildKnowledgeIndex()`。

8. 调整前端知识库类型
   - 修改 `frontend/src/entities/knowledge/types.ts`。
   - 新增：

```ts
export type KnowledgeChunkSize = 'small' | 'medium' | 'large'
export type KnowledgeIndexRefreshScope = 'project' | 'source'

export interface RefreshKnowledgeIndexPayload {
  scope: KnowledgeIndexRefreshScope
  source_id?: string | null
  chunk_size: KnowledgeChunkSize
}

export interface RefreshKnowledgeIndexResponse {
  source_count: number
  chunk_count: number
  indexed_count: number
  chunk_size: KnowledgeChunkSize
  model_name: string
  warnings: string[]
}
```

   - 可新增用户可见 label/description map：

```ts
export const knowledgeChunkSizeLabels = {
  small: '小',
  medium: '中',
  large: '大',
}
```

9. 调整前端知识库 API
   - 修改 `frontend/src/entities/knowledge/api.ts`。
   - 新增：

```ts
export function refreshKnowledgeIndex(
  projectId: string,
  payload: RefreshKnowledgeIndexPayload,
): Promise<RefreshKnowledgeIndexResponse>
```

   - 调用：

```text
POST /api/projects/${projectId}/knowledge/index/refresh
```

   - 保留旧函数导出以降低破坏风险，但从 `ProjectKnowledgePage.vue` 移除直接使用。

10. 新增刷新索引对话框
   - 新增 `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue`。
   - 对话框标题建议：`刷新知识索引`。
   - 说明文案建议：
     - `当你导入、修改了资料，或搜索/问答没有命中新内容时，可以刷新知识索引。刷新会重新整理资料片段并更新检索结果。`
   - scope 选择：
     - `全部资料`
     - `当前资料`
   - 如果没有选中资料，则禁用 `当前资料`。
   - 分块大小选择：
     - `小`
     - `中（推荐）`
     - `大`
   - 风险说明必须随选择变化：
     - 小：`更容易命中细节，但内容会被切得更碎，搜索结果可能重复，刷新耗时和索引占用会增加。`
     - 中：`适合大多数小说资料，兼顾细节命中和上下文完整度。`
     - 大：`能保留更完整上下文，但细节命中可能下降，问答时可能带入较长无关内容。`
   - 二次确认文案：
     - `刷新期间请不要关闭页面。资料较多时可能需要一些时间。`
   - 主按钮：
     - `开始刷新`
   - 进行中：
     - `正在刷新索引...`
   - 完成后：
     - `已刷新 X 条资料，整理出 Y 个索引片段。`
   - 不要在对话框中出现：
     - `向量`
     - `embedding`
     - `生成向量`
     - `重建分块`

11. 改造 `ProjectKnowledgePage.vue` 的 UI
   - 移除作者可见按钮：
     - `重建分块`
     - `生成向量`
     - `重建全部索引`
   - 移除或改写作者可见状态：
     - `向量索引：x / y`
   - 在页面适合位置增加一个入口：
     - 按钮：`刷新知识索引`
   - 推荐放置位置：
     - 页面 header 操作区，和 `批量导入`、`新建空白资料` 同级，但用 secondary 样式。
     - 或右侧索引片段区域顶部，但仍应是单一入口。
   - 状态文案建议：
     - `索引状态：已准备 x / y 个片段`
     - 或 `检索准备度：x / y`
   - 右侧 tab 建议：
     - `分块预览` 改为 `索引片段`
   - 空状态建议：
     - `暂无索引片段。保存或导入资料后系统会自动整理；如果搜索不到新内容，可以刷新知识索引。`
   - 成功消息建议：
     - `知识索引已刷新：X 条资料，Y 个索引片段。`
   - 错误消息建议：
     - `刷新知识索引失败，请稍后重试。`

12. 保留技术能力但不暴露技术文案
   - `chunks` 列表可继续用于“索引片段”预览。
   - `token_count` UI label 不建议写“token”，改为：
     - `约 N 字`
   - 如果需要显示模型名，只放在开发/调试折叠区，不在默认 UI 展示。

13. 前端状态和交互
   - 在 `ProjectKnowledgePage.vue` 中新增：
     - `isRefreshDialogOpen`
     - `isRefreshingIndex`
   - 对话框完成后：
     - 调用 `loadIndexStatus()`
     - 如果当前选中了资料，调用 `loadChunks()`
     - 如果列表可能受影响，必要时调用 `loadSources()`
   - 刷新时禁用重复提交。
   - 不要让刷新索引影响当前编辑表单的未保存内容。
   - 如果当前资料表单有未保存改动，点击刷新前提示：
     - `当前资料有未保存内容。请先保存后再刷新索引，否则索引仍基于上一次保存的正文。`
   - 如当前代码没有 dirty 检测，可在计划执行中补一个轻量 `hasSourceFormDirty` computed，只用于提示，不做复杂状态系统。

14. 后端测试
   - 修改或新增后端测试。
   - `backend/tests/test_knowledge_service.py`：
     - `medium` 分块保持现有默认行为。
     - `small` 产生的 chunk 数量应大于或等于 `medium`。
     - `large` 产生的 chunk 数量应小于或等于 `medium`。
     - invalid chunk size 如通过 API 传入应返回 422 或 400。
   - `backend/tests/test_knowledge_embedding_service.py` 或新增 refresh service 测试：
     - project 级 refresh 会重建 chunks 并刷新 embeddings。
     - source 级 refresh 只影响当前 source。
     - 空资料不会报错，并返回 warning。
     - 不存在 project/source 返回 404。
   - 如果新增 `test_knowledge_index_refresh_service.py` 更清晰，可以采用新增文件。

15. 前端测试
   - 可选新增 `frontend/src/__tests__/knowledge-index-refresh.spec.ts`。
   - 至少测试纯数据或组件能覆盖：
     - 分块大小 label 和风险说明完整。
     - `refreshKnowledgeIndex()` 使用新 endpoint 和 payload。
     - 页面不再出现 `重建分块`、`生成向量`、`向量索引`、`重建全部索引` 等作者可见文案。
   - 如果组件测试成本过高，至少保证 `npm run type-check` 和手动检查通过。

16. 执行报告
   - 创建新的 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
   - 报告必须说明：
     - 改了哪些文件。
     - 作者 UI 中哪些技术按钮被移除。
     - 新的“刷新知识索引”入口在哪里。
     - 小/中/大分块大小的实际字符范围。
     - 刷新索引是否支持当前资料和全部资料。
     - 是否保留旧技术 API。
     - 验证命令结果。

# Constraints

1. 不要在作者面向 UI 中出现 `生成向量`、`向量索引`、`embedding`、`重建分块`、`重建全部索引`。
2. 可以在代码、API、service 内保留 embedding/chunk 命名，但 UI 文案必须转为用户可理解表达。
3. 不要删除现有后端技术接口，除非确认没有任何调用和测试依赖；本任务推荐保留。
4. 不要新增真实外部 AI 调用。
5. 不要修改 RAG 问答、AI 总结、向量检索核心搜索逻辑。
6. 不要新增数据库迁移，除非 Claude Code 发现当前实现无法不迁移完成；如需要迁移必须停止并反馈。
7. 不要把索引刷新编排逻辑写进 API router。
8. 不要把 embedding 逻辑写进前端组件。
9. 用户可见文案使用简体中文。
10. 不要引入大型 UI 库。
11. 不要修改知识库导入文件解析逻辑，除非刷新索引流程必须读取导入结果；默认不需要。
12. 不要修改写作工作区、人物、设定、伏笔、关系图等无关模块。
13. 不要提交本地数据库、日志、临时文件、上传测试文件或构建产物。

# Verification Commands

后端：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
pytest tests/test_knowledge_service.py
pytest tests/test_knowledge_embedding_service.py
pytest tests/test_knowledge_retrieval.py
pytest
```

前端：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit -- --run
npm run build
```

手动检查：

```text
/projects/:projectId/knowledge
确认页面不再显示“重建分块”
确认页面不再显示“生成向量”
确认页面不再显示“向量索引”
确认页面不再显示“重建全部索引”
确认存在“刷新知识索引”入口
点击“刷新知识索引”
确认可选“全部资料 / 当前资料”
确认可选分块大小“小 / 中 / 大”
确认“小 / 中 / 大”各自有清楚的后果和风险说明
选择“小”刷新，确认完成提示为用户语言
选择“中”刷新，确认是推荐默认值
选择“大”刷新，确认完成提示为用户语言
刷新后确认搜索和问答仍可使用
确认索引片段预览仍可查看，但文案不是技术按钮
```

# Acceptance Criteria

1. `CODEX_PLAN.md` 已由 Codex 写入，业务代码未由 Codex 修改。
2. Claude Code 执行后，知识库作者 UI 不再出现 `重建分块`、`生成向量`、`向量索引`、`重建全部索引`。
3. 知识库页面提供清晰的 `刷新知识索引` 入口。
4. 刷新索引支持选择 `小`、`中`、`大` 分块大小。
5. `中` 为默认推荐选项，并保持当前 800-1200 字符区间。
6. 每个分块大小选项都有用户能理解的风险说明。
7. 刷新索引至少支持全部资料；如当前选中资料，支持只刷新当前资料。
8. 刷新索引会重新整理索引片段并刷新检索索引。
9. 刷新后搜索和问答仍可正常使用。
10. 页面状态使用 `索引状态`、`检索准备度` 或 `索引片段` 等用户语言。
11. 技术 API 可保留，但不再由作者 UI 直接暴露为技术按钮。
12. 后端 API 层不堆业务编排逻辑。
13. 后端测试覆盖分块大小和刷新索引流程。
14. 前端通过 type-check、单元测试和 build。
15. Claude Code 创建 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md` 并记录执行结果。

# Risks and Watchpoints

1. 分块大小会影响检索质量，不只是 UI 选项。小分块可能提高细节命中，但上下文更碎、结果更重复、刷新更慢、索引占用更多。
2. 大分块上下文更完整，但细节可能被淹没，问答可能带入更多无关内容。
3. 如果刷新索引自动改写 chunks，会影响后续搜索和 RAG 引用片段，必须测试检索仍可用。
4. 如果 source 级刷新只刷新该 source，需要确保旧 source embeddings 被删除，否则会出现过期检索结果。
5. 如果 project 级刷新先删除 embeddings 后失败，可能导致索引暂时不可用；应尽量在错误提示中说明可再次刷新。
6. 不持久化用户选择的 chunk_size 可能导致下次创建/编辑资料仍使用默认 medium。本任务可以接受，但执行报告必须说明。
7. 现有前端 `KnowledgeSearchPanel` 和 `KnowledgeAskPanel` 也有“分块”文案，Claude Code 应评估是否同步改成“索引片段”，但不要扩大到改 RAG 逻辑。
8. 后端现有技术接口保留后，代码中仍会有 vector/embedding 命名，这是内部实现允许的；复审重点是用户 UI 和业务化入口。
9. 刷新索引可能耗时，前端必须防重复点击。
10. 不要因为 UI 包装而掩盖失败，需要保留明确错误提示。

# Review Checklist

Codex 复审时应检查：

1. Claude 是否先读取本计划并生成执行报告。
2. 是否归档了旧交接文件，活跃交接文件只代表当前任务。
3. 作者 UI 是否完全移除了 `重建分块`、`生成向量`、`向量索引`、`重建全部索引`。
4. 是否新增了 `刷新知识索引` 入口。
5. 刷新入口是否有小 / 中 / 大分块大小选择。
6. 风险说明是否清楚解释分块过细和过大的后果。
7. 是否默认推荐 `中`。
8. 后端是否支持按不同分块大小重建索引片段。
9. 刷新流程是否同时处理片段重建和检索索引刷新。
10. 是否有 source 级刷新时清理旧 embeddings 的逻辑。
11. API 层是否没有堆复杂业务编排。
12. 是否没有修改 RAG / AI 总结核心逻辑。
13. 是否没有新增不必要依赖或数据库迁移。
14. 搜索和问答是否仍可用。
15. 测试是否覆盖分块大小、刷新流程、错误场景。
16. 是否有不该提交的密钥、本地配置、临时文件、数据库或日志。
17. 最终建议应明确为 Accept、Minor Revision 或 Rework。
