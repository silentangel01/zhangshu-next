# Task Summary

继续改进“设定”功能模块，在上一轮设定树实现基础上做三项交互优化：

1. 将搜索框从左侧树面板移动到页面上方，作为全局设定搜索入口。
2. 将原本常驻展示的筛选项收起为一个“筛选”按钮，点击后再选择按类型、确认状态、重要程度等条件筛选。
3. 支持用户拖拽左侧树中的设定页卡片，将其移动到任意目录下；完成移动前进行检查，如果检测到设定页当前类型与目标目录默认类型不同，提示用户是否自动更改设定类型。

本计划只规划实现方案。Codex 已阅读 Claude 的执行报告和当前相关代码，但未修改业务代码。本计划应由 Claude Code 执行；Claude Code 执行前应再次检查计划与当前代码是否冲突，如有冲突应停止并反馈。

# Current Codebase Findings

- Claude 执行报告位于旧任务归档中，报告称已完成设定树、默认目录、类型继承、系统目录保护、章节绑定只显示 page，并补充了后端/前端测试。
- 当前工作区已有未提交业务改动，涉及：
  - `backend/app/api/settings.py`
  - `backend/app/infrastructure/database.py`
  - `backend/app/models/setting_item.py`
  - `backend/app/repositories/setting_repo.py`
  - `backend/app/schemas/setting.py`
  - `backend/app/services/setting_service.py`
  - `frontend/src/entities/setting/types.ts`
  - `frontend/src/features/settings/ChapterSettingPanel.vue`
  - `frontend/src/pages/settings/ProjectSettingsPage.vue`
  - `backend/tests/`
  - `frontend/src/__tests__/settings-tree.spec.ts`
- `frontend/src/pages/settings/ProjectSettingsPage.vue` 当前仍把搜索框和筛选 select 放在左侧 `list-panel` 的 `.filters` 区域。
- 当前左侧树已通过 `buildTree()` 展示目录和设定页，并用 `node_kind` 区分 `folder` / `page`。
- 当前前端已有 `handleSelectSetting()`、`handleSaveSetting()`、`refreshSettings()`、`buildFilters()`、`buildTree()` 等函数，可以在此基础上定向扩展，不需要重写页面。
- 当前前端通过 `updateSetting(settingId, payload)` 更新设定。拖拽移动可复用该 API，发送 `parent_id` 更新即可。
- 当前后端 `SettingService.update_setting()` 已有规则：page 移动到新 folder 且请求未显式传 `item_type` 时，会继承目标目录默认类型；如果显式传 `item_type`，则可保留原类型。
- 当前 `frontend/src/entities/setting/types.ts` 已支持 `SettingNodeKind`、`SettingItem.folder_default_item_type`、`SettingItem.item_type` 等拖拽检查所需字段。
- 当前 `frontend/src/entities/setting/api.ts` 的 `buildQuery()` 会透传 `SettingFilters` 字段，顶部搜索和筛选按钮无需新增 API。
- 当前 UI 中文在 PowerShell 输出中显示乱码，Claude Code 修改时必须确保实际文件以 UTF-8 保存，且用户可见文案为简体中文。
- 当前后端 pytest 在 Claude 报告中未成功运行；本次任务虽主要是前端交互，但执行前仍应先确认上一轮代码至少能通过 Python 编译和前端 type-check。

# Architecture Decision

采用前端定向交互升级，不新增后端表、不新增 API、不引入拖拽依赖。

- 搜索与筛选属于前端展示和查询参数组合逻辑，继续复用现有 `GET /api/projects/{project_id}/settings`。
- 筛选按钮使用页面内轻量弹出层或下拉面板实现，不引入 UI 库。
- 拖拽使用浏览器原生 HTML Drag and Drop API，避免新增依赖。
- 只允许拖拽 `node_kind === 'page'` 的设定页；目录本身暂不支持拖拽移动，避免引入目录循环和大范围交互复杂度。
- 只允许把设定页拖放到 `node_kind === 'folder'` 的目标目录。
- 拖拽移动前由前端做交互确认：
  - 如果目标目录没有 `folder_default_item_type`，直接移动并保留原类型。
  - 如果目标目录默认类型与设定页当前 `item_type` 相同，直接移动。
  - 如果目标目录默认类型与设定页当前 `item_type` 不同，弹出确认：
    - 用户选择“自动更改类型”：调用 `updateSetting(page.id, { parent_id: targetFolder.id })`，不传 `item_type`，让后端继承目标目录类型。
    - 用户选择“仅移动，保留原类型”：调用 `updateSetting(page.id, { parent_id: targetFolder.id, item_type: page.item_type })`。
    - 用户取消：不调用 API，不改变状态。
- 后端仍作为最终规则兜底：父级必须是 folder、同项目、不得形成循环。前端只负责用户提示，不替代后端校验。
- 本任务不处理目录拖拽、批量移动、多选移动、拖拽排序；这些可留给后续任务。

# Files to Create or Modify

需要修改：

- `frontend/src/pages/settings/ProjectSettingsPage.vue`
  - 移动搜索框到页面上方。
  - 将筛选 select 收进“筛选”按钮触发的面板。
  - 为左侧 page 卡片增加拖拽源。
  - 为 folder 卡片增加拖放目标。
  - 增加拖拽前检查、类型差异确认、调用 `updateSetting()` 移动、刷新列表和错误提示。
  - 调整必要 CSS，确保顶部搜索区、筛选面板、拖拽状态在桌面和移动端不重叠。

可按需要修改：

- `frontend/src/__tests__/settings-tree.spec.ts`
  - 增加拖拽移动辅助逻辑或筛选状态的轻量测试。
- `frontend/src/entities/setting/types.ts`
  - 一般不需要改；如当前类型定义无法表达筛选面板状态，优先在页面组件内定义本地 UI 类型。
- `frontend/src/entities/setting/api.ts`
  - 一般不需要改；仅当发现 `SettingFilters` 缺少本次筛选字段时再补充。

不建议修改：

- 后端业务文件。本任务可复用现有 `PATCH /api/settings/{setting_id}`。
- `backend/app/main.py`。
- `frontend/src/router/index.ts`。
- `frontend/src/App.vue`。
- 其它 Project / Volume / Chapter / Editor / Autosave / Version / Import / Outline / Character / Clue API。

# Implementation Steps for Claude Code

1. 执行前检查
   - 读取 `docs/ai-handoff/CODEX_PLAN.md`。
   - 运行 `git status --short`，确认当前存在上一轮设定树相关未提交改动。
   - 先运行静态基础检查：
     - `cd F:\zhangshu\backend`
     - `.\.venv\Scripts\Activate.ps1`
     - `python -m compileall app`
     - `cd F:\zhangshu\frontend`
     - `npm run type-check`
   - 如果上一轮代码存在语法错误或 type-check 失败，先停止并反馈，不要在错误基础上继续叠加交互改动。

2. 重构搜索与筛选布局
   - 修改 `frontend/src/pages/settings/ProjectSettingsPage.vue`。
   - 在 `page-header` 下方、错误/成功提示上方，新增顶部工具条，例如 `.settings-toolbar`。
   - 将当前左侧 `.filters` 中的 keyword 搜索框移动到顶部工具条。
   - 搜索框继续绑定 `filters.keyword`。
   - 搜索触发方式建议：
     - 保留一个“搜索”按钮，点击调用 `handleApplyFilters()`。
     - 可支持 `@keyup.enter="handleApplyFilters"`。
   - 从左侧 `list-panel` 删除常驻的筛选 select，左侧只保留树、空状态和必要说明。

3. 实现筛选按钮与筛选面板
   - 在 `<script setup>` 中新增 UI 状态：
     - `const isFilterPanelOpen = ref(false)`
   - 顶部工具条新增“筛选”按钮：
     - 点击切换 `isFilterPanelOpen`。
     - 按钮文案使用简体中文：`筛选`。
     - 可显示激活数量，例如 `筛选（2）`。
   - 新增计算属性：
     - `activeFilterCount`，统计 `item_type`、`canon_status`、`importance` 中非空项数量，不统计 keyword。
   - 筛选面板中放置原有三个 select：
     - 类型：绑定 `filters.item_type`。
     - 确认状态：绑定 `filters.canon_status`。
     - 重要程度：绑定 `filters.importance`。
   - 筛选面板按钮：
     - “应用筛选”：调用 `handleApplyFilters()` 后关闭面板。
     - “清空筛选”：清空 `item_type`、`canon_status`、`importance`，保留或不保留 keyword 需明确；建议只清空筛选项，不清空搜索词。
   - 新增函数：
     - `handleClearStructuredFilters()`：清空三个筛选字段并调用 `refreshSettings()`。
   - 关闭逻辑：
     - 点击“应用筛选”关闭。
     - 可选：点击页面其它位置关闭，但不是必须，避免额外复杂度。

4. 增加拖拽状态
   - 在 `ProjectSettingsPage.vue` `<script setup>` 中新增：
     - `const draggedSettingId = ref<string | null>(null)`
     - `const dragOverFolderId = ref<string | null>(null)`
     - `const isMovingSetting = ref(false)`
   - 新增 helper：
     - `function isPage(setting: SettingItem): boolean`
     - `function isFolder(setting: SettingItem): boolean`
     - `function getSettingById(id: string): SettingItem | undefined`
     - `function getFolderDefaultType(folder: SettingItem): SettingItemType | null`
   - 不新增全局 store；状态保持在页面组件内。

5. 设定页作为拖拽源
   - 在左侧树 `v-for` 的 `.setting-card` 上增加条件属性：
     - `:draggable="item.setting.node_kind === 'page' && !isSaving && !isMovingSetting"`
   - 绑定事件：
     - `@dragstart="handleSettingDragStart($event, item.setting)"`
     - `@dragend="handleSettingDragEnd"`
   - `handleSettingDragStart(event, setting)`：
     - 如果不是 page，阻止拖拽。
     - 设置 `draggedSettingId.value = setting.id`。
     - 使用 `event.dataTransfer?.setData('text/plain', setting.id)`。
     - 设置 `event.dataTransfer.effectAllowed = 'move'`。
   - `handleSettingDragEnd()`：
     - 清空 `draggedSettingId` 和 `dragOverFolderId`。

6. 目录作为拖放目标
   - 仅目录节点可接收 drop。
   - 在 `.setting-card` 上按目录条件绑定：
     - `@dragover.prevent="handleFolderDragOver($event, item.setting)"`
     - `@dragleave="handleFolderDragLeave(item.setting)"`
     - `@drop.prevent="handleSettingDrop($event, item.setting)"`
   - `handleFolderDragOver(event, folder)`：
     - 如果 `folder.node_kind !== 'folder'`，返回。
     - 如果没有 `draggedSettingId`，返回。
     - 设置 `dragOverFolderId.value = folder.id`。
     - 设置 `event.dataTransfer.dropEffect = 'move'`。
   - `handleFolderDragLeave(folder)`：
     - 如果当前 hover 是该 folder，清空 `dragOverFolderId`。
   - 模板 class 增加：
     - `dragging`：当前 page 是拖拽源。
     - `drop-target`：当前 folder 是悬停目标。
   - CSS 中提供清晰但克制的视觉反馈，不改变布局尺寸。

7. 拖放前检查与确认
   - 新增 `async function handleSettingDrop(event: DragEvent, targetFolder: SettingItem)`。
   - 执行顺序：
     - 从 `draggedSettingId` 或 `event.dataTransfer.getData('text/plain')` 获取 page id。
     - 获取 dragged page；若不存在，直接清理状态。
     - 如果目标不是 folder，直接清理状态。
     - 如果 page 当前 `parent_id === targetFolder.id`，直接清理状态，不调用 API。
     - 如果 `targetFolder.folder_default_item_type` 存在且与 `page.item_type` 不同，进入确认流程。
   - 确认流程建议使用 `window.confirm` 做第一版，不新增 modal 组件：
     - 文案示例：
       `该设定当前类型为「人物」，目标目录默认类型为「世界观」。是否移动后自动更改为「世界观」？选择“确定”将自动更改类型，选择“取消”将仅移动并保留原类型。`
     - 注意：`window.confirm` 只有确定/取消两项；这里取消被解释为“仅移动保留原类型”。如果需要真正取消移动，可改用浏览器 confirm 两次或自定义轻量弹窗。
   - 更推荐的三态交互：
     - 实现组件内轻量确认面板 `pendingMove`，提供三个按钮：
       - `自动更改类型`
       - `仅移动`
       - `取消`
     - 不新增新文件，直接在 `ProjectSettingsPage.vue` 内实现。
   - 本任务建议采用三态轻量确认面板，避免把“取消”误解为“保留类型并移动”。

8. 三态确认面板实现
   - 新增状态：
     - `pendingMove = ref<{ page: SettingItem; targetFolder: SettingItem } | null>(null)`
   - 当检测到类型不同时：
     - 设置 `pendingMove.value = { page, targetFolder }`。
     - 不立即调用 API。
   - 在模板中增加一个小型确认区域或 modal，用户可见文案为简体中文：
     - 标题：`确认移动设定`
     - 正文说明当前类型和目标目录默认类型。
     - 按钮：
       - `自动更改类型`
       - `仅移动`
       - `取消`
   - 新增函数：
     - `confirmMoveWithTypeChange()`
     - `confirmMoveKeepType()`
     - `cancelPendingMove()`

9. 执行移动
   - 新增 `async function moveSettingToFolder(page, targetFolder, mode)`。
   - `mode === 'inherit'`：
     - 调用 `updateSetting(page.id, { parent_id: targetFolder.id })`。
   - `mode === 'keep'`：
     - 调用 `updateSetting(page.id, { parent_id: targetFolder.id, item_type: page.item_type })`。
   - 移动期间：
     - `isMovingSetting.value = true`
     - 清空 `errorMessage` 和 `successMessage`
   - 成功后：
     - `await refreshSettings()`
     - 将 `selectedSetting.value` 更新为后端返回的 updated setting，或从 `allSettings` 中重新定位。
     - 设置 `selectedFolderId.value = targetFolder.id`。
     - 显示成功提示：`设定已移动`。
   - 失败后：
     - 使用 `getErrorMessage(error, '移动设定失败。')`。
   - finally：
     - 清空拖拽状态和 `pendingMove`。
     - `isMovingSetting.value = false`。

10. 搜索与拖拽交互边界
    - 如果当前有搜索词或筛选条件，拖拽移动成功后仍保持当前搜索/筛选条件。
    - 如果移动后的 page 因筛选条件不再可见，这是正常行为；成功提示仍要显示。
    - 过滤后的树必须继续保留匹配项祖先目录，沿用当前 `buildTree()` 思路。
    - drop 目标只来自当前可见树；不需要额外做“移动到隐藏目录”的交互。

11. CSS 与可访问性
    - 顶部工具条样式：
      - `.settings-toolbar`
      - `.search-group`
      - `.filter-menu`
      - `.filter-panel`
    - 拖拽样式：
      - `.setting-card.dragging`
      - `.setting-card.drop-target`
    - 确认面板样式：
      - `.move-confirm-panel` 或复用现有 panel/card 风格。
    - 保证按钮文字不溢出，移动端工具条可换行。
    - 不使用 emoji 作为唯一信息来源；如保留图标，也要有文本可读。

12. 测试补充
    - 修改或新增 `frontend/src/__tests__/settings-tree.spec.ts`。
    - 最低覆盖：
      - `activeFilterCount` 或筛选状态清理逻辑可测试则测试。
      - 拖拽移动类型判断 helper：当 page 类型与目标目录默认类型不同，应进入 pending confirm。
      - `ChapterSettingPanel` 原有 `node_kind: 'page'` 行为不要回退。
    - 如果当前测试环境难以直接测 Vue 拖拽 DOM 事件，至少抽出纯 helper 函数在组件内或测试文件中通过可测试方式验证；不要为了测试引入新依赖。

13. 执行报告
    - Claude Code 完成后覆盖写入 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
    - 报告必须包含：
      - 实际修改文件。
      - 是否遵守“不新增依赖、不改后端 API”的决策。
      - 拖拽移动时三种路径：直接移动、自动更改类型、保留原类型。
      - 验证命令和结果。
      - 未解决风险。

# Constraints

- 不要修改业务代码以外的无关模块。
- 不要新增拖拽库或 UI 库。
- 不要新增后端 API，除非发现当前 `PATCH /api/settings/{setting_id}` 无法满足移动；如必须新增，先停止反馈。
- 不要支持目录拖拽，本任务只支持设定页拖到目录。
- 不要改动数据库结构。
- 不要把目录/类型继承规则搬到前端作为唯一校验；后端仍是最终规则。
- 不要让筛选面板占据左侧树空间；左侧应专注展示树。
- 不要破坏章节设定绑定只展示 page 的行为。
- 用户可见文案必须是简体中文。
- 代码标识符、API 路径、数据库表名保持英文。
- 不要提交本地数据库、日志、密钥、临时文件或构建产物。

# Verification Commands

执行前基础检查：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
python -m compileall app
```

前端验证：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit
npm run build
```

如后端虚拟环境可用，补充运行：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
pytest tests/test_settings_tree.py -v
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

- 打开项目“设定”页面。
- 确认搜索框位于页面上方，而不是左侧树面板内。
- 点击“筛选”按钮，确认出现类型、确认状态、重要程度筛选项。
- 应用筛选后，树保留匹配结果及其祖先目录。
- 清空筛选后，搜索词按计划保留，结构化筛选项清空。
- 拖拽一个设定页到同类型目录，确认可直接移动。
- 拖拽一个人物类型设定页到世界观或历史目录，确认移动前出现类型变更确认。
- 选择“自动更改类型”，确认移动后设定类型变为目标目录默认类型。
- 选择“仅移动”，确认移动后目录改变但设定类型保持原值。
- 选择“取消”，确认不移动。
- 尝试拖拽目录，确认不会触发移动。
- 尝试把设定页拖到设定页上，确认不会触发移动。

# Acceptance Criteria

- 搜索框已移动到设定页面上方。
- 左侧树面板不再常驻展示多个筛选 select。
- “筛选”按钮可打开和关闭筛选面板。
- 筛选面板可按类型、确认状态、重要程度筛选。
- 可清空结构化筛选条件。
- 左侧树中设定页卡片可被拖拽。
- 左侧树中目录可作为拖放目标。
- 目录不能被当作设定页拖拽移动。
- 设定页不能被拖放到另一个设定页下。
- 拖放到同一目录不发起无意义 API 请求。
- 拖放到目标目录默认类型与当前类型一致时，直接移动。
- 拖放到目标目录默认类型与当前类型不一致时，必须先提示用户。
- 用户可选择自动更改类型、仅移动保留类型、取消移动。
- 移动成功后刷新树并保留当前搜索/筛选状态。
- 移动失败时显示错误提示，不产生前端假状态。
- 不新增依赖。
- 前端 type-check、unit test、build 通过；如后端测试无法运行，执行报告必须说明原因。

# Risks and Watchpoints

- Claude 上一轮报告提到后端 pytest 未运行成功，本次执行前应先确认现有代码基础状态，避免在潜在错误上叠加 UI 改动。
- 当前 PowerShell 输出显示中文乱码，实际编辑时必须确保 UTF-8，用户可见中文不可乱码。
- `window.confirm` 无法表达三态选择，本任务建议使用组件内轻量确认面板，否则“取消”语义会不清晰。
- 原生 HTML Drag and Drop 在移动端支持较弱；本任务验收重点是桌面端。移动端至少不能破坏页面布局。
- 当前 `update_setting()` 的类型继承依赖“是否显式传 `item_type`”。前端必须严格区分自动更改类型和保留原类型两种 payload。
- 搜索/筛选结果可能让移动后的设定页暂时不可见，这是可接受行为，但需要成功提示。
- 如果目标目录没有默认类型，应保留当前类型并直接移动。
- 如果用户拖拽时选中了系统目录作为目标，应允许设定页移入系统目录，因为系统目录不能删除但可以作为分类目录。
- 不要为了拖拽移动引入排序语义；本任务不改变 `order_index`。
- 不要把拖拽移动写成直接修改本地数组后再调用 API；应以后端返回和 `refreshSettings()` 为准。

# Review Checklist

- 是否只修改计划列出的前端文件。
- 是否没有新增后端 API 或数据库字段。
- 是否没有引入新依赖。
- 搜索框是否位于顶部工具条。
- 左侧树是否移除了常驻筛选 select。
- 筛选按钮是否能打开筛选面板。
- 筛选应用和清空行为是否符合计划。
- page 节点是否可拖拽。
- folder 节点是否是唯一 drop target。
- folder 节点是否不会被拖拽移动。
- page -> page drop 是否被忽略。
- page -> same folder 是否不会发起 PATCH。
- 类型不一致时是否出现三态确认。
- “自动更改类型”是否不传 `item_type`。
- “仅移动”是否显式传原 `item_type`。
- “取消”是否不调用 API。
- 移动成功后是否刷新数据而不是只改本地数组。
- 错误提示是否清晰。
- 中文 UI 文案是否为简体中文且没有乱码。
- 前端 type-check、test、build 是否通过。
- 执行报告是否覆盖写入 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
