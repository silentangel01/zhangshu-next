# Task Summary

统一章枢各页面的“返回”按钮位置和行为，并给出若干 UI 改进建议供 Claude Code 执行时酌情采纳。

目标：

1. 页面级返回入口位置统一。
2. 避免同一页面出现多个含义相近的返回入口。
3. 返回按钮文案与目标路由根据页面上下文统一。
4. 在不重写页面、不引入 UI 库的前提下，顺手提出轻量 UI 改进建议。

本计划只规划实现方案。Codex 已阅读 Claude 上一轮伏笔模块 UI 调整执行报告，并扫描当前前端页面中的 `back-link`、`RouterLink`、`page-header`、toolbar 相关结构；Codex 未修改业务代码。本计划应由 Claude Code 执行；Claude Code 执行前应再次检查计划与当前代码是否冲突，如有冲突应停止并反馈。

# Current Codebase Findings

- Claude 上一轮执行报告位于 `docs/ai-handoff/archive/2026-05-23-clue-ui-tree/CLAUDE_EXECUTION_REPORT.md`，报告称伏笔模块已完成搜索上移、筛选折叠、按卷/章节树形展示，并通过前端 type-check/test/build 和后端 compileall。
- 当前页面级返回入口分布不一致：
  - `frontend/src/pages/characters/ProjectCharactersPage.vue`：`page-header` 内左上方 `.back-link`，文案 `返回写作页`。
  - `frontend/src/pages/settings/ProjectSettingsPage.vue`：`page-header` 内左上方 `.back-link`，文案 `返回写作页`。
  - `frontend/src/pages/clues/ProjectCluesPage.vue`：`page-header` 内左上方 `.back-link`，文案 `返回写作页`。
  - `frontend/src/pages/outlines/ProjectOutlinePage.vue`：`page-header` 内左上方 `.back-link`，文案 `返回写作页`。
  - `frontend/src/pages/graph/ProjectGraphPage.vue`：`page-header` 内左上方 `.back-link`，文案 `返回写作页`。
  - `frontend/src/pages/timeline/ProjectTimelinePage.vue`：既有 `page-header` 内 `.back-link`，又在工具栏操作区有 `toolbar-link` 返回写作页，存在重复返回入口。
  - `frontend/src/pages/search/SearchPage.vue`：`page-header` 内 `.back-link` 文案为 `返回项目`，另有 `secondary-link` 到项目列表。
  - `frontend/src/pages/review/ReviewCheckPage.vue`：`page-header` 内 `.back-link` 到 `/projects`，文案 `返回项目列表`，同时页面内还有 `secondary-link` 返回写作页。
  - `frontend/src/pages/imports/ProjectBackupPage.vue`：`page-header` 内 `.back-link`，根据 `projectId` 返回项目或项目列表；另有 `secondary-link` 项目列表。
  - `frontend/src/pages/imports/ImportPage.vue`：header actions 中有 `secondary-link` 到 `/projects`，不是 `.back-link`。
  - `frontend/src/pages/projects/ProjectDetailPage.vue`：header actions 里有 `toolbar-link` 到 `/projects`，文案 `项目列表`，不是统一的 `.back-link`。
  - `frontend/src/pages/projects/ProjectsPage.vue` 是项目列表根页面，不需要返回按钮。
- 多个页面重复定义 `.back-link` CSS，且部分 material page 又有 `.material-page .back-link` 覆盖。
- 当前页面标题、返回、操作按钮通常都在 `page-header` 中，但左侧返回按钮和右侧操作按钮的层级不完全统一。
- 当前工作区已有设定与伏笔模块未提交业务改动；本任务必须避免回退或重写这些改动。

# Architecture Decision

采用“页面级返回入口规范化”的小范围前端调整，不新建路由、不改后端、不引入依赖。

统一规则：

- 所有需要返回上一级上下文的页面，返回入口放在页面主 `page-header` 的左上角，位于 eyebrow / H1 之前。
- 返回入口使用统一 class：`back-link`。
- 项目内子页面统一返回 `/projects/{projectId}`，文案统一为 `返回写作页`。
- 项目详情页返回 `/projects`，文案为 `返回项目列表`。
- 独立导入页返回 `/projects`，文案为 `返回项目列表`。
- 备份页：
  - 有 `projectId` 时返回 `/projects/{projectId}`，文案 `返回写作页`。
  - 无 `projectId` 时返回 `/projects`，文案 `返回项目列表`。
- 搜索页和检查页：
  - 如果路由含 `projectId`，主返回入口应返回 `/projects/{projectId}`，文案 `返回写作页`。
  - 不应在同一区域重复放置“返回写作页”和“返回项目列表”；若仍需要项目列表入口，应作为次级操作放在右侧 header actions，文案 `项目列表`。
- 工具栏内不再放置重复的页面级返回入口；时间轴工具栏里的 `返回写作页` 应移除，保留 header 左上角返回。

实现策略：

- 优先复用现有 `.back-link` 样式，不新增大型抽象。
- 如 Claude Code 判断重复 CSS 已经明显影响维护，可新增一个轻量共享样式段到全局样式；但不要为了本任务重构所有 page header。
- 不新增 `PageHeader` 组件，不重写页面布局。

# Files to Create or Modify

建议修改：

- `frontend/src/pages/projects/ProjectDetailPage.vue`
  - 将 `项目列表` 从右侧 toolbar 风格调整为页面左上角 `.back-link`，或至少统一 class/位置。
- `frontend/src/pages/imports/ImportPage.vue`
  - 将 `返回项目` 从 header actions 调整为 header 左上角 `.back-link`，文案改为 `返回项目列表`。
- `frontend/src/pages/imports/ProjectBackupPage.vue`
  - 统一返回文案和位置；检查是否需要保留额外 `项目列表` 次级入口。
- `frontend/src/pages/search/SearchPage.vue`
  - 主返回入口统一为 `返回写作页`，目标 `/projects/{projectId}`。
  - `项目列表` 作为次级入口时放在 header actions，不与主返回混淆。
- `frontend/src/pages/review/ReviewCheckPage.vue`
  - 主返回入口统一为 `返回写作页`，目标 `/projects/{projectId}`。
  - 如保留项目列表入口，放在次级操作区。
- `frontend/src/pages/timeline/ProjectTimelinePage.vue`
  - 移除工具栏内重复 `返回写作页`。
  - 保留 header 左上角 `.back-link`。
- `frontend/src/pages/characters/ProjectCharactersPage.vue`
- `frontend/src/pages/settings/ProjectSettingsPage.vue`
- `frontend/src/pages/clues/ProjectCluesPage.vue`
- `frontend/src/pages/outlines/ProjectOutlinePage.vue`
- `frontend/src/pages/graph/ProjectGraphPage.vue`
  - 这些页面已有较接近规范的 `.back-link`，只需要检查样式、位置、文案是否一致。

可按需要修改：

- `frontend/src/style.css`
  - 如 Claude Code 认为多个页面重复 `.back-link` 过多，可抽取统一的 `.page-back-link` 或统一 `.back-link` 基础样式。
  - 若抽取全局样式，应保持局部页面样式不冲突。

不应修改：

- 后端代码。
- API、数据库、schema。
- `frontend/src/router/index.ts`，除非发现现有路由目标拼写错误；一般不需要。
- 业务组件，如 ChapterEditor、ChapterTree、WritingAidPanel。

# Implementation Steps for Claude Code

1. 执行前检查
   - 读取本计划。
   - 运行 `git status --short`，确认当前已有设定/伏笔模块未提交改动。
   - 不要回退、格式化或重写这些已有改动。
   - 先运行：
     - `cd F:\zhangshu\frontend`
     - `npm run type-check`
   - 如果当前 type-check 已失败，停止并反馈，不要继续叠加 UI 改动。

2. 定义返回入口规范
   - 在执行报告中记录采用的规范：
     - 主返回入口位于 `page-header` 左上角。
     - class 使用 `back-link`。
     - 项目内页面返回 `返回写作页`。
     - 顶层/非项目上下文页面返回 `返回项目列表`。
   - 不需要新增文档文件；执行报告中说明即可。

3. 调整项目详情页
   - 修改 `frontend/src/pages/projects/ProjectDetailPage.vue`。
   - 当前 `项目列表` 在 `header-actions` 中。
   - 将其移到 header 左侧标题内容区的最上方，样式使用 `back-link`，目标 `/projects`，文案 `返回项目列表`。
   - 右侧 `header-actions` 保留 `搜索`、`检查` 等同级功能入口。
   - 避免出现两个到 `/projects` 的重复入口。

4. 调整导入页
   - 修改 `frontend/src/pages/imports/ImportPage.vue`。
   - 将返回项目列表入口移动到 `page-header` 左上角。
   - 文案统一为 `返回项目列表`。
   - 如果 header actions 中原本只有返回入口，移动后 header actions 可删除或保留其它操作。

5. 调整备份页
   - 修改 `frontend/src/pages/imports/ProjectBackupPage.vue`。
   - 保持项目上下文判断：
     - `projectId ? /projects/${projectId} : /projects`
   - 文案统一：
     - `projectId ? '返回写作页' : '返回项目列表'`
   - 如果页面内还有 `项目列表` 次级链接，确认它不与主返回重复；有项目上下文时可保留为次级入口，无项目上下文时应删除重复入口。

6. 调整搜索页
   - 修改 `frontend/src/pages/search/SearchPage.vue`。
   - 主返回入口改为：
     - target: `/projects/${projectId}`
     - text: `返回写作页`
   - `项目列表` 如保留，放在 header actions 或页面次级区域，文案 `项目列表`。
   - 避免主返回文案 `返回项目` 这种模糊表达。

7. 调整检查页
   - 修改 `frontend/src/pages/review/ReviewCheckPage.vue`。
   - 主返回入口改为：
     - target: `/projects/${projectId}`
     - text: `返回写作页`
   - 当前页面内 `secondary-link` 返回写作页应删除或改为项目列表次级入口，避免重复。
   - 如果需要保留返回项目列表，放在 header actions，文案 `项目列表`。

8. 调整时间轴页
   - 修改 `frontend/src/pages/timeline/ProjectTimelinePage.vue`。
   - 保留 `page-header` 内 `.back-link` 返回写作页。
   - 删除工具栏操作区内重复的 `<RouterLink class="toolbar-link" :to="\`/projects/${projectId}\`">返回写作页</RouterLink>`。
   - 工具栏应专注时间轴操作，不承担页面级导航返回。

9. 检查已有项目子页面
   - 检查以下文件的 header 返回入口是否都在 title/eyebrow 前方：
     - `frontend/src/pages/characters/ProjectCharactersPage.vue`
     - `frontend/src/pages/settings/ProjectSettingsPage.vue`
     - `frontend/src/pages/clues/ProjectCluesPage.vue`
     - `frontend/src/pages/outlines/ProjectOutlinePage.vue`
     - `frontend/src/pages/graph/ProjectGraphPage.vue`
   - 如已符合规范，只做必要的小范围 class/style 对齐。
   - 不要因样式统一而重写页面结构。

10. 样式统一
   - 确认 `.back-link` 的视觉一致：
     - 出现在 header 左上方。
     - 与标题之间有稳定间距。
     - 颜色使用项目主色或现有 `var(--zs-color-primary)`。
     - 字重和字号统一，避免有的页面像普通链接、有的像按钮。
   - 可选方案：
     - 如果不想改全局样式，只在各页面保持现有 `.back-link` 风格即可。
     - 如果抽取全局样式到 `frontend/src/style.css`，应减少页面 scoped 中重复定义，但不要大规模清理无关 CSS。

11. 可选 UI 改进建议，由 Claude Code 评估采纳
   - 建议 A：页面标题区采用统一结构：
     - 返回链接
     - eyebrow
     - H1
     - 项目名/说明
     - 右侧 actions
   - 建议 B：所有 header actions 中的导航入口区分主次：
     - 页面级返回只在左上角。
     - 跨功能入口放右侧 actions。
     - 操作按钮如“新建”保留右侧，使用 primary button。
   - 建议 C：统一空状态和提示条间距：
     - `error-banner` / `success-banner` / `state-message` 与 toolbar/header 间距一致。
   - 建议 D：减少重复返回文案：
     - 项目内统一 `返回写作页`。
     - 顶层统一 `返回项目列表`。
     - 不使用 `返回项目` 这种不够具体的文案。
   - 建议 E：如页面已有顶部工具条，返回按钮不要进入工具条；工具条只放本页面功能操作。
   - 这些建议不是强制项。Claude Code 如采纳，必须保持小范围修改，并在执行报告中说明采纳了哪些。

12. 测试与验证
   - 本任务主要是页面结构和样式调整，一般不需要新增单元测试。
   - 若改动影响现有测试快照或查询，可更新相关测试。
   - 必须运行前端 type-check 和 build。
   - 如测试环境可用，运行 unit test。

13. 执行报告
   - Claude Code 完成后覆盖写入 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
   - 报告必须包含：
     - 实际修改文件列表。
     - 每个页面返回入口的新位置和目标路由。
     - 删除了哪些重复返回入口。
     - 采纳了哪些可选 UI 建议。
     - 验证命令和结果。
     - 未完成项或风险。

# Constraints

- 不要修改后端代码。
- 不要新增路由。
- 不要新增依赖。
- 不要重写页面整体布局。
- 不要修改业务数据流或 API 调用。
- 不要改动核心写作组件：ProjectDetailPage 的业务逻辑、ChapterTree、ChapterEditor、WritingAidPanel，除非只是移动 header 返回入口。
- 不要破坏设定和伏笔模块刚完成的搜索/筛选/树形改动。
- 用户可见 UI 文案必须是简体中文。
- 不要提交本地数据库、日志、密钥、临时文件或构建产物。

# Verification Commands

前端验证：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit
npm run build
```

手动验证：

```powershell
cd F:\zhangshu\frontend
npm run dev
```

浏览器检查页面：

- `/projects`
- `/projects/{projectId}`
- `/projects/{projectId}/characters`
- `/projects/{projectId}/settings`
- `/projects/{projectId}/clues`
- `/projects/{projectId}/outlines`
- `/projects/{projectId}/graph`
- `/projects/{projectId}/timeline`
- `/projects/{projectId}/search`
- `/projects/{projectId}/review`
- `/projects/{projectId}/backup`
- `/imports`
- `/backup`

检查点：

- 返回入口是否位于页面左上角。
- 返回文案是否符合页面上下文。
- 点击返回是否进入正确路由。
- 是否存在重复的“返回写作页”。
- 右侧操作按钮是否仍然可用。
- 移动端 header 是否换行正常，不遮挡标题和操作按钮。

# Acceptance Criteria

- 项目内子页面的主返回入口统一位于 `page-header` 左上角。
- 项目内子页面主返回文案统一为 `返回写作页`。
- 顶层/非项目上下文页面主返回文案统一为 `返回项目列表`。
- 项目详情页返回项目列表入口位置与其它页面规则一致。
- 时间轴页不再同时在 header 和 toolbar 中重复展示 `返回写作页`。
- 搜索页和检查页不再把主返回指向项目列表；主返回应回到写作页。
- 导入页和备份页返回入口位置统一。
- 设定和伏笔模块新完成的工具条、筛选、树形结构不被破坏。
- 前端 type-check 和 build 通过；如 unit test 无法运行，执行报告说明原因。

# Risks and Watchpoints

- 当前工作区有大量未提交改动，Claude Code 不得回退或覆盖设定/伏笔模块现有改动。
- 多个页面有 scoped `.back-link` 样式，统一时容易产生局部样式不一致；优先小范围调整，不做大规模 CSS 清理。
- `ReviewCheckPage` 和 `SearchPage` 当前返回目标可能与用户习惯不同，改为返回写作页后应保留项目列表作为次级入口，避免导航断点。
- `TimelinePage` 工具栏较复杂，删除重复返回链接时不要影响工具栏其它按钮。
- `ImportPage` 和 `/backup` 可能没有项目上下文，返回目标必须保持 `/projects`。
- 不要为了统一 header 而重写整页结构或引入共享组件，除非改动极小且执行报告说明理由。
- PowerShell 输出可能显示中文乱码，实际文件必须保持 UTF-8，UI 文案不能乱码。

# Review Checklist

- 是否先读取 Claude 执行报告。
- 是否归档旧 `CODEX_PLAN.md` 和 `CLAUDE_EXECUTION_REPORT.md`。
- 是否只修改前端页面返回入口相关代码。
- 是否没有修改后端/API/数据库。
- 是否没有新增依赖或路由。
- 项目内页面是否统一返回 `/projects/{projectId}`。
- 顶层页面是否统一返回 `/projects`。
- 时间轴是否移除了重复返回入口。
- 搜索页和检查页是否保留了到项目列表的次级入口或等价导航。
- 设定/伏笔页面的新搜索、筛选、树结构是否没有回退。
- 移动端 header 是否无重叠。
- 中文文案是否为简体中文且无乱码。
- 前端 type-check/test/build 是否通过。
- 执行报告是否写入 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
