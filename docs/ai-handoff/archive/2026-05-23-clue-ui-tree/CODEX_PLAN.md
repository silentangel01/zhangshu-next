# Task Summary

参考设定模块页面的最新交互，对“伏笔”模块做 UI 调整：

1. 将搜索框从左侧列表移到页面上方。
2. 将状态、可见程度、重要程度筛选合并到一个“筛选”按钮的二级菜单/面板内。
3. 将左侧伏笔列表改成类似树形结构，按伏笔绑定的章节或卷来组织展示。

本计划只规划实现方案。Codex 已阅读 Claude 对上一轮设定模块交互优化的执行报告，并读取当前伏笔相关前后端代码；Codex 未修改业务代码。本计划应由 Claude Code 执行；Claude Code 执行前应再次检查计划与当前代码是否冲突，如有冲突应停止并反馈。

# Current Codebase Findings

- Claude 上一轮执行报告位于 `docs/ai-handoff/archive/2026-05-23-setting-ui-drag/CLAUDE_EXECUTION_REPORT.md`，报告称设定模块已完成搜索上移、筛选折叠、拖拽移动和三态确认，且前端 type-check/test/build 通过。
- 当前旧交接文件已归档，活跃交接区只保留本任务的新 `CODEX_PLAN.md`。
- 伏笔后端主表为 `backend/app/models/clue.py` 的 `Clue`，已有：
  - `setup_chapter_id`
  - `payoff_chapter_id`
  - `status`
  - `visibility`
  - `importance`
  - `deleted_at`
- 伏笔 API 在 `backend/app/api/clues.py`，已有 `GET /api/projects/{project_id}/clues`，支持 `status`、`visibility`、`importance`、`keyword` 查询参数。
- 伏笔 Service / Repository 已按项目和筛选条件返回扁平伏笔列表；本次 UI 调整不需要新增后端查询。
- 前端伏笔页面为 `frontend/src/pages/clues/ProjectCluesPage.vue`。
- `ProjectCluesPage.vue` 当前：
  - 已加载 `listChapters(projectId)`。
  - 未加载 `listVolumes(projectId)`。
  - 搜索框和筛选 select 常驻在左侧 `.filters` 区域。
  - 左侧展示为扁平 `clue-list`。
  - 通过 `chapterTitleMap` 显示埋设/回收章节标题。
- 章节 `Chapter` 类型包含 `volume_id` 和 `order_index`，卷 `Volume` 类型包含 `order_index`，足够在前端派生 `卷 > 章节 > 伏笔` 树。
- 当前伏笔数据只直接绑定章节，不直接绑定卷；“按卷管理”应通过章节的 `volume_id` 派生，不应新增 `clue.volume_id`。
- 当前 `frontend/src/entities/clue/api.ts` 的 `listProjectClues()` 已可透传现有筛选字段，不需要改 API 层。
- 当前 `frontend/src/entities/volume/api.ts` 提供 `listVolumes(projectId)`，可在伏笔页复用。
- 当前 `frontend/src/features/clues/ChapterCluePanel.vue` 是章节编辑侧栏里的伏笔绑定面板，本任务不应改动，除非发现共享类型变更导致编译问题。
- 当前工作区已有上一轮设定模块大量未提交业务改动；Claude Code 执行前必须避免把本任务改动和设定模块修复混在一起。

# Architecture Decision

采用前端派生树形结构，不改后端存储、不新增 API、不引入 UI 组件库。

- 搜索与筛选仍通过现有 `GET /api/projects/{project_id}/clues` 查询参数完成。
- 页面顶部工具条复用设定模块已形成的交互风格：搜索框在上方，筛选项折叠到“筛选”按钮打开的面板内。
- 左侧树由前端根据 `volumes`、`chapters`、`clues` 派生：
  - 根节点：`全部伏笔`。
  - 第一层：卷节点，如 `第一卷`、`第二卷`。
  - 第二层：章节节点。
  - 第三层：伏笔卡片。
- 分组依据建议提供一个轻量切换：
  - `按埋设章节`：使用 `clue.setup_chapter_id`。
  - `按回收章节`：使用 `clue.payoff_chapter_id`。
  - 默认使用 `按埋设章节`，因为伏笔管理通常先看埋设位置。
- 未绑定章节的伏笔放入专用分组：
  - `未绑定埋设章节` 或 `未绑定回收章节`，随当前分组模式变化。
- 如果章节无卷，则放入 `未分卷` 卷节点。
- 如果伏笔绑定的章节已不存在或不在当前项目章节列表中，则放入 `未知章节` 节点。
- 树节点只是前端展示结构，不写入数据库；伏笔的真实绑定仍由 `setup_chapter_id` 和 `payoff_chapter_id` 决定。
- 本任务不做拖拽移动伏笔到章节；如果后续需要，可复用 `updateClue(clue.id, { setup_chapter_id })` 或 `payoff_chapter_id`，但本次不扩大范围。

# Files to Create or Modify

需要修改：

- `frontend/src/pages/clues/ProjectCluesPage.vue`
  - 引入 `listVolumes` 和 `Volume` 类型。
  - 将搜索框移动到页面上方工具条。
  - 将筛选项收进“筛选”按钮二级菜单/面板。
  - 将左侧扁平 `clue-list` 改为树形展示。
  - 新增按埋设章节/回收章节分组模式。
  - 新增树展开/折叠状态。
  - 调整 CSS，保持页面在桌面和移动端不重叠。

可按需要修改：

- `frontend/src/__tests__/clues-tree.spec.ts`
  - 如果当前测试习惯允许，新增伏笔树分组与筛选状态的轻量测试。
- `frontend/src/__tests__/settings-tree.spec.ts`
  - 不应修改，除非本次改动导致共享测试工具冲突。

一般不需要修改：

- `frontend/src/entities/clue/api.ts`
- `frontend/src/entities/clue/types.ts`
- `frontend/src/entities/chapter/types.ts`
- `frontend/src/entities/volume/types.ts`

不应修改：

- 后端伏笔 model / schema / repository / service / API。
- `backend/app/main.py`。
- `frontend/src/router/index.ts`。
- `frontend/src/App.vue`。
- Project / Volume / Chapter / Editor / Autosave / Version / Import / Outline / Character / Setting API。

# Implementation Steps for Claude Code

1. 执行前检查
   - 读取本计划。
   - 运行 `git status --short`。
   - 确认上一轮设定模块改动仍在工作区，不要回退或重写这些改动。
   - 先运行前端基础检查：
     - `cd F:\zhangshu\frontend`
     - `npm run type-check`
   - 如果当前项目已因上一轮改动 type-check 失败，停止并反馈，不要继续叠加伏笔 UI 改动。

2. 引入卷数据
   - 修改 `frontend/src/pages/clues/ProjectCluesPage.vue`。
   - 新增 import：
     - `import { listVolumes } from '@/entities/volume/api'`
     - `import type { Volume } from '@/entities/volume/types'`
   - 新增状态：
     - `const volumes = ref<Volume[]>([])`
   - 修改 `loadWorkspace()`：
     - 当前 Promise.all 是 `getProject`、`listChapters`、`listProjectClues`。
     - 扩展为同时加载 `listVolumes(projectId.value)`。
     - 将返回结果写入 `volumes.value`。
   - `refreshClues()` 不需要重新加载 volumes 和 chapters，除非项目章节/卷结构变化；本任务保持现有范围。

3. 顶部搜索工具条
   - 在 `page-header` 下方、错误/成功提示上方新增 `.clues-toolbar`。
   - 将左侧 `.filters` 中的搜索 input 移动到顶部工具条。
   - 搜索 input 继续绑定 `filters.keyword`。
   - 添加搜索按钮：
     - 文案：`搜索`
     - 点击调用 `handleApplyFilters()`。
   - 支持回车搜索：
     - `@keyup.enter="handleApplyFilters"`。
   - 左侧 list panel 中移除 keyword input。

4. 筛选按钮和二级面板
   - 新增 UI 状态：
     - `const isFilterPanelOpen = ref(false)`
   - 新增计算属性：
     - `activeFilterCount`，统计 `filters.status`、`filters.visibility`、`filters.importance` 中非空项数量，不统计 keyword。
   - 在顶部工具条新增“筛选”按钮：
     - 无筛选时显示 `筛选`。
     - 有筛选时显示 `筛选（N）`。
     - 点击切换 `isFilterPanelOpen`。
   - 筛选面板放在工具条下或工具条内，不占用左侧树空间。
   - 面板内容包括原有三个 select：
     - 伏笔状态：`filters.status`
     - 可见程度：`filters.visibility`
     - 重要程度：`filters.importance`
   - 面板按钮：
     - `应用筛选`：调用 `handleApplyFilters()`，然后关闭面板。
     - `清空筛选`：清空 status / visibility / importance，保留 keyword，然后刷新列表。
   - 新增函数：
     - `handleClearStructuredFilters()`。
   - 左侧 `.filters` 区域整体删除或改为树控制区，不再常驻展示筛选 select。

5. 分组模式切换
   - 新增状态：
     - `const clueGroupMode = ref<'setup' | 'payoff'>('setup')`
   - 在顶部工具条或左侧树标题处新增 segmented 控制：
     - `按埋设章节`
     - `按回收章节`
   - 切换时不重新请求 API，只改变树的派生方式。
   - 切换后保留当前已选中伏笔；如果该伏笔仍在列表中，卡片应保持 active。

6. 构建树数据结构
   - 在 `ProjectCluesPage.vue` 中定义本地 interface：
     - `ClueTreeVolumeNode`
     - `ClueTreeChapterNode`
     - 或统一 `ClueTreeItem`，包含 `kind: 'volume' | 'chapter' | 'clue'`。
   - 新增计算映射：
     - `volumeById`
     - `chapterById`
     - `chaptersByVolumeId`
   - 新增 `clueTree` computed：
     - 遍历当前 `clues.value`，根据 `clueGroupMode` 取 `setup_chapter_id` 或 `payoff_chapter_id`。
     - 找到章节后，根据 `chapter.volume_id` 放入对应卷节点。
     - 没有章节 id 的放入未绑定分组。
     - 有章节 id 但找不到章节的放入未知章节分组。
   - 排序规则：
     - 卷按 `volume.order_index asc`，再按 title。
     - 未分卷卷节点放在正常卷之后，未知章节和未绑定分组放在最后。
     - 章节按 `chapter.order_index asc`，再按 title。
     - 伏笔按当前后端返回顺序，或按 `updated_at desc`；建议保留后端返回顺序，避免用户理解变化过大。
   - 每个卷/章节节点显示计数：
     - 卷显示该卷下匹配伏笔总数。
     - 章节显示该章节下匹配伏笔数。

7. 树展开/折叠
   - 新增状态：
     - `const expandedTreeKeys = ref<Set<string>>(new Set())`
   - 注意 Vue 对 Set 的响应式更新：
     - 更新时创建新 Set 再赋值，例如 `expandedTreeKeys.value = new Set(expandedTreeKeys.value).add(key)`。
   - 新增函数：
     - `isTreeExpanded(key: string): boolean`
     - `toggleTreeNode(key: string): void`
   - 初始展开策略：
     - 默认展开所有含有伏笔的卷和章节，或者默认展开第一个卷。
     - 建议简单起步：`clueTree` 变化后，如果 `expandedTreeKeys` 为空，则自动展开全部有内容的卷节点；章节可默认展开。
   - 不要新增复杂持久化，避免 localStorage 状态污染。

8. 左侧树模板
   - 将原 `ul.clue-list` 扁平列表替换为树模板。
   - 结构建议：
     - `<ul class="clue-tree">`
     - 卷节点为按钮或 header，点击展开/折叠。
     - 章节节点缩进一级，点击展开/折叠。
     - 伏笔卡片缩进二级，点击调用 `handleSelectClue(clue)`。
   - 卷节点不触发表单编辑。
   - 章节节点不触发表单编辑。
   - 只有伏笔节点可选中并打开右侧编辑器。
   - 伏笔卡片继续显示：
     - 标题
     - 状态 / 可见程度 / 重要程度
     - 埋设章节
     - 回收章节
     - 简短描述
   - 树节点文案必须为简体中文。

9. 空状态与过滤状态
   - 如果 `clues.length === 0`，保留空状态，但文案区分：
     - 无搜索/筛选：`暂无伏笔，请先新建伏笔。`
     - 有搜索/筛选：`没有符合条件的伏笔。`
   - 搜索/筛选后树只展示匹配伏笔及其卷/章节祖先节点。
   - 分组模式切换不影响搜索/筛选结果，只影响组织方式。

10. 编辑表单保持不变
    - 右侧伏笔详情表单保持当前字段：
      - 标题
      - 状态
      - 可见程度
      - 重要程度
      - 埋设章节
      - 回收章节
      - 描述
      - 回收计划
      - 实际回收
      - 备注
    - 不改变创建/保存/删除逻辑。
    - 不改变关系图打开逻辑。
    - 不改变 `MaterialLinkPanel`。

11. 样式调整
    - 新增或调整 CSS：
      - `.clues-toolbar`
      - `.search-group`
      - `.filter-menu`
      - `.filter-panel`
      - `.tree-mode-control`
      - `.clue-tree`
      - `.tree-volume`
      - `.tree-chapter`
      - `.tree-clue`
      - `.tree-count`
   - 不要嵌套卡片套卡片；树节点用轻量边框/背景区分。
   - 保证顶部工具条在移动端换行，不遮挡内容。
   - 保证长标题不溢出，可换行。

12. 测试补充
    - 可新增 `frontend/src/__tests__/clues-tree.spec.ts`。
    - 建议测试纯 helper 或导出的局部构造函数；如无法从 Vue SFC 直接导出，可在测试中复制最小输入输出结构验证业务规则，但不要引入依赖。
    - 覆盖点：
      - 按埋设章节分组时，伏笔进入对应卷和章节。
      - 按回收章节分组时，伏笔进入回收章节对应卷。
      - 无绑定章节的伏笔进入未绑定分组。
      - `activeFilterCount` 不统计 keyword，只统计结构化筛选。
    - 如果不新增测试，执行报告必须说明原因，并至少运行 type-check/build。

13. 执行报告
    - Claude Code 完成后覆盖写入 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
    - 报告必须包含：
      - 实际修改文件列表。
      - 是否未改后端、未改 API、未新增依赖。
      - 搜索上移和筛选按钮交互说明。
      - 伏笔树按埋设/回收章节分组的实现说明。
      - 验证命令和结果。
      - 未完成项或风险。

# Constraints

- 不要修改后端伏笔 API、Service、Repository、Model、Schema。
- 不要新增数据库字段或迁移逻辑。
- 不要新增大型依赖、UI 库或树组件库。
- 不要改变伏笔的真实数据结构；树只是前端派生视图。
- 不要实现拖拽移动伏笔到章节或卷；本任务只做树形组织展示。
- 不要修改章节、卷、设定、人物等无关模块。
- 不要重写整个 `ProjectCluesPage.vue`，应基于现有页面定向调整。
- 用户可见文案必须是简体中文。
- 代码标识符、文件名、API 路径保持英文。
- 不要提交本地数据库、日志、密钥、临时文件或构建产物。

# Verification Commands

前端验证：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit
npm run build
```

后端基础语法检查，确保未被本任务破坏：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
python -m compileall app
```

手动验证：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd F:\zhangshu\frontend
npm run dev
```

浏览器验证：

- 打开项目“伏笔”页面。
- 确认搜索框位于页面上方，而不是左侧树内。
- 点击“筛选”按钮，确认出现状态、可见程度、重要程度筛选项。
- 应用筛选后，左侧树只显示符合条件的伏笔及其所属卷/章节节点。
- 清空筛选后，结构化筛选条件清空，搜索词按计划保留。
- 切换“按埋设章节”，确认伏笔按 `setup_chapter_id` 所在章节/卷组织。
- 切换“按回收章节”，确认伏笔按 `payoff_chapter_id` 所在章节/卷组织。
- 创建一个未绑定埋设章节的伏笔，确认它出现在未绑定分组。
- 选择伏笔卡片，确认右侧编辑表单正常加载。
- 保存伏笔后，树刷新且仍可按当前搜索/筛选/分组展示。

# Acceptance Criteria

- 伏笔页面搜索框已移动到页面上方。
- 左侧面板不再常驻展示状态、可见程度、重要程度筛选 select。
- “筛选”按钮可打开二级筛选面板。
- 筛选面板可按状态、可见程度、重要程度筛选。
- 可清空结构化筛选条件。
- 左侧伏笔列表已改为树形结构。
- 树可按埋设章节组织为 `卷 > 章节 > 伏笔`。
- 树可按回收章节组织为 `卷 > 章节 > 伏笔`。
- 未绑定章节的伏笔有明确分组。
- 未分卷章节有明确分组。
- 只有伏笔节点会打开右侧编辑器；卷和章节节点只负责展开/折叠。
- 搜索/筛选后树不会出现孤立伏笔，必须保留其分组上下文。
- 不改后端 API 和数据库。
- 不新增依赖。
- 前端 type-check、unit test、build 通过；如某项无法运行，执行报告必须说明原因。

# Risks and Watchpoints

- 当前工作区已有设定模块未提交改动，Claude Code 不得回退或重写这些改动。
- PowerShell 输出中文乱码，实际文件必须保持 UTF-8，UI 文案不能乱码。
- 伏笔只有章节绑定，没有卷绑定；按卷展示必须通过章节 `volume_id` 派生。
- 一个伏笔同时有埋设章节和回收章节，因此树必须明确当前分组模式，否则用户会困惑。
- 如果按回收章节分组，未填写回收章节的伏笔会较多，未绑定分组需要清晰。
- 如果后端筛选返回结果不包含某些章节，前端仍有完整 `chapters` 和 `volumes`，可以恢复分组上下文。
- 不要为了树视图把过滤逻辑从后端搬到前端；继续使用现有 API 筛选。
- 不要把树展开状态持久化到 localStorage，避免和项目切换造成旧状态污染。
- 移动端不要求完整树交互增强，但布局不能破裂。

# Review Checklist

- 是否先归档旧 `CODEX_PLAN.md` 和 `CLAUDE_EXECUTION_REPORT.md`。
- 是否只修改了伏笔页面和必要前端测试。
- 是否没有修改后端伏笔 API/Service/Repository/Model/Schema。
- 是否没有新增 API 或数据库字段。
- 是否没有新增依赖。
- 搜索框是否位于页面上方。
- 筛选项是否合并进“筛选”按钮二级面板。
- 清空筛选是否只清空结构化筛选项。
- 树是否按卷和章节正确组织。
- 分组模式是否能在埋设章节和回收章节之间切换。
- 未绑定章节和未分卷是否有明确分组。
- 卷/章节节点是否只展开折叠，不打开编辑器。
- 伏笔节点是否能正常选中并加载详情。
- 保存/删除/打开关系图/资料关联是否没有回退。
- 中文 UI 文案是否为简体中文且没有乱码。
- 前端 type-check/test/build 是否通过。
- 执行报告是否覆盖写入 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
