# Task Summary

本次任务是对现有前端 UI 做一轮小范围体验优化，不实现新业务功能，不修改后端、数据库或接口。

优化范围：

- 时间轴模块：压缩左侧时间轴列表中“时间轴列表 / 轨道”标题区与“主轴”等列表项之间的过大空白。
- 写作工作区：缩窄“新建章节”和“新建分卷”按钮宽度，使其不再像整行主操作。
- 大纲模块：扩大“新建大纲条目”表单的可用宽度，并补足左右内边距，避免文本框贴边。
- 检查功能：调整“检查范围”三个单选项为横向排版；让“检查”和“词库”两个容器宽度更均衡，并让页面核心容器在竖直轴上更对称。
- 可选 UI 建议：将低频操作收纳到二级菜单，由 Claude Code 结合实际页面复杂度决定是否执行。

Codex 未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

已阅读上一轮 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`，上一任务为 SQLite FTS5 全文搜索与完整版本管理，报告显示前后端实现和测试已完成。旧交接文件已归档到：

`docs/ai-handoff/archive/2026-05-25-fts-version-management/`

本次重点阅读了相关前端文件：

- `frontend/src/pages/timeline/ProjectTimelinePage.vue`
  - 左侧栏使用 `.left-panel`、`.panel-head`、`.panel-eyebrow`、`.track-list`、`.track-item` 等结构。
  - 左侧标题区显示“时间轴列表”和“轨道”，列表项中包含“主轴”等轨道名称。
  - 当前标题区与列表区之间的视觉空白偏大，可能来自 `.left-panel` 的 grid gap、`.panel-head`、`.panel-eyebrow` 或标题默认 margin。

- `frontend/src/features/chapters/ChapterTree.vue`
  - “新建章节”和“新建分卷”按钮使用 `.tree-row.create-row`、`.child-row`、`.volume-create-row` 等样式。
  - 这些按钮继承树节点行的整行布局，视觉上按钮宽度偏大。
  - 该组件还承载章节树拖拽相关交互，缩窄按钮时不能破坏拖拽放置区域和键盘可访问性。

- `frontend/src/features/outlines/CreateOutlineDialog.vue`
  - 新建大纲条目表单直接使用全局 `.zs-dialog-content`。
  - 全局 dialog 最大宽度约为 560px，且该表单没有单独的 `.zs-dialog-body` 内层容器。
  - 表单字段较多时，当前宽度和左右间距都不够舒展。

- `frontend/src/pages/review/ReviewCheckPage.vue`
  - 页面核心区包含检查面板、词库面板和检查结果面板。
  - 检查面板和词库面板目前使用 flex 布局，视觉高度和宽度不够稳定。
  - “检查范围”使用 `.segmented-control`，当前允许换行，三个选项在某些宽度下不够横向一致。
  - 词库导入、导出等低频操作始终暴露在工具栏中，可考虑收纳到二级菜单。

- `frontend/src/features/writing/WritingAidPanel.vue`
  - 右侧辅助面板包含较多标签项，后续如出现拥挤，可考虑将低频入口放入“更多”菜单。
  - 本次不建议主动重构该组件，只在 Claude Code 实测确认拥挤时做极小范围 UI 收纳。

# Architecture Decision

本次为前端 UI 微调任务，应采用“局部 CSS / 模板小改”的方式完成。

架构决策：

- 不修改后端 API、Service、Repository、Model、Schema、数据库迁移或数据结构。
- 不新增依赖，不引入新的 UI 库。
- 不重写页面或组件，只在既有组件内做局部布局调整。
- 优先复用现有设计 token，例如 `var(--zs-space-*)`、`var(--zs-radius-*)`、`var(--zs-color-*)`。
- 对 dialog 宽度和内边距的调整应优先使用局部 class，避免修改全局 `.zs-dialog-content` 影响其他弹窗。
- 对低频操作二级菜单的调整属于可选优化，必须以“不降低可发现性、不破坏已有功能”为前提。
- 本次不应改变任何业务流程、数据保存逻辑、路由结构或 API 调用。

# Files to Create or Modify

Claude Code 预计需要修改：

- `frontend/src/pages/timeline/ProjectTimelinePage.vue`
- `frontend/src/features/chapters/ChapterTree.vue`
- `frontend/src/features/outlines/CreateOutlineDialog.vue`
- `frontend/src/pages/review/ReviewCheckPage.vue`

Claude Code 可选修改：

- `frontend/src/features/outlines/EditOutlineDialog.vue`
  - 仅当编辑大纲弹窗也存在同类贴边或宽度问题时，做一致性小调整。
- `frontend/src/features/writing/WritingAidPanel.vue`
  - 仅当右侧辅助面板标签或操作在当前断点明显拥挤时，将低频入口收纳到“更多”菜单。

不应修改：

- `backend/` 下任何文件。
- 数据库模型、迁移、初始化脚本。
- `frontend/src/router/`，除非 Claude Code 发现页面无法访问且必须修正，但本任务原则上不需要。
- `frontend/src/App.vue`。
- 依赖文件，如 `package.json`、`package-lock.json`、`pnpm-lock.yaml`。
- 构建脚本、启动脚本、测试框架配置。

# Implementation Steps for Claude Code

1. 执行前检查
   - 运行 `git status --short`，确认当前工作区状态。
   - 打开并确认以下页面/组件的最新代码：
     - `frontend/src/pages/timeline/ProjectTimelinePage.vue`
     - `frontend/src/features/chapters/ChapterTree.vue`
     - `frontend/src/features/outlines/CreateOutlineDialog.vue`
     - `frontend/src/pages/review/ReviewCheckPage.vue`

2. 时间轴模块左侧列表空白优化
   - 在 `frontend/src/pages/timeline/ProjectTimelinePage.vue` 中定位左侧列表区域：
     - `.left-panel`
     - `.panel-head`
     - `.panel-eyebrow`
     - `.track-list`
     - `.track-item` 或轨道卡片相关样式
   - 优先压缩标题区与列表区之间的垂直间距：
     - 检查 `.left-panel` 的 `gap` 是否过大。
     - 检查 `.panel-head` 是否有额外 `margin-bottom`。
     - 检查 `.panel-eyebrow`、`h2` 是否保留浏览器默认 margin。
   - 建议采用局部规则，例如：
     - `.left-panel .panel-head { margin-bottom: 0; }`
     - `.left-panel .panel-eyebrow { margin: 0 0 2px; line-height: 1.2; }`
     - `.left-panel .panel-head h2 { margin: 0; line-height: 1.25; }`
     - 适度降低 `.left-panel` 内部 gap，但不要让标题、统计、列表拥挤。
   - 如果实际问题来自“主轴”列表项内部左右元素距离过远，而不是标题与列表的距离：
     - 保持轨道名称和主轴标识视觉上成组。
     - 将低优先级操作按钮改为更紧凑的图标按钮或收纳到已有菜单。
     - 不要隐藏“主轴”这个核心信息。

3. 写作工作区新建按钮宽度优化
   - 在 `frontend/src/features/chapters/ChapterTree.vue` 中调整 `.create-row`、`.volume-create-row`、必要时 `.child-row.create-row`。
   - 目标是让“新建章节”“新建分卷”更像轻量辅助操作，而不是整行主按钮。
   - 推荐方向：
     - 将 `.create-row` 设置为内容宽度或较小固定最大宽度，如 `width: fit-content`、`justify-self: start`、更小的水平 padding。
     - 对子级新建章节按钮保留适当缩进，但避免整行铺满。
     - 对新建分卷按钮保留虚线边框或轻量样式，但降低横向占比。
   - 注意：
     - 不要破坏章节树拖拽排序、拖入分卷、未分配章节区域等已有交互。
     - 如果当前按钮同时承担拖拽放置区域，应保留足够可点击和可拖放的命中区域，或只缩窄视觉按钮而不缩窄外层放置容器。

4. 新建大纲条目表单宽度与内边距优化
   - 在 `frontend/src/features/outlines/CreateOutlineDialog.vue` 中为弹窗添加局部 class，例如：
     - `outline-create-dialog`
     - `outline-dialog-body`
   - 不要直接扩大全局 `.zs-dialog-content`。
   - 建议：
     - 将新建大纲弹窗宽度调整为 `min(720px 或 760px, calc(100vw - 32px))`。
     - 给表单主体增加明确内边距，例如复用 `.zs-dialog-body` 或局部 body class。
     - 将字段 grid 的最小列宽从约 180px 提升到 220px 或 240px，避免字段过窄。
     - 保持小屏下单列布局，不产生横向滚动。
   - 如 `EditOutlineDialog.vue` 也存在同类贴边问题，可采用同样局部 class 做一致性调整，但不要扩大范围到全部 dialog。

5. 检查功能页面布局优化
   - 在 `frontend/src/pages/review/ReviewCheckPage.vue` 中调整核心布局。
   - 将检查面板和词库面板从不稳定的 flex 体验改为更稳定的两列 grid：
     - 桌面端建议 `grid-template-columns: minmax(0, 1fr) minmax(0, 1fr)`。
     - `align-items: stretch`，使两个容器宽度一致、视觉重量更平衡。
   - 检查结果面板保持与上方两列区域同一个 `max-width` 和水平中心线。
   - 调整“检查范围”：
     - 桌面端三个选项固定横向排列，例如 `grid-template-columns: repeat(3, minmax(0, 1fr))`。
     - 每个选项内部使用 `inline-flex` 或 flex，确保 radio 与文本“当前章节 / 当前分卷 / 全书”在同一行。
     - 设置 `white-space: nowrap`，避免文本拆行。
     - 小屏端可以改为单列或允许自然换行。
   - 调整页面三个核心容器的竖直轴对称：
     - 检查面板、词库面板、检查结果面板使用一致的外层宽度、左右边距和对齐方式。
     - 不要让某个面板单独贴边或偏离页面中心线。

6. 可选 UI 交互优化，由 Claude Code 判断是否执行
   - `frontend/src/pages/review/ReviewCheckPage.vue`
     - 可将“导入词库”“导出词库”等低频操作收纳到“更多”二级菜单。
     - 常用操作如“开始检查”“添加词条”应继续直接可见。
   - `frontend/src/pages/timeline/ProjectTimelinePage.vue`
     - 如左侧轨道列表卡片操作过多，可将删除、隐藏、重命名等低频操作收纳到单个菜单。
     - 不要隐藏创建时间轴、切换轨道等主要操作。
   - `frontend/src/features/writing/WritingAidPanel.vue`
     - 如右侧辅助面板标签在常见宽度下明显拥挤，可考虑将“关系图、时间轴、伏笔、提醒、版本”等低频入口中的一部分收纳到“更多”。
     - 该项为可选建议，不应为了本任务重构右侧面板。

7. 执行后记录
   - Claude Code 应在 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md` 中说明：
     - 实际修改了哪些文件。
     - 哪些 UI 建议已采纳，哪些未采纳及原因。
     - 是否存在与计划不一致的地方。
     - 执行了哪些验证命令。
     - 手动检查了哪些页面和断点。

# Constraints

- 本任务只做 UI 布局和交互层面的微调，不实现新业务功能。
- 不修改后端，不修改数据库，不新增 API。
- 不新增依赖，不引入大型 UI 库。
- 不做全局样式大改，除非是非常小且确定不会影响其他页面的 token 级修复。
- dialog 宽度和间距优先使用局部 class，不要直接改变所有弹窗。
- 不要重写 `ProjectTimelinePage.vue`、`ChapterTree.vue`、`ReviewCheckPage.vue` 或 `WritingAidPanel.vue`。
- 不要改动无关页面。
- 用户可见 UI 文案必须使用简体中文。
- 所有改动必须保持现有功能可用，尤其是章节树拖拽、检查范围选择、词库操作和时间轴轨道切换。

# Verification Commands

建议 Claude Code 执行：

```powershell
cd frontend
npm run type-check
npm run build
```

如项目当前配置包含前端单元测试，可补充执行：

```powershell
cd frontend
npm run test:unit
```

手动视觉验证：

- 打开写作工作区页面，例如 `/projects/{projectId}`：
  - 检查“新建章节”“新建分卷”按钮宽度是否收窄。
  - 检查章节树拖拽、点击、新建入口是否仍可用。
- 打开时间轴页面，例如 `/projects/{projectId}/timeline`：
  - 检查左侧“时间轴列表 / 轨道”和“主轴”之间是否仍存在异常大空白。
  - 检查轨道切换、创建、编辑、删除操作是否仍可用。
- 打开大纲页面并触发新建大纲条目：
  - 检查表单宽度是否更舒展。
  - 检查左右内边距是否合理。
  - 检查 390px 左右移动端宽度下是否无横向滚动。
- 打开检查页面，例如 `/projects/{projectId}/review`：
  - 检查“当前章节 / 当前分卷 / 全书”是否横向排列且文本不拆行。
  - 检查“检查”和“词库”两个容器是否宽度均衡。
  - 检查检查结果区域是否与上方区域保持同一中心轴和合理左右间距。

建议检查断点：

- 1440px 桌面宽度
- 1366px 桌面宽度
- 1024px 平板或窄桌面宽度
- 390px 移动端宽度

# Acceptance Criteria

- 时间轴左侧栏标题区和轨道列表之间不再出现明显不合理空白。
- “主轴”等轨道列表项信息仍然清晰，主要操作仍可访问。
- 写作工作区“新建章节”“新建分卷”按钮明显变窄，视觉层级更轻，但点击和拖拽相关交互不受影响。
- 新建大纲条目表单宽度和左右内边距更合理，字段不贴边，小屏不横向溢出。
- 检查页面中“当前章节 / 当前分卷 / 全书”三个选项在桌面端横向排列。
- 检查面板和词库面板宽度均衡，检查结果面板与上方区域保持中心对齐。
- 可选的二级菜单优化若执行，必须保留常用操作的可见性。
- `npm run type-check` 和 `npm run build` 通过。
- 未修改任何后端、数据库、依赖或无关文件。

# Risks and Watchpoints

- 缩窄章节树新建按钮可能减少拖拽放置命中区域。若按钮当前承担放置功能，应保留外层可拖放区域。
- 修改全局 dialog 样式可能影响大量弹窗。应使用局部 class 控制新建大纲弹窗。
- 检查页面两列 grid 在窄屏可能溢出。必须添加或保留移动端断点。
- 将低频操作放入二级菜单可能降低可发现性。仅在操作区明显拥挤时执行，并保留核心操作直达入口。
- 时间轴页面样式较复杂，压缩间距时不要让左侧栏标题、统计数和轨道卡片互相贴得过近。
- 本次是视觉优化，不应顺手修改业务逻辑、接口字段或数据保存逻辑。

# Review Checklist

- [ ] Claude Code 是否只修改了计划允许的前端 UI 文件？
- [ ] 是否没有修改 `backend/`、数据库、依赖、启动脚本或无关文件？
- [ ] 时间轴左侧栏空白问题是否被实际修正？
- [ ] 写作工作区新建按钮是否收窄且不影响章节树交互？
- [ ] 新建大纲条目弹窗是否更宽、更有内边距，并保持移动端可用？
- [ ] 检查范围三个选项是否横向排列且文本不拆行？
- [ ] 检查、词库、检查结果三个核心容器是否在页面中心轴上更一致？
- [ ] 如执行二级菜单优化，是否没有隐藏高频操作？
- [ ] 是否通过 `npm run type-check`？
- [ ] 是否通过 `npm run build`？
- [ ] 是否没有引入密钥、本地配置、日志、数据库或临时文件？
- [ ] `CLAUDE_EXECUTION_REPORT.md` 是否说明实际改动、验证结果和未采纳建议？
