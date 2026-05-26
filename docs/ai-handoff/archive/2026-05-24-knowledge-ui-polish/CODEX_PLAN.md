<!-- Archived before planning knowledge-vector-provider-upgrade on 2026-05-24. -->

# Task Summary

规划知识库模块的 UI 细节修正。本任务围绕上一轮“刷新知识索引”改造后的体验问题继续优化：

1. 修复 `刷新知识索引` 小窗口正文区域左右贴边的问题。
2. 为刷新索引过程新增可见进度条，让用户能直观看到刷新进度。
3. 调整知识库浏览页的资料编辑区：正文内容应占更大比重，作者、来源、摘要、类型、状态、可信度、标签等信息放入二级菜单。
4. 统一 `检索`、`问答`、`摘要` 三个子模块的页面横向间距，避免核心卡片贴着浏览器边缘，应与 `浏览` 子模块的最大宽度和左右留白保持一致。

Codex 本轮未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

1. 已阅读 Claude Code 最新执行报告：
   - 上一任务为“知识库索引刷新 UX 改造”。
   - Claude 已新增 `KnowledgeIndexRefreshDialog.vue`、`knowledge_index_refresh_service.py`、`POST /api/projects/{project_id}/knowledge/index/refresh`。
   - Claude 已移除知识库作者 UI 中的 `重建分块`、`生成向量`、`向量索引`、`重建全部索引` 等技术按钮/文案。
   - 验证通过：后端 189 个测试、前端 80 个单元测试、type-check 和 build。
2. 旧交接文件已归档到：
   - `docs/ai-handoff/archive/2026-05-24-knowledge-index-refresh-ux/CODEX_PLAN.md`
   - `docs/ai-handoff/archive/2026-05-24-knowledge-index-refresh-ux/CLAUDE_EXECUTION_REPORT.md`
3. `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue` 当前问题：
   - `.refresh-body` 使用 `padding: var(--zs-space-md, 16px) 0;`
   - 项目全局 token 中没有 `--zs-space-md`，实际走 fallback。
   - 横向 padding 为 `0`，导致说明、选项组和风险提示贴近弹窗左右边缘。
   - `step-refreshing` 目前只有 spinner 和文字 `正在刷新索引...`，没有进度条。
   - 刷新成功后组件会 `emit('refreshed')`；父组件 `handleRefreshed()` 会立即关闭弹窗，用户可能看不到 `result` 步骤的完成摘要。
4. `frontend/src/pages/knowledge/ProjectKnowledgePage.vue` 当前问题：
   - 页面最大宽度规则只覆盖 `.page-header`、`.error-banner`、`.success-banner`、`.state-message`、`.knowledge-toolbar`、`.knowledge-layout`。
   - `KnowledgeSearchPanel`、`KnowledgeAskPanel`、`KnowledgeSummaryPanel` 在 `viewMode !== 'browse'` 时直接渲染，没有统一外层 shell，因此在大屏或窄屏下与 `浏览` 模块的左右间距不一致。
   - `view-back` 有 `max-width: 1480px`，但三个子模块主体没有对应容器。
   - 浏览页 detail 表单目前将标题、类型、状态、可信度、来源、作者、摘要、正文、标签全部同级展示。
   - 正文 `textarea` 只有 `rows="12"`，且被较多元信息挤压，知识库文档正文不是视觉主区域。
5. `frontend/src/features/knowledge/KnowledgeSearchPanel.vue`、`KnowledgeAskPanel.vue`、`KnowledgeSummaryPanel.vue` 当前共性：
   - 根节点均为 `<section class="search-panel">`。
   - `.search-panel` 自身是卡片样式，包含 `padding: 20px`、`border`、`background`。
   - 问题不在组件内部卡片是否有 padding，而在父页面没有像 `knowledge-layout` 一样提供统一最大宽度容器。
6. 当前后端刷新 API 已支持：
   - project scope 刷新。
   - source scope 刷新。
   - 分块大小 `small`、`medium`、`large`。
   - 这足以支持前端按资料逐个刷新，从而实现 source 级真实进度。
7. 本任务预计不需要修改后端。

# Architecture Decision

1. 本任务以 UI 层优化为主，优先不修改后端。
2. 刷新索引进度条不要做纯假进度。
   - `全部资料` 刷新建议改为前端按资料逐个调用现有 source scope 刷新接口。
   - 每完成一条资料，更新 `processed / total` 和百分比。
   - `当前资料` 刷新只有一个目标，可显示单目标进度条或 indeterminate 状态，完成后到 100%。
3. 不新增后台 job、WebSocket、SSE 或数据库任务表。
   - 当前是本地写作工具，source 级顺序刷新足够直观、可测试，也不会扩大架构复杂度。
   - 如果 Claude Code 判断必须实现后端 job/polling 才能满足进度条，应先停止并在执行报告中说明原因，不要临时大改后端架构。
4. 刷新对话框完成后不应立即关闭。
   - 父页面可以刷新索引状态和片段列表。
   - 但弹窗应保留在 `result` 状态，让用户看到刷新结果和 warnings。
   - 用户点击 `关闭` 后再关闭弹窗。
5. 知识库资料编辑区应采用“正文优先”的信息架构：
   - 一级区域：标题、正文、保存/删除。
   - 二级菜单：类型、状态、可信度、来源 / 原路径 / URL、作者、摘要、标签。
   - 二级菜单可用 native `<details>`，保持轻量，不引入 UI 库。
6. `检索`、`问答`、`摘要` 子模块的布局统一在父页面处理。
   - 新增共享 shell，例如 `.knowledge-mode-panel`。
   - 让三个组件在同一个 max-width、margin auto、width 规则下渲染。
   - 不要在每个子组件中分别硬塞 viewport margin，避免重复和不一致。

# Files to Create or Modify

建议修改：

- `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue`
- `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`

可选修改：

- `frontend/src/features/knowledge/KnowledgeSearchPanel.vue`
- `frontend/src/features/knowledge/KnowledgeAskPanel.vue`
- `frontend/src/features/knowledge/KnowledgeSummaryPanel.vue`
- `frontend/src/__tests__/knowledge-index-refresh.spec.ts`

预计不需要修改：

- `backend/app/api/knowledge_embedding.py`
- `backend/app/services/knowledge_index_refresh_service.py`
- `backend/app/services/knowledge_service.py`
- `backend/app/services/knowledge_embedding_service.py`
- `backend/app/schemas/knowledge_embedding.py`
- 数据库模型或迁移文件

执行完成后必须创建：

- `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`

# Implementation Steps for Claude Code

1. 执行前检查
   - 阅读本计划。
   - 执行 `git status --short`，记录当前工作区状态。
   - 不要回滚上一轮 Claude 对知识库索引刷新、`.doc` 导入、写作工作区排版等已完成改动。
   - 本任务只处理知识库 UI 布局与刷新进度，不修改 RAG/AI/向量检索核心逻辑。

2. 修复刷新索引弹窗横向贴边
   - 修改 `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue`。
   - 将 `.refresh-body` 的横向 padding 从 `0` 改为明确的设计 token，例如：

```css
.refresh-body {
  display: flex;
  flex-direction: column;
  gap: var(--zs-space-4);
  padding: var(--zs-space-5) var(--zs-space-6);
}
```

   - 移除 `--zs-space-md`、`--zs-space-sm`、`--zs-space-lg` 这类项目未定义 token 的使用，统一改成已有 token：
     - `--zs-space-1`
     - `--zs-space-2`
     - `--zs-space-3`
     - `--zs-space-4`
     - `--zs-space-5`
     - `--zs-space-6`
     - `--zs-space-8`
   - 确保 warning、error、option group、result warning 的左右留白不贴边。
   - 增加移动端适配：

```css
@media (max-width: 560px) {
  .refresh-body {
    padding-inline: var(--zs-space-4);
  }
}
```

3. 为刷新索引增加进度状态
   - 在 `KnowledgeIndexRefreshDialog.vue` 中新增本地进度状态。
   - 建议类型：

```ts
interface RefreshProgressState {
  total: number
  completed: number
  currentTitle: string
  chunkCount: number
  indexedCount: number
  warnings: string[]
}
```

   - 新增 computed：
     - `progressPercent`
     - `progressText`
     - `hasProgress`
   - `progressPercent`：
     - `total > 0` 时为 `Math.round((completed / total) * 100)`。
     - `total === 0` 时为 `0`。

4. 使用 source scope 实现真实进度
   - 修改 `KnowledgeIndexRefreshDialog.vue` 的刷新逻辑。
   - 对 `scope === 'source'`：
     - target list 为当前选中资料一条。
     - 调用现有 `refreshKnowledgeIndex(projectId, { scope: 'source', source_id, chunk_size })`。
     - 完成后 `completed = 1`、`total = 1`。
   - 对 `scope === 'project'`：
     - 在开始刷新前调用 `listKnowledgeSources(projectId)` 获取未筛选的资料列表。
     - 不要使用父页面当前 `sources`，因为它可能被搜索或筛选过滤。
     - 对返回的每个 source，顺序调用：

```ts
await refreshKnowledgeIndex(projectId, {
  scope: 'source',
  source_id: source.id,
  chunk_size: chunkSize.value,
})
```

     - 每完成一个 source：
       - `completed += 1`
       - 累加 `chunk_count`
       - 累加 `indexed_count`
       - 合并 warnings
       - 更新 `currentTitle`
   - 如果资料数量为 0：
     - 显示完成态：`当前没有可刷新的资料。`
   - 注意：当前后端已有 project scope 刷新，但单次请求无法提供中间进度；前端项目级刷新为获得进度，使用 source scope 循环。

5. 增加进度条 UI
   - 在 `step === 'refreshing'` 中加入进度条。
   - 建议结构：

```html
<div class="refresh-progress" role="progressbar" :aria-valuenow="progressPercent" aria-valuemin="0" aria-valuemax="100">
  <div class="refresh-progress-bar" :style="{ width: `${progressPercent}%` }" />
</div>
<p class="progress-text">{{ progressText }}</p>
<p v-if="progress.currentTitle" class="progress-current">正在处理：{{ progress.currentTitle }}</p>
```

   - 对单个资料刷新，如果只有一个长请求，允许显示 indeterminate 样式，但不要显示虚假的百分比跳动。
   - 可在 source scope 开始时显示 `正在刷新当前资料...`，完成后显示 100%。
   - 使用设计 token，不要硬编码主题色。

6. 不要刷新完成后自动关闭弹窗
   - 当前 `handleRefresh()` 成功后 `emit('refreshed')`，父组件 `handleRefreshed()` 会关闭弹窗。
   - 修改事件语义：
     - `refreshed` 只通知父组件刷新页面数据。
     - 不由父组件立即关闭 dialog。
   - 修改 `ProjectKnowledgePage.vue` 的 `handleRefreshed()`：
     - 删除或避免 `isRefreshDialogOpen.value = false`。
     - 保留：
       - `await loadIndexStatus()`
       - 当前选中资料存在时 `await loadChunks()`
       - `void loadSources()`
   - 弹窗 `result` 状态显示完成摘要和 warnings。
   - 用户点击 `关闭` 后才触发 close。

7. 调整知识库资料编辑区为正文优先
   - 修改 `ProjectKnowledgePage.vue` 的 detail form。
   - 保留一级可见字段：
     - 标题
     - 正文
     - 保存 / 删除
   - 将以下字段移入二级菜单：
     - 类型
     - 状态
     - 可信度
     - 来源 / 原路径 / URL
     - 作者
     - 摘要
     - 标签
   - 建议使用：

```html
<details class="source-extra-fields">
  <summary>资料信息</summary>
  <div class="source-extra-grid">...</div>
</details>
```

   - `summary` 文案可用：
     - `资料信息`
     - 或 `来源、作者、标签等`
   - 对新建资料时，二级菜单可以默认打开，方便补充元信息。
   - 对编辑已有资料时，默认收起，让正文更突出。

8. 放大正文编辑区域
   - 将正文 textarea 放在标题之后、二级菜单之前或之后均可，但必须是视觉主区域。
   - 推荐顺序：
     - 标题
     - 正文
     - 资料信息 details
     - 操作按钮
   - 调整正文 textarea：
     - `rows` 从 `12` 增加到 `18` 或更多。
     - 增加 CSS：

```css
.knowledge-content-textarea {
  min-height: clamp(360px, 52vh, 720px);
}
```

   - 不要让二级菜单展开时挤压掉正文的最小高度。
   - 窄屏下仍保持可滚动和不溢出。

9. 适当调整三栏比例
   - 当前 `.knowledge-layout` 是：

```css
grid-template-columns: minmax(260px, 320px) minmax(0, 1fr) minmax(260px, 320px);
```

   - 可以微调为正文更优先的比例，例如：

```css
grid-template-columns: minmax(240px, 300px) minmax(560px, 1fr) minmax(240px, 300px);
```

   - 注意不要造成 1366 宽度下横向溢出。
   - 如果微调三栏比例风险较高，至少通过正文 textarea 的 min-height 和二级菜单收纳实现“正文更大”。

10. 统一检索 / 问答 / 摘要模块横向布局
   - 修改 `ProjectKnowledgePage.vue`。
   - 将三个非 browse 子模块包进统一 shell。
   - 示例：

```html
<section v-if="viewMode === 'search'" class="knowledge-mode-panel">
  <KnowledgeSearchPanel ... />
</section>
```

   - 或：

```html
<section v-if="viewMode !== 'browse'" class="knowledge-mode-panel">
  <KnowledgeSearchPanel v-if="viewMode === 'search'" ... />
  <KnowledgeAskPanel v-else-if="viewMode === 'ask'" ... />
  <KnowledgeSummaryPanel v-else-if="viewMode === 'summary'" ... />
</section>
```

   - CSS：

```css
.knowledge-mode-panel {
  max-width: 1480px;
  width: 100%;
  margin-right: auto;
  margin-left: auto;
  box-sizing: border-box;
}
```

   - 也可把 `.knowledge-mode-panel` 加入现有 max-width 规则组。
   - 确保 `view-back` 与子模块主体左边缘对齐。
   - 不要在 `KnowledgeSearchPanel`、`KnowledgeAskPanel`、`KnowledgeSummaryPanel` 中分别设置 viewport margin，避免三个模块后续继续分叉。

11. 子模块内部卡片可做轻微统一
   - 如发现三个组件内部 `.search-panel` 宽度仍异常，可补：

```css
.search-panel {
  width: 100%;
  box-sizing: border-box;
}
```

   - 优先在父容器解决问题；只有必要时才改三个子组件。
   - 避免把卡片放进另一个装饰性卡片中，保持当前单卡片结构。

12. 样式清理
   - 将新增样式尽量使用现有 token：
     - `--zs-space-*`
     - `--zs-color-*`
     - `--zs-radius-*`
     - `--zs-shadow-*`
   - 不要新增硬编码主题色。
   - 如果必须使用 fallback，优先确认项目是否已有对应 token；不要继续使用不存在的 `--zs-space-md`。

13. 测试与检查
   - 如已有知识库组件测试基础，可新增或补充：
     - 刷新弹窗出现进度条。
     - `scope=project` 时按资料数量更新进度。
     - 完成后弹窗保留 result，不被父组件立即关闭。
     - 页面不再出现内容贴边。
   - 如果组件测试成本高，本任务至少必须完成 type-check、unit tests、build 和手动 UI 检查。

14. 执行报告
   - 创建新的 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
   - 报告必须说明：
     - 修改了哪些文件。
     - 刷新弹窗贴边问题的原因和修复方式。
     - 进度条是如何计算进度的。
     - 是否使用 source scope 循环刷新。
     - 完成后是否保留结果页。
     - 正文区域如何变成主区域。
     - 检索/问答/摘要如何与浏览模块统一左右间距。
     - 验证命令结果。

# Constraints

1. 不要修改后端索引、RAG、AI 总结、向量检索核心逻辑。
2. 不要新增后台任务表、WebSocket、SSE 或复杂 job 系统。
3. 不要新增依赖。
4. 不要恢复作者 UI 中的 `重建分块`、`生成向量`、`向量索引`、`重建全部索引` 文案。
5. 进度条不能用误导性的假百分比；项目级刷新应基于已处理资料数计算。
6. 如果无法实现真实细粒度进度，必须在 UI 文案中说明是“按资料刷新进度”，不要暗示能看到每个片段的生成进度。
7. 不要让刷新完成后立即关闭弹窗，用户应能看到结果。
8. 不要把作者、来源、摘要等元信息删除；只是移入二级菜单。
9. 不要改变知识资料数据结构和数据库模型。
10. 不要改动知识库导入解析逻辑。
11. 不要改动写作工作区、人物、设定、伏笔、关系图等无关模块。
12. 用户可见文案必须为简体中文。
13. 不要提交本地数据库、日志、临时文件或构建产物。

# Verification Commands

前端：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit -- --run
npm run build
```

如果 Claude Code 修改了后端，则还必须运行：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
pytest tests/test_knowledge_service.py
pytest tests/test_knowledge_index_refresh_service.py
pytest tests/test_knowledge_embedding_service.py
pytest
```

手动检查：

```text
/projects/:projectId/knowledge
点击“刷新知识索引”
确认弹窗正文区域左右有合理留白，不贴边
选择“全部资料”并开始刷新
确认刷新期间出现进度条、百分比或 processed/total 文案
确认当前正在处理的资料名可见
确认刷新完成后弹窗不自动关闭，并显示完成摘要
确认 warning 能正常展示
关闭弹窗后确认索引状态和索引片段已刷新
选择一条资料，只刷新当前资料，确认进度反馈正常
在浏览模式中确认正文 textarea 占主要区域
确认作者、来源、摘要、类型、状态、可信度、标签位于二级菜单中
切换到“检索”
切换到“问答”
切换到“摘要”
确认三个子模块核心卡片左右间距与“浏览”模块统一，不贴浏览器边缘
在 1366px、900px 以下宽度分别检查无横向溢出
```

# Acceptance Criteria

1. `CODEX_PLAN.md` 已由 Codex 写入，业务代码未由 Codex 修改。
2. Claude Code 执行后，刷新知识索引弹窗正文不再左右贴边。
3. 刷新知识索引过程有可见进度条。
4. 项目级刷新进度基于已处理资料数计算。
5. 当前资料刷新至少有明确的进行中状态和完成状态。
6. 刷新完成后弹窗保留结果页，不会立即自动关闭。
7. 知识库资料编辑区以正文为主，正文 textarea 明显增大。
8. 作者、来源、摘要、类型、状态、可信度、标签等元信息进入二级菜单。
9. 元信息没有丢失，保存 payload 不变。
10. `检索`、`问答`、`摘要` 子模块与 `浏览` 子模块使用统一最大宽度和左右留白。
11. 页面在常见桌面和窄屏宽度下无横向溢出。
12. 不重新暴露“重建分块 / 生成向量 / 向量索引”等技术文案。
13. 前端 `npm run type-check` 通过。
14. 前端 `npm run test:unit -- --run` 通过。
15. 前端 `npm run build` 通过。
16. Claude Code 创建 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md` 并记录执行结果。

# Risks and Watchpoints

1. 当前 project scope 单请求无法提供中间进度；如果直接沿用单请求，只能做 spinner，不满足“直观看到进度”。建议使用 source scope 顺序刷新实现真实 source 级进度。
2. source 级顺序刷新会比 project 单请求多一些 HTTP 请求，但更容易展示进度，也更符合本地写作工具场景。
3. 父组件当前 `handleRefreshed()` 会关闭 dialog，必须改掉，否则用户看不到完成结果。
4. `listKnowledgeSources(projectId)` 获取全量资料时，不要被当前页面筛选条件影响。
5. 元信息移入 details 后，用户仍需要能发现这些字段；summary 文案要清楚。
6. 新建资料时如果 details 默认收起，用户可能忽略类型/来源/标签；建议新建时默认展开。
7. 正文 textarea 增大后要注意右侧索引片段栏和左侧列表不要被撑出布局。
8. 搜索/问答/摘要三个组件内部有重复 CSS，父容器统一后不要继续复制更多不一致样式。
9. 进度条样式必须支持护眼/黑夜主题。
10. 不要为了这次 UI 调整引入复杂后端 job 架构。

# Review Checklist

Codex 复审时应检查：

1. Claude 是否读取本计划并生成执行报告。
2. 旧交接文件是否已归档，活跃交接文件是否只代表当前任务。
3. 是否只改了知识库 UI 相关范围，没有触碰无关模块。
4. 刷新弹窗 `.refresh-body` 是否有横向 padding。
5. 是否移除了不存在 token `--zs-space-md` 等不稳定写法。
6. 是否新增进度条，并且项目级进度来自真实已处理资料数。
7. 刷新完成后弹窗是否保留 result 页面。
8. `handleRefreshed()` 是否不再立即关闭弹窗。
9. 正文 textarea 是否成为知识资料编辑主区域。
10. 作者、来源、摘要等元信息是否进入二级菜单且仍能保存。
11. 检索/问答/摘要是否有统一父容器控制最大宽度和左右留白。
12. 三个子模块是否不再贴浏览器边缘。
13. 是否没有重新出现“重建分块 / 生成向量 / 向量索引”等作者不可见技术文案。
14. 是否没有新增不必要依赖或后端复杂任务系统。
15. 验证命令是否通过。
16. 是否有不该提交的密钥、本地配置、临时文件、数据库或日志。
17. 最终建议应明确为 Accept、Minor Revision 或 Rework。
