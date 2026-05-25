# Task Summary

规划章枢当前阶段的 UI 设计进一步优化方案。目标不是立即实现某一个单点功能，而是让 Claude Code 基于现有代码状态，分批改进界面一致性、主题适配、信息架构、交互状态和响应式体验。

本计划仅用于规划与交接。Codex 不直接修改业务代码。

# Current Codebase Findings

1. 已阅读 Claude Code 的上一份执行报告。上一任务完成了全局主题系统：
   - 新增 `frontend/src/shared/theme/appTheme.ts`
   - 新增 `frontend/src/shared/theme/ThemeSwitcher.vue`
   - 新增 `frontend/src/__tests__/app-theme.spec.ts`
   - 修改 `frontend/src/main.ts`、`frontend/src/App.vue`、`frontend/src/style.css`
   - 修改多个页面和画布组件以支持全局主题与画布中性色 token
2. 旧交接文件已按生命周期规则归档到：
   - `docs/ai-handoff/archive/2026-05-23-global-theme-system/CODEX_PLAN.md`
   - `docs/ai-handoff/archive/2026-05-23-global-theme-system/CLAUDE_EXECUTION_REPORT.md`
3. 当前 `frontend/src/App.vue` 将 `ThemeSwitcher` 固定在右上角。该方案简单可用，但可能与页面标题、返回按钮、页面操作区、移动端顶部内容发生位置冲突。
4. `frontend/src/style.css` 已有一批全局 token 和基础工具类，例如：
   - `--zs-color-*`
   - `--zs-canvas-*`
   - `.zs-card`
   - `.zs-button`
   - `.zs-tag`
   - `.zs-status`
   - `.zs-empty`
   - `.zs-toolbar`
5. 仍有不少 feature 组件保留局部硬编码颜色、局部按钮样式、局部状态提示样式，容易导致深色模式和护眼模式下观感不统一。重点文件包括：
   - `frontend/src/features/characters/ChapterCharacterPanel.vue`
   - `frontend/src/features/clues/ChapterCluePanel.vue`
   - `frontend/src/features/settings/ChapterSettingPanel.vue`
   - `frontend/src/features/outlines/ChapterOutlinePanel.vue`
   - `frontend/src/features/timeline/ChapterTimelinePanel.vue`
   - `frontend/src/features/graph/ChapterGraphCard.vue`
   - `frontend/src/features/chapters/CreateChapterDialog.vue`
   - `frontend/src/features/chapters/EditChapterDialog.vue`
   - `frontend/src/features/chapters/ChapterVersionPreviewDialog.vue`
   - `frontend/src/features/chapters/ChapterVersionPanel.vue`
   - `frontend/src/features/writing/CreativeReminderPanel.vue`
6. `frontend/src/pages/projects/ProjectsPage.vue` 已具备书籍卡片展示、标签、封面、状态等基础信息，但还缺少更高效的顶部搜索、排序和筛选入口。
7. 写作辅助侧栏中的人物、设定、伏笔、时间线、关系图等面板，在列表、详情、绑定、空状态、错误状态、按钮位置方面仍有较多局部差异。

# Architecture Decision

1. 采用“小步统一”的 UI 优化策略，不做大型页面重写，不重建前端项目，不重写 router、`App.vue` 主结构或核心写作编辑器。
2. 优先完善已有全局 design token 和共享 CSS utility，再逐步替换 feature 组件里的重复样式。
3. UI 优化分为四个批次执行：
   - Batch 1: 全局主题入口与共享 UI utility
   - Batch 2: 写作辅助侧栏 feature 面板的主题一致性
   - Batch 3: 项目页 `/projects` 的检索、筛选、排序和卡片信息密度
   - Batch 4: 响应式、可访问性、状态反馈和视觉 QA
4. Canvas、关系图、时间线画布继续使用 `--zs-canvas-*` token，不随黑夜模式或护眼模式改变为强主题背景，避免影响图形识别。
5. 不新增大型 UI 库。若需要图标，优先复用项目已有方式；若项目尚未引入图标库，本轮不新增依赖。

# Files to Create or Modify

建议 Claude Code 只在前端范围内修改以下文件。若执行时发现实际结构不同，应先记录到执行报告，再按最小范围调整。

1. 全局样式与主题入口：
   - 修改 `frontend/src/App.vue`
   - 修改 `frontend/src/style.css`
   - 可选新增 `frontend/src/shared/theme/ThemeUtilityBar.vue`
2. 写作辅助侧栏与 feature 面板：
   - 修改 `frontend/src/features/characters/ChapterCharacterPanel.vue`
   - 修改 `frontend/src/features/clues/ChapterCluePanel.vue`
   - 修改 `frontend/src/features/settings/ChapterSettingPanel.vue`
   - 修改 `frontend/src/features/outlines/ChapterOutlinePanel.vue`
   - 修改 `frontend/src/features/timeline/ChapterTimelinePanel.vue`
   - 修改 `frontend/src/features/graph/ChapterGraphCard.vue`
   - 修改 `frontend/src/features/writing/CreativeReminderPanel.vue`
3. 章节弹窗和版本面板：
   - 修改 `frontend/src/features/chapters/CreateChapterDialog.vue`
   - 修改 `frontend/src/features/chapters/EditChapterDialog.vue`
   - 修改 `frontend/src/features/chapters/ChapterVersionPreviewDialog.vue`
   - 修改 `frontend/src/features/chapters/ChapterVersionPanel.vue`
4. 项目页：
   - 修改 `frontend/src/pages/projects/ProjectsPage.vue`
   - 可选新增 `frontend/src/features/projects/projectFilters.ts`
   - 可选新增或修改对应单元测试，例如 `frontend/src/__tests__/project-filters.spec.ts`
5. 交接文件：
   - 修改 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`

# Implementation Steps for Claude Code

1. 执行前检查
   - 读取本计划。
   - 查看当前 `git status --short`，确认是否存在与本任务无关的未提交改动。
   - 不要修改 `docs/ai-handoff/archive/` 下的历史文件。

2. Batch 1: 优化全局主题入口与共享 UI utility
   - 检查 `frontend/src/App.vue` 中的 `ThemeSwitcher` 固定定位是否会覆盖页面内容。
   - 可选新增 `frontend/src/shared/theme/ThemeUtilityBar.vue`，内部复用 `ThemeSwitcher`。
   - 将右上角固定入口调整为更稳定的全局工具条：
     - 桌面端固定在右上角，但预留与页面 header 的距离。
     - 移动端避免覆盖返回按钮、标题和主要操作按钮。
     - 保持 `aria-label` 和键盘可访问。
   - 在 `frontend/src/style.css` 中补充共享 UI utility：
     - `.zs-button-danger`
     - `.zs-alert`
     - `.zs-alert-error`
     - `.zs-alert-success`
     - `.zs-alert-warning`
     - `.zs-page-header`
     - `.zs-page-actions`
     - `.zs-back-link`
     - `.zs-dialog`
     - `.zs-dialog-header`
     - `.zs-dialog-body`
     - `.zs-dialog-footer`
     - `.zs-field`
     - `.zs-filter-button`
     - `.zs-filter-menu`
   - 这些类应基于现有 `--zs-color-*` token，不引入新的主色体系。

3. Batch 2: 清理写作辅助侧栏和 feature 面板的主题不一致
   - 优先处理以下文件中的硬编码颜色、重复按钮样式和状态提示：
     - `ChapterCharacterPanel.vue`
     - `ChapterCluePanel.vue`
     - `ChapterSettingPanel.vue`
     - `ChapterOutlinePanel.vue`
     - `ChapterTimelinePanel.vue`
     - `ChapterGraphCard.vue`
     - `CreativeReminderPanel.vue`
   - 替换方向：
     - 局部 `.primary-button` 替换为 `.zs-button .zs-button-primary`
     - 局部 `.secondary-button` 替换为 `.zs-button .zs-button-secondary`
     - 危险操作使用 `.zs-button .zs-button-danger`
     - 错误、成功、警告、空状态使用 `.zs-alert-*` 或 `.zs-empty`
     - 卡片、详情块、列表项背景使用 `--zs-color-surface`、`--zs-color-surface-muted`、`--zs-color-border`
   - 不要在这一批重写业务逻辑、API 调用或数据结构。
   - 保持原有交互流程和组件 props/emits 不变，除非局部样式整理必须轻微调整模板 class。

4. Batch 3: 优化 `/projects` 书籍页面的信息检索与卡片密度
   - 在 `frontend/src/pages/projects/ProjectsPage.vue` 顶部增加搜索输入，搜索范围建议包括：
     - 书名
     - 作者
     - 简介
     - 标签
   - 增加一个筛选按钮，点击后显示二级菜单或浮层，避免把所有筛选条件直接铺在页面顶部。
   - 筛选条件建议包括：
     - 写作状态
     - 标签
     - 是否有封面
   - 增加排序控件，建议支持：
     - 最近更新
     - 创建时间
     - 书名
     - 作者
   - 若筛选和排序逻辑超过页面内简单表达，抽出到 `frontend/src/features/projects/projectFilters.ts`，并添加单元测试。
   - 优化书籍卡片：
     - 保持封面、书名、作者、简介、标签为主信息。
     - 次要属性使用紧凑 meta 行，不要让卡片过度膨胀。
     - 空封面继续使用默认封面或默认占位。

5. Batch 4: 统一章节弹窗、版本面板和状态反馈
   - 在以下文件中复用 `.zs-dialog-*`、`.zs-field`、`.zs-alert-*`：
     - `CreateChapterDialog.vue`
     - `EditChapterDialog.vue`
     - `ChapterVersionPreviewDialog.vue`
     - `ChapterVersionPanel.vue`
   - 检查弹窗在深色模式和护眼模式下的输入框、边框、遮罩、按钮状态。
   - 保持弹窗业务逻辑不变。

6. Batch 5: 响应式和可访问性修正
   - 检查移动端宽度下：
     - 全局主题入口不遮挡返回按钮和页面主操作。
     - 页面标题、返回按钮、操作按钮不会换行重叠。
     - 项目卡片、辅助面板、筛选菜单没有水平溢出。
   - 为筛选菜单补充必要的：
     - `aria-expanded`
     - `aria-controls`
     - Escape 关闭
     - 点击外部关闭
   - 确保按钮和链接有可见 focus 样式。
   - 若存在动画，遵守已有 `prefers-reduced-motion` 规则。

7. 执行完成后写报告
   - 将执行过程、修改文件、验证结果、未完成项写入：
     - `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`
   - 报告中必须单独列出：
     - 哪些 UI 建议已采纳
     - 哪些 UI 建议未采纳及原因
     - 是否发现额外风险

# Constraints

1. 不要修改后端代码，除非执行过程中发现前端已有接口数据无法支持页面现有功能，且必须先写入执行报告等待确认。
2. 不要重建 Vue 项目。
3. 不要重写 router、`ProjectDetailPage`、`ChapterTree`、`ChapterEditor`、`WritingAidPanel`。
4. 不要引入大型 UI 库。
5. 不要为了 UI 统一进行大规模重构。
6. 不要改动与 UI 优化无关的文件。
7. 不要改变现有 API 路径、数据字段含义或数据库结构。
8. 所有用户可见文案必须使用简体中文。
9. Canvas、关系图、时间线画布区域继续使用 `--zs-canvas-*`，不要被全局主题背景直接覆盖。
10. 如果存在用户未提交改动，必须保护这些改动，不能回滚。

# Verification Commands

在 `F:\zhangshu\frontend` 下执行：

```powershell
npm run type-check
npm run test:unit
npm run build
```

辅助检查硬编码颜色，结果用于执行报告，不要求完全清零：

```powershell
rg -n "#[0-9a-fA-F]{3,8}|rgb\(|rgba\(" src/pages src/features src/shared
```

建议人工或浏览器检查以下页面和状态：

```text
/projects
/projects/:projectId
/projects/:projectId/characters
/projects/:projectId/settings
/projects/:projectId/clues
/projects/:projectId/timeline
/projects/:projectId/graph
写作编辑页面及右侧 WritingAidPanel
章节创建、编辑、版本预览弹窗
```

主题检查矩阵：

```text
默认主题
护眼主题
黑夜主题
桌面宽度 1440px
笔记本宽度 1280px
移动宽度 390px
```

# Acceptance Criteria

1. 全局主题入口不再明显遮挡页面标题、返回按钮或主要操作按钮。
2. 护眼和黑夜模式下，主要页面、feature 面板、弹窗、状态提示的颜色表现一致。
3. Canvas、关系图和时间线画布保持中性画布风格，不被深色模式或护眼模式错误染色。
4. 写作辅助侧栏中人物、设定、伏笔、时间线、关系图等面板的按钮、卡片、空状态、错误状态样式明显统一。
5. `/projects` 页面具备顶部搜索、筛选按钮和排序入口，且交互不拥挤。
6. 搜索、筛选、排序不改变原始项目数据，不影响项目打开、创建、编辑、删除等已有功能。
7. 移动端没有明显遮挡、重叠、水平溢出。
8. 所有新增或调整的用户可见文案均为简体中文。
9. `npm run type-check`、`npm run test:unit`、`npm run build` 均通过。
10. `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md` 完整记录执行范围、验证结果和未采纳建议。

# Risks and Watchpoints

1. `App.vue` 中全局固定主题入口如果处理不当，可能继续覆盖页面局部按钮。
2. 批量替换局部样式时，容易误改组件结构或破坏点击事件绑定。
3. 项目页筛选菜单如果直接写在页面中，可能让 `ProjectsPage.vue` 继续膨胀。逻辑复杂时应抽出纯函数。
4. 深色模式下浏览器原生 input、select、textarea 的默认样式可能与项目 token 不一致，需要人工检查。
5. 画布类组件应只使用 `--zs-canvas-*`，不要混用普通页面 surface token。
6. 不要将 UI 改进扩展成业务功能改造，例如新增后端字段、改变书籍模型或重写项目 API。
7. 右侧写作辅助面板空间较窄，新增按钮或状态文案时必须检查文本换行和溢出。

# Review Checklist

Codex 复审时应检查：

1. 是否严格按本计划执行，没有修改无关业务代码。
2. 是否遵守 `AGENTS.md` 中前端约束。
3. 是否保持 UI、业务逻辑、数据访问、AI 调用边界清晰。
4. 是否存在未说明的新依赖。
5. 是否存在不必要的大规模重构。
6. 是否保留已有 Project、Chapter、Character、Setting、Clue、Timeline、Graph 等功能。
7. 是否存在 hardcoded color 导致主题不一致的明显遗漏。
8. `/projects` 的搜索、筛选、排序是否只影响展示，不破坏原始数据。
9. 响应式布局下是否有遮挡、重叠、水平滚动。
10. 是否有不该提交的密钥、本地配置、临时文件、数据库或日志。
11. 验证命令是否通过，失败项是否在 Claude 执行报告中说明。
12. 最终建议应明确为 Accept、Minor Revision 或 Rework。
