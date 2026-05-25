# Task Summary

规划章枢下一阶段 UI 设计优化。上一轮 Claude Code 已完成全局主题、部分共享 utility、`/projects` 搜索筛选排序、若干 feature 面板和弹窗的第一批主题统一。本轮不新增业务功能，重点继续提升界面一致性、页面信息架构、状态反馈、响应式和可访问性。

Codex 本轮只规划，不修改业务代码。本计划交由 Claude Code 执行。

# Current Codebase Findings

1. 已阅读 Claude Code 最新执行报告：
   - 任务名称为 `UI Progressive Unification`。
   - 已完成全局主题入口、共享 UI utility、写作辅助侧栏部分面板颜色清理、`/projects` 搜索筛选排序、章节弹窗和版本面板样式统一。
   - 验证结果为 `npm run type-check`、`npm run test:unit -- --run`、`npm run build` 均通过。
2. 已按交接文件生命周期规则归档旧活跃文件：
   - `docs/ai-handoff/archive/2026-05-23-ui-progressive-unification/CODEX_PLAN.md`
   - `docs/ai-handoff/archive/2026-05-23-ui-progressive-unification/CLAUDE_EXECUTION_REPORT.md`
3. 当前全局样式 `frontend/src/style.css` 已有：
   - 全局主题 token：`--zs-color-*`
   - 状态 token：`--zs-color-success-*`、`--zs-color-warning-*`、`--zs-color-danger-*`、`--zs-color-info-*`
   - 画布 token：`--zs-canvas-*`
   - 基础 utility：`.zs-card`、`.zs-button`、`.zs-alert-*`、`.zs-dialog-*`、`.zs-field-*`、`.zs-filter-*`、`.zs-page-header`、`.zs-page-actions`、`.zs-back-link`
4. 当前 `frontend/src/App.vue` 仍将 `ThemeSwitcher` 固定在页面右上角，移动端固定到右下角。该方案可用，但仍属于浮动控件，后续若页面操作继续增多，容易与页面主操作、回到顶部、浮动菜单等控件竞争空间。
5. 通过硬编码颜色检查，仍有较多未统一区域，主要集中在：
   - `frontend/src/pages/characters/ProjectCharactersPage.vue`
   - `frontend/src/pages/settings/ProjectSettingsPage.vue`
   - `frontend/src/pages/clues/ProjectCluesPage.vue`
   - `frontend/src/pages/outlines/ProjectOutlinePage.vue`
   - `frontend/src/pages/projects/ProjectDetailPage.vue`
   - `frontend/src/features/projects/CreateProjectDialog.vue`
   - `frontend/src/features/projects/EditProjectDialog.vue`
   - `frontend/src/features/projects/ProjectCoverUploader.vue`
   - `frontend/src/features/projects/ProjectTagInput.vue`
   - `frontend/src/features/volumes/CreateVolumeDialog.vue`
   - `frontend/src/features/volumes/EditVolumeDialog.vue`
   - `frontend/src/features/outlines/CreateOutlineDialog.vue`
   - `frontend/src/features/outlines/EditOutlineDialog.vue`
   - `frontend/src/features/outlines/ChapterOutlineNode.vue`
   - `frontend/src/features/writing/ChapterContextSection.vue`
   - `frontend/src/features/writing/ChapterContextSummary.vue`
6. `ProjectsPage.vue` 已有顶部搜索、筛选、排序，但模板中仍保留局部按钮类、局部空状态和局部筛选菜单样式。可以继续迁移到共享 utility，但不应改变现有搜索筛选排序逻辑。
7. 项目详情、人物、设定、伏笔、大纲等页面在布局上有相似管理后台属性，但页面 header、返回按钮、状态提示、列表卡片、详情区、表单弹窗的视觉规则还没有完全统一。

# Architecture Decision

1. 本轮 UI 优化定位为“设计系统第二轮收敛”，不做业务功能扩展，不改数据库，不改后端 API。
2. 优先消化上一轮执行报告中的遗留问题：
   - 剩余硬编码颜色 token 化。
   - 新增 utility 的实际采用率提升。
   - 页面级状态提示、弹窗、表单控件一致性。
3. 不建议一口气重写所有页面。按“高复用、高可见、高风险低”的顺序执行：
   - 第一优先级：共享 token 和 utility 补齐。
   - 第二优先级：项目、卷、大纲相关弹窗统一。
   - 第三优先级：项目详情、人物、设定、伏笔、大纲页面的页面级样式统一。
   - 第四优先级：写作上下文和侧栏内部组件的视觉一致性。
4. 页面应继续保持“写作工具”而不是“营销站点”的气质：信息密度适中、层级清晰、操作位置稳定、视觉装饰克制。
5. Canvas、关系图和时间线画布继续使用 `--zs-canvas-*`，不要随全局主题改变为普通页面背景。

# Files to Create or Modify

建议 Claude Code 修改以下文件。若执行时发现实际代码与计划冲突，应停止并写入执行报告，不要强行扩大范围。

1. 全局样式：
   - 修改 `frontend/src/style.css`
2. 全局主题入口：
   - 可选修改 `frontend/src/App.vue`
   - 可选新增 `frontend/src/shared/theme/ThemeUtilityBar.vue`
3. 项目页和项目组件：
   - 修改 `frontend/src/pages/projects/ProjectsPage.vue`
   - 修改 `frontend/src/pages/projects/ProjectDetailPage.vue`
   - 修改 `frontend/src/features/projects/CreateProjectDialog.vue`
   - 修改 `frontend/src/features/projects/EditProjectDialog.vue`
   - 修改 `frontend/src/features/projects/ProjectCoverUploader.vue`
   - 修改 `frontend/src/features/projects/ProjectTagInput.vue`
4. 卷、章节、大纲相关组件：
   - 修改 `frontend/src/features/volumes/CreateVolumeDialog.vue`
   - 修改 `frontend/src/features/volumes/EditVolumeDialog.vue`
   - 修改 `frontend/src/features/outlines/CreateOutlineDialog.vue`
   - 修改 `frontend/src/features/outlines/EditOutlineDialog.vue`
   - 修改 `frontend/src/features/outlines/ChapterOutlineNode.vue`
   - 修改 `frontend/src/pages/outlines/ProjectOutlinePage.vue`
5. 资料管理页面：
   - 修改 `frontend/src/pages/characters/ProjectCharactersPage.vue`
   - 修改 `frontend/src/pages/settings/ProjectSettingsPage.vue`
   - 修改 `frontend/src/pages/clues/ProjectCluesPage.vue`
6. 写作上下文组件：
   - 修改 `frontend/src/features/writing/ChapterContextSection.vue`
   - 修改 `frontend/src/features/writing/ChapterContextSummary.vue`
7. 测试与交接：
   - 仅在需要验证纯函数或交互辅助函数时修改 `frontend/src/__tests__/`
   - 创建 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`

# Implementation Steps for Claude Code

1. 执行前检查
   - 阅读本计划。
   - 执行 `git status --short`，记录当前工作区状态。
   - 不要读取或修改 `docs/ai-handoff/archive/` 下的历史计划，除非用户另行要求历史对比。
   - 不要修改后端文件、数据库文件、启动脚本、依赖文件。

2. 补齐全局 UI token 和 utility
   - 检查 `frontend/src/style.css` 中是否缺少以下可复用 token：
     - `--zs-color-backdrop`
     - `--zs-shadow-dialog`
     - `--zs-shadow-card-hover`
     - `--zs-focus-ring`
     - `--zs-color-overlay-text`
   - 若缺少，基于现有色彩系统补充，不新增新的视觉主色。
   - 将 `rgb(20 24 31 / 54%)`、`rgb(20 24 31 / 22%)`、`rgb(37 99 235 / 15%)` 等重复值抽象为 token。
   - 补充或确认以下 utility：
     - `.zs-button-ghost`
     - `.zs-icon-button`
     - `.zs-state`
     - `.zs-state-compact`
     - `.zs-meta`
     - `.zs-form-grid`
     - `.zs-overlay`
     - `.zs-menu`
     - `.zs-menu-item`
   - 这些 utility 只负责视觉和布局，不承载业务逻辑。

3. 提升共享 utility 的采用率
   - 在以下组件中优先替换局部重复样式：
     - `CreateProjectDialog.vue`
     - `EditProjectDialog.vue`
     - `CreateVolumeDialog.vue`
     - `EditVolumeDialog.vue`
     - `CreateOutlineDialog.vue`
     - `EditOutlineDialog.vue`
   - 替换方向：
     - 弹窗遮罩使用 `.zs-dialog` 或新的 `.zs-overlay`
     - 弹窗主体使用 `.zs-dialog-content`
     - 表单字段使用 `.zs-field`
     - 主按钮使用 `.zs-button .zs-button-primary`
     - 次按钮使用 `.zs-button .zs-button-secondary`
     - 关闭按钮使用 `.zs-icon-button`
     - 错误信息使用 `.zs-alert .zs-alert-error` 或轻量字段错误 token
   - 不改变 emits、props、表单字段、提交逻辑。

4. 清理项目相关组件的主题适配问题
   - 在 `ProjectCoverUploader.vue` 中：
     - 上传区域背景、边框、错误态改为 token。
     - 封面图片上的覆盖层保留半透明效果，但颜色来源改为 token 或明确注释为覆盖层视觉。
     - 确保默认封面、上传封面、删除封面的按钮状态清晰。
   - 在 `ProjectTagInput.vue` 中：
     - 标签 chip 使用 `.zs-tag` 或统一 token。
     - 建议标签、已选标签、输入框 focus 状态在三种主题下保持可读。
   - 在 `ProjectsPage.vue` 中：
     - 保留现有搜索、筛选、排序逻辑。
     - 将局部 `.primary-button`、`.secondary-button`、`.danger-button`、`.empty-state`、`.error-banner` 尽量迁移为共享 utility。
     - 给筛选按钮补充 `aria-expanded`，筛选面板补充稳定 id 或 `aria-controls`。
     - 可选补充 Escape 关闭筛选面板和点击外部关闭，但如果实现会明显增加复杂度，可以只在执行报告中说明暂不采纳。

5. 统一页面级管理视图
   - 对以下页面做页面级视觉收敛：
     - `ProjectDetailPage.vue`
     - `ProjectCharactersPage.vue`
     - `ProjectSettingsPage.vue`
     - `ProjectCluesPage.vue`
     - `ProjectOutlinePage.vue`
   - 统一方向：
     - 页面 header 使用相同的标题、副标题、返回按钮、操作按钮布局。
     - 错误、成功、空状态统一使用 `.zs-alert-*` 或 `.zs-state`。
     - 列表卡片统一使用 `.zs-card` 或同等 token。
     - 表单输入、select、textarea 统一 focus 样式。
     - 状态 badge 和类型 tag 使用 `.zs-status`、`.zs-tag` 或同等 token。
   - 不改变已有页面的数据加载、保存、删除、拖拽、树形结构、筛选逻辑。

6. 优化写作上下文与大纲节点视觉
   - 在 `ChapterContextSection.vue`、`ChapterContextSummary.vue` 中：
     - 替换硬编码颜色。
     - 统一摘要卡片、空状态、错误状态和链接色。
     - 保持文本内容结构不变，不修改上下文生成逻辑。
   - 在 `ChapterOutlineNode.vue` 中：
     - 替换硬编码背景、边框、文字、类型徽标颜色。
     - 保持树节点缩进、展开、选择、点击行为不变。

7. 评估全局主题入口是否继续浮动
   - 检查 `ThemeSwitcher` 在以下页面是否遮挡内容：
     - `/projects`
     - `/projects/:projectId`
     - 写作编辑页
     - 人物、设定、伏笔、大纲、时间线、关系图页面
   - 如果存在明显遮挡，优先做小范围调整：
     - 增加固定入口的安全边距。
     - 移动端改为更低优先级位置。
     - 或新增 `ThemeUtilityBar.vue` 包装主题入口，保留 App 层接入。
   - 不要为了主题入口重写整体 AppShell 或 router。

8. 响应式与可访问性检查
   - 检查 390px、768px、1280px、1440px 下：
     - header 操作按钮是否换行合理。
     - 弹窗是否超出视口。
     - 筛选菜单是否溢出。
     - 卡片内长标题、长标签、长简介是否挤压布局。
   - 所有可点击元素应有可见 focus。
   - 弹窗应保留 `role="dialog"`、`aria-modal="true"`、标题关联。
   - 筛选菜单、下拉菜单应补充必要 aria 属性。

9. 执行后输出报告
   - 创建 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
   - 报告必须包含：
     - 实际修改文件列表。
     - 哪些 UI 建议已采纳。
     - 哪些 UI 建议未采纳及原因。
     - 验证命令与结果。
     - 剩余硬编码颜色清单或说明。
     - 是否存在需要 Codex 复审重点关注的问题。

# Constraints

1. 不要修改业务逻辑、API 调用、数据模型、数据库结构。
2. 不要修改后端文件。
3. 不要新增大型 UI 库或图标库。
4. 不要重写 `App.vue`、router、`ProjectDetailPage`、`ChapterTree`、`ChapterEditor`、`WritingAidPanel` 的核心结构。
5. 不要改变已有页面的功能行为，包括创建、编辑、删除、拖拽、筛选、树形结构、章节编辑、自动保存、版本管理。
6. 不要把 UI 样式整理扩展成新业务需求。
7. 不要让 UI、业务逻辑、数据访问、AI 调用混杂。
8. 不要改动 `data/`、`logs/`、本地数据库、密钥、本地配置或构建产物。
9. 所有用户可见文案必须为简体中文。
10. Canvas、关系图、时间线画布不得被普通页面主题 token 误染，继续遵守 `--zs-canvas-*` 边界。

# Verification Commands

在 `F:\zhangshu\frontend` 下执行：

```powershell
npm run type-check
npm run test:unit -- --run
npm run build
```

硬编码颜色检查：

```powershell
rg -n "#[0-9a-fA-F]{3,8}|rgb\(|rgba\(" src/pages src/features src/shared
```

人工视觉检查页面：

```text
/projects
/projects/:projectId
/projects/:projectId/characters
/projects/:projectId/settings
/projects/:projectId/clues
/projects/:projectId/outlines
/projects/:projectId/timeline
/projects/:projectId/graph
写作编辑页右侧辅助面板
项目、分卷、大纲、章节相关弹窗
```

主题和视口矩阵：

```text
默认主题 / 护眼主题 / 黑夜主题
390px / 768px / 1280px / 1440px
```

# Acceptance Criteria

1. 上一轮执行报告中列出的主要硬编码颜色遗留区域，本轮至少完成项目弹窗、卷弹窗、大纲弹窗、项目封面、项目标签、页面级状态提示的 token 化。
2. 新增或已有共享 utility 在项目、卷、大纲弹窗中被实际采用，重复 scoped CSS 明显减少。
3. `ProjectsPage.vue` 保留现有搜索、筛选、排序能力，且筛选按钮的可访问性更完整。
4. 项目详情、人物、设定、伏笔、大纲页面的 header、返回按钮、状态提示、卡片和表单控件视觉规则更一致。
5. 写作上下文组件和大纲节点在默认、护眼、黑夜主题下均可读。
6. 全局主题入口不遮挡关键页面操作。
7. 移动端没有明显横向溢出、按钮重叠、弹窗超出视口。
8. 不破坏已有业务功能。
9. `npm run type-check`、`npm run test:unit -- --run`、`npm run build` 均通过。
10. `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md` 完整记录执行范围、验证结果和未采纳建议。

# Risks and Watchpoints

1. 批量替换样式时容易误删组件 scoped 样式中仍被模板引用的 class，应逐个文件检查。
2. 共享 utility 采用过度可能让局部组件失去必要布局差异，应保留确有必要的 scoped layout class。
3. 弹窗样式统一时不要改变表单 submit、emit、校验和关闭逻辑。
4. `ProjectsPage.vue` 已有筛选排序逻辑，不要重复实现第二套状态。
5. 页面级管理视图文件较大，建议逐页处理并及时运行 type-check。
6. `rg` 检查中的部分颜色可能是用户输入示例、画布阴影或覆盖层，不需要机械清零，应在报告中分类说明。
7. 深色模式下 success、warning、danger、info 的 soft 背景可能对比不足，需人工检查。
8. 不要把全局主题入口优化扩展成完整 AppShell 重构。

# Review Checklist

Codex 复审时应检查：

1. 是否符合本计划，没有擅自扩大到业务功能开发。
2. 是否符合 `AGENTS.md` 的 Planner / Architect / Reviewer 协作边界。
3. 是否只修改计划允许范围内的前端 UI 文件和交接报告。
4. 是否存在后端、数据库、依赖、启动脚本等不应修改的文件。
5. 是否继续保持 UI、业务逻辑、数据访问、AI 调用边界清晰。
6. 是否有不必要的大规模重构。
7. 是否有无理由新增依赖。
8. 主题 token 和 utility 是否使用合理，没有把 canvas 区域错误改成普通页面主题。
9. 页面级 header、返回按钮、状态提示、弹窗、表单、卡片是否更一致。
10. `ProjectsPage.vue` 搜索筛选排序是否仍然正常。
11. 移动端和深色模式是否存在明显遮挡、重叠、对比不足。
12. 是否有未提交密钥、本地配置、临时文件、数据库、日志或构建产物。
13. 验证命令是否全部通过；若失败，执行报告是否说明原因。
14. 最终建议应明确为 Accept、Minor Revision 或 Rework。
