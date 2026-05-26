---
date: 2026-05-23
task: 伏笔模块 UI 调整 — 搜索上移、筛选折叠、树形按卷/章节展示
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

# Claude Code 执行报告：伏笔模块 UI 调整

## 1. 实际修改文件列表

| 文件 | 操作 | 说明 |
|---|---|---|
| `frontend/src/pages/clues/ProjectCluesPage.vue` | 修改 | 搜索上移、筛选折叠到按钮面板、左侧改为树形结构、新增埋设/回收分组切换 |
| `frontend/src/__tests__/clues-tree.spec.ts` | 新建 | 伏笔树分组逻辑与筛选计数的纯函数测试 |

## 2. 后端/API/依赖变更

- 未修改后端任何文件（model / schema / repository / service / API 均未动）。
- 未新增 API 端点。
- 未新增数据库字段或迁移。
- 未新增任何 npm 依赖。

## 3. 搜索上移和筛选按钮交互说明

- 搜索框从左侧 `.filters` 区域移到页面顶部 `.clues-toolbar` 内的 `.search-group`。
- 搜索 input 支持回车触发 `handleApplyFilters()`，旁边有"搜索"按钮。
- 筛选按钮位于搜索组右侧，显示"筛选"；有结构化筛选时显示"筛选（N）"，按钮高亮。
- 点击筛选按钮展开 `.filter-panel` 浮动面板，包含：
  - 伏笔状态 select
  - 可见程度 select
  - 重要程度 select
  - "清空筛选"按钮（仅清空结构化筛选，保留搜索词）
  - "应用筛选"按钮（应用后关闭面板）
- `activeFilterCount` 只统计 status / visibility / importance，不统计 keyword。

## 4. 伏笔树按埋设/回收章节分组的实现说明

- 新增分组模式切换：`.tree-mode-control` 内两个 `.mode-button`（"按埋设章节"/"按回收章节"），默认"按埋设章节"。
- 切换分组模式时：
  - 不重新请求 API。
  - 重置 `expandedTreeKeys` 并调用 `autoExpandTree()` 重新展开。
  - 已选中伏笔如仍在列表中保持 active。
- 树由 `clueTree` computed 派生，结构为扁平 `ClueTreeNode[]`，包含三种 `kind`：
  - `'volume'`：卷节点，显示卷标题和伏笔计数。
  - `'chapter'`：章节节点，缩进一级，显示章节标题和伏笔计数。
  - `'clue'`：伏笔卡片，缩进二级，点击打开右侧编辑器。
- 分组依据：
  - 按埋设章节 → `clue.setup_chapter_id`
  - 按回收章节 → `clue.payoff_chapter_id`
- 特殊分组：
  - 未绑定章节 → `__unbound__` 卷节点，标题为"未绑定埋设章节"或"未绑定回收章节"。
  - 章节已删除或不存在 → `__unknown__` 卷节点，标题为"未知章节"。
  - 章节无卷 → `__unvolumed__` 卷节点，标题为"未分卷"。
- 排序规则：
  - 正常卷按 `volume.order_index` 升序，再按标题排序。
  - 特殊卷节点（未绑定、未知、未分卷）排在正常卷之后。
  - 章节按 `chapter.order_index` 升序，再按标题排序。
  - 伏笔保持后端返回顺序。
- 展开/折叠状态由 `expandedTreeKeys: Set<string>` 管理，Vue 响应式通过重新赋值 Set 实现。
- 初始加载和分组切换时调用 `autoExpandTree()`，展开所有包含伏笔的卷和章节节点。

## 5. 编辑表单保持不变

- 右侧伏笔详情表单字段未变：标题、状态、可见程度、重要程度、埋设章节、回收章节、描述、回收计划、实际回收、备注。
- 创建/保存/删除逻辑未变。
- 关系图打开逻辑未变。
- `MaterialLinkPanel` 未变。

## 6. 验证命令和结果

| 验证项 | 命令 | 结果 |
|---|---|---|
| 前端类型检查 | `npm run type-check` | ✅ 通过 |
| 前端单元测试 | `npm run test:unit -- --run` | ✅ 20 tests passed (3 files) |
| 前端生产构建 | `npm run build` | ✅ type-check + vite build 均通过 |
| 后端语法检查 | `python -m compileall app` | ✅ 无语法错误 |

## 7. 测试覆盖

新增 `frontend/src/__tests__/clues-tree.spec.ts`，12 个测试用例：

- 按埋设章节分组：正确进入卷/章节、未绑定分组、未知章节分组、未分卷分组。
- 按回收章节分组：正确进入卷/章节、未绑定回收分组。
- 排序：卷按 order_index 排序、特殊分组排在后面。
- `activeFilterCount`：不计 keyword，只计 status/visibility/importance。

## 8. 未完成项或风险

- 无未完成项。
- 风险：如果后续需要拖拽移动伏笔到章节，需新增交互逻辑（本任务不做）。
- 已知限制：后端 venv 无法在 Git Bash 中直接激活，`python -m compileall` 通过 `.venv/Scripts/python.exe` 绝对路径执行。
