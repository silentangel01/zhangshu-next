# Task Summary

规划修正知识库模块当前 UI 问题：新建资料入口不够清楚、页面组件间空白过大、全局主题在知识库页面仅部分生效。Codex 本轮只写计划，不修改业务代码。本计划交由 Claude Code 执行。

# Current Codebase Findings

1. 已阅读当前 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`，但该文件只有占位内容：
   - `等待 Claude Code 执行下一个任务后生成执行报告。`
   - 这与当前代码中已经存在知识库页面、知识库 API、向量检索、RAG 问答、摘要等实现不一致。
   - Claude Code 执行本计划后，必须补写真实执行报告。
2. 旧活跃交接文件已归档到：
   - `docs/ai-handoff/archive/2026-05-24-knowledge-stage-placeholder/CODEX_PLAN.md`
   - `docs/ai-handoff/archive/2026-05-24-knowledge-stage-placeholder/CLAUDE_EXECUTION_REPORT.md`
3. 当前知识库页面已经存在：
   - `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`
   - 路由：`/projects/:projectId/knowledge`
   - 项目详情入口：`frontend/src/pages/projects/ProjectDetailPage.vue` 已有“知识库”入口。
4. 当前 `ProjectKnowledgePage.vue` 有 `handleNewSource()`，模板 header 中也有“新建资料”按钮，但用户反馈“不明显或像是少了新建资料按钮”。原因可能是：
   - 新建入口只在页面 header 右侧，距离列表和空状态较远。
   - 进入检索、问答、摘要视图后，用户注意力在工具面板，新建入口不在当前操作区域。
   - 空状态虽然提示“点击新建资料”，但没有就地按钮。
   - 列表面板顶部没有“新建资料”按钮，资料管理页的主操作不够贴近列表。
5. 当前知识库页面存在较多空白和松散布局：
   - `.knowledge-page` 使用 `gap: 14px; padding: 20px;`
   - `.knowledge-layout` 使用 `grid-template-columns: 260px 1fr 300px; gap: 14px; min-height: 500px;`
   - `.list-panel`、`.detail-panel`、`.right-panel` 使用 `max-height: calc(100vh - 260px)`，在顶部工具区高度变化时可能造成可用区域计算不稳定。
   - 空详情区 `.empty-detail` 以 `height: 100%` 居中，容易产生大面积空白。
   - 检索、问答、摘要子面板各自有独立 padding/gap，和主页面布局节奏不完全一致。
6. 当前主题问题明确存在：
   - `ProjectKnowledgePage.vue` 中 `.knowledge-page` 使用 `background: var(--zs-canvas-bg, var(--zs-color-bg));`
   - `--zs-canvas-bg` 按全局主题规则是画布专用 token，不应作为普通页面背景，因此知识库页不会完全跟随护眼/黑夜主题。
   - 文件中仍有 `var(..., #hex)` fallback，例如 success、badge、shadow 等，可能导致主题表现不一致。
   - `KnowledgeImportDialog.vue` 也存在 success fallback。
   - `KnowledgeAskPanel.vue` 和 `KnowledgeSummaryPanel.vue` 使用警告符号文案，但需要确认颜色和提示样式是否基于主题 token。

# Architecture Decision

1. 本次只做知识库前端 UI 修正，不改后端业务逻辑、数据库、RAG、向量检索或导入功能。
2. 新建资料入口应遵循“主操作就近可见”原则：
   - 页面 header 保留主按钮。
   - 列表面板或空状态增加就近按钮。
   - 在检索/问答/摘要视图中保留清晰的“返回浏览 / 新建资料”路径。
3. 知识库是完整资料页，应采用资料页布局，而不是画布页布局：
   - 普通页面背景使用 `--zs-color-bg`。
   - 面板背景使用 `--zs-color-surface`。
   - 不使用 `--zs-canvas-*`。
4. 减少空白的目标不是压缩到拥挤，而是让资料列表、详情表单、分块/关联区更像工作台：
   - 顶部区域更紧凑。
   - 列表与详情区域高度统一。
   - 空状态就地提供操作。
   - 三栏间距和面板内距回归全局 spacing token。
5. 尽量复用已有全局 utility：
   - `.zs-button`
   - `.zs-button-primary`
   - `.zs-button-secondary`
   - `.zs-button-ghost`
   - `.zs-alert-*`
   - `.zs-state`
   - `.zs-card`
   - `.zs-field`

# Files to Create or Modify

Claude Code 建议只修改以下文件：

1. 知识库主页面：
   - `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`
2. 知识库子面板样式一致性：
   - `frontend/src/features/knowledge/KnowledgeSearchPanel.vue`
   - `frontend/src/features/knowledge/KnowledgeAskPanel.vue`
   - `frontend/src/features/knowledge/KnowledgeSummaryPanel.vue`
   - `frontend/src/features/knowledge/KnowledgeImportDialog.vue`
3. 如需补充共享 token 或 utility，允许小范围修改：
   - `frontend/src/style.css`
4. 如果修改涉及测试纯函数或组件行为，允许新增或修改：
   - `frontend/src/__tests__/knowledge*.spec.ts`
5. 执行完成后必须创建：
   - `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`

不得修改后端文件，除非执行中发现前端无法调用现有 API 完成“新建资料”入口显示；若出现这种情况，应停止并写入报告，不要直接扩大范围。

# Implementation Steps for Claude Code

1. 执行前检查
   - 阅读本计划。
   - 执行 `git status --short` 并记录当前工作区状态。
   - 确认本任务只处理知识库 UI，不处理 RAG/向量功能逻辑。

2. 修正新建资料入口
   - 在 `ProjectKnowledgePage.vue` 保留 header 右侧“新建资料”按钮。
   - 在左侧资料列表面板顶部新增一个轻量操作条，例如：
     - 标题：`资料`
     - 右侧按钮：`新建`
   - 该按钮调用现有 `handleNewSource()`。
   - 在空状态中新增明确按钮：
     - 文案：`新建第一条资料`
     - 点击调用 `handleNewSource()`。
   - 当 `viewMode !== 'browse'` 时，在工具面板区域提供清晰返回路径：
     - 保留顶部模式切换。
     - 可选增加一个次级按钮：`返回资料列表`，点击设置 `viewMode = 'browse'`。
   - 确认点击新建后：
     - `isCreating = true`
     - `selectedSource = null`
     - 详情区显示“新建知识资料”表单。
     - 移动端不会因为表单在下方导致用户误以为没有反应。必要时可在新建后滚动到详情区，但不要引入复杂滚动逻辑。

3. 收紧页面布局空白
   - 将 `.knowledge-page` 改为普通页面布局：
     - 背景使用 `var(--zs-color-bg)`。
     - padding 建议使用 `var(--zs-space-5)` 或响应式值。
     - gap 使用 `var(--zs-space-3)`。
   - 调整 `.page-header`：
     - 减少 header 下方空白。
     - 保持返回、标题、说明和操作区清晰。
     - 移动端操作按钮允许换行。
   - 调整 `.knowledge-toolbar`：
     - 使用更稳定的一行/换行布局。
     - 视图切换、搜索、筛选之间间距减少到 `var(--zs-space-2)` 或 `var(--zs-space-3)`。
   - 调整 `.knowledge-layout`：
     - 建议使用 `grid-template-columns: minmax(220px, 280px) minmax(420px, 1fr) minmax(260px, 320px);`
     - gap 使用 `var(--zs-space-3)`。
     - 不要固定 `min-height: 500px`，改用 `min-height: 0` 和容器高度约束。
   - 调整三个面板：
     - `.list-panel`、`.detail-panel`、`.right-panel` 统一 padding、border、background。
     - max-height 计算避免依赖过大的 `260px` 魔法数字。
     - 可改为 `max-height: calc(100vh - 220px)` 或使用页面局部滚动容器；具体以实际视觉为准。
   - 调整空状态：
     - `.empty-detail` 不要占据大量空白只显示一句话。
     - 改为紧凑空状态卡，包含说明和新建按钮。

4. 修正主题 token
   - 在 `ProjectKnowledgePage.vue` 中移除普通页面对 `--zs-canvas-bg` 的使用：
     - `background: var(--zs-color-bg);`
   - 检查知识库相关文件中所有 `var(..., #hex)` fallback：
     - 能改为已有 token 的，去掉 fallback。
     - 不存在 token 的，优先使用已有 `--zs-color-*`，不要新增无必要 token。
   - 重点处理：
     - success banner
     - status/credibility badge
     - filter panel shadow
     - import dialog success message
   - 画布 token 只允许保留在关系图、时间线等画布组件中，知识库页面不得使用。

5. 统一知识库子面板视觉
   - `KnowledgeSearchPanel.vue`、`KnowledgeAskPanel.vue`、`KnowledgeSummaryPanel.vue` 应和主页面共享同样的按钮、表单、状态提示风格。
   - 优先复用 `.zs-button`、`.zs-field`、`.zs-alert-*`、`.zs-state`。
   - AI 提示文案建议去掉符号依赖，改为纯文本加 warning 样式：
     - `AI 回答仅供参考，不会自动修改任何内容。`
     - `AI 摘要为草稿建议，不会自动写入设定或正文。`
   - 不要改变问答、检索、摘要的 API 调用逻辑。

6. 响应式检查
   - 390px：
     - header 操作按钮不遮挡。
     - 新建资料入口可见。
     - 列表、详情、右侧分块按单列堆叠。
   - 768px：
     - 左列表和详情可读。
     - 右侧分块/关联移动到下方。
   - 1280px：
     - 三栏布局不出现过大空白。
   - 1440px：
     - 页面不显得松散，详情表单和右侧面板信息密度合理。

7. 执行后报告
   - 创建 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
   - 报告必须包括：
     - 当前执行前的报告为何是占位。
     - 实际修改文件。
     - 新建资料入口如何调整。
     - 空白区域如何收紧。
     - 主题 token 如何修正。
     - 验证命令和结果。
     - 未采纳建议及原因。

# Constraints

1. 不要修改后端业务代码。
2. 不要修改知识库 RAG、向量索引、embedding、导入解析等功能逻辑。
3. 不要新增依赖。
4. 不要重写整个知识库页面，只做定向 UI 修正。
5. 不要使用 `--zs-canvas-*` 作为知识库普通页面背景。
6. 不要把知识库页面改成营销式首页，应保持资料管理工具界面。
7. 不要破坏现有新建、编辑、删除、导入、分块、关联、检索、问答、摘要入口。
8. 用户可见文案必须是简体中文。
9. 如果发现当前实现超出原知识库阶段计划，例如已实现 RAG/向量，应只在报告中记录，不在本任务中回滚或重构。

# Verification Commands

前端验证：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit -- --run
npm run build
```

辅助检查知识库页面硬编码颜色和 canvas token：

```powershell
cd F:\zhangshu\frontend
rg -n "--zs-canvas|#[0-9a-fA-F]{3,8}|rgb\(|rgba\(" src/pages/knowledge src/features/knowledge
```

手动检查：

```text
/projects/:projectId/knowledge
默认主题 / 护眼主题 / 黑夜主题
390px / 768px / 1280px / 1440px
浏览视图：新建资料入口是否清楚
空列表：是否有“新建第一条资料”
检索/问答/摘要视图：是否能清楚回到资料列表或新建资料
新建表单：点击新建后是否立即可见
导入弹窗：主题是否完整生效
```

# Acceptance Criteria

1. 用户在知识库页面能明确看到“新建资料”入口。
2. 空状态中有就地新建按钮。
3. 左侧资料列表区域有就近的新建操作。
4. 点击新建资料后，新建表单明确出现。
5. 知识库页面不再使用 `--zs-canvas-bg` 作为页面背景。
6. 默认、护眼、黑夜主题下，知识库页面背景、面板、输入框、状态提示、badge 均随主题一致变化。
7. 页面组件间空白明显收紧，三栏布局不松散。
8. 390px、768px、1280px、1440px 下无明显遮挡、横向溢出或大面积无意义空白。
9. 现有知识库功能入口不被破坏。
10. `npm run type-check`、`npm run test:unit -- --run`、`npm run build` 通过。
11. `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md` 真实记录执行结果，不再是占位文件。

# Risks and Watchpoints

1. 当前代码已包含 RAG/向量/AI 摘要相关实现，明显超过之前阶段计划；本任务不要回滚，只修 UI，并在报告中记录。
2. 新建资料按钮实际存在但不够清楚，修正重点是可发现性，不是新增第二套创建逻辑。
3. 主题问题的根因之一是误用了 canvas token，必须避免把普通页面继续接到 `--zs-canvas-*`。
4. 收紧空白时不要压缩正文 textarea 到难以编辑。
5. 右侧分块/关联面板内容可能很长，必须保留局部滚动。
6. 子面板样式如果各自 scoped 过多，可能仍有局部主题遗漏；执行报告需列出剩余项。

# Review Checklist

Codex 复审时应检查：

1. 是否只修改知识库前端 UI 和交接报告。
2. 是否没有修改后端业务逻辑、RAG、向量、导入解析。
3. 是否补写真实 `CLAUDE_EXECUTION_REPORT.md`。
4. 新建资料入口是否在 header、列表区或空状态中足够清楚。
5. 空状态是否有就地新建按钮。
6. 页面是否仍能创建、编辑、删除知识资料。
7. 是否移除了知识库普通页面对 `--zs-canvas-*` 的使用。
8. 护眼和黑夜主题是否完整生效。
9. 是否减少了无意义空白，同时保持资料编辑可读性。
10. 是否存在硬编码颜色 fallback 导致主题不一致。
11. 响应式布局是否无明显重叠、遮挡、横向溢出。
12. 验证命令是否通过。
13. 是否有不该提交的密钥、本地配置、临时文件、数据库或日志。
14. 最终建议应明确为 Accept、Minor Revision 或 Rework。
