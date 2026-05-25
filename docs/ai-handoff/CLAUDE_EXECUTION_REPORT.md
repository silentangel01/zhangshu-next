---
date: 2026-05-25
task: 前端 UI 微调（时间轴/章节树/大纲弹窗/检查页面）
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

对前端 4 个模块做 UI 布局微调：压缩时间轴左侧栏标题区空白、缩窄章节树新建按钮视觉权重、扩大新建大纲条目弹窗宽度与内边距、优化检查页面检查范围横排与双列面板均衡。

## Files Changed

- 修改：`frontend/src/pages/timeline/ProjectTimelinePage.vue` — 压缩 `.left-panel` gap（从 `--zs-space-3` 降到 `--zs-space-1`），减少 `.panel-head` gap，为 `.panel-eyebrow` 添加局部行高和 margin 控制，压缩 `.track-list` gap
- 修改：`frontend/src/features/chapters/ChapterTree.vue` — 将 `.create-row` 改为虚线边框、透明背景、较浅文字色，使新建按钮视觉层级更轻；添加 hover 高亮过渡；居中文字；移除 `.volume-create-row` 冗余 `border-style: dashed`（已在 `.create-row` 统一）
- 修改：`frontend/src/features/outlines/CreateOutlineDialog.vue` — 添加 `.outline-create-dialog` 局部 class，扩大弹窗最大宽度至 `min(720px, calc(100vw - 32px))`；为表单字段和 grid 添加 `padding-inline`；`.form-grid` 最小列宽从 180px 提升到 220px
- 修改：`frontend/src/features/outlines/EditOutlineDialog.vue` — 添加 `.outline-edit-dialog` 局部 class，与新建弹窗宽度保持一致
- 修改：`frontend/src/features/outlines/OutlineEditor.vue` — `.form-grid` / `.metadata-grid` 最小列宽从 170px 提升到 200px
- 修改：`frontend/src/pages/review/ReviewCheckPage.vue` — `.page-layout` 从 flex 改为 2 列 grid（`minmax(0, 1fr) minmax(0, 1fr)`）；`.segmented-control` 从 `flex-wrap` 改为 `grid-template-columns: repeat(3, minmax(0, 1fr))` 实现桌面端三选项横排；`.segmented-control label` 添加 `white-space: nowrap` 和 `justify-content: center`；移除 `.panel` 的 `flex: 1 1 0`；更新移动端断点为单列 grid

## Implementation Notes

1. **时间轴侧栏**：`.left-panel` 与 `.detail-panel` 共享 `gap: --zs-space-3`，为 `.left-panel` 单独覆盖为 `--zs-space-1`，不影响右侧详情面板。`.panel-head` gap 从 `--zs-space-3` 降为 `--zs-space-2`，并添加 `.left-panel .panel-head { margin-bottom: var(--zs-space-1) }` 微调标题与列表的间距。

2. **章节树新建按钮**：保留按钮全宽（作为拖拽放置区域），但视觉改为虚线边框 + 透明背景 + 浅色文字 + `opacity: 0.8`，hover 时高亮为 `--zs-color-primary`。这样既不破坏拖拽交互，又让按钮视觉上更轻量。

3. **大纲弹窗**：使用局部 class `.outline-create-dialog` 覆盖全局 `.zs-dialog-content` 的 `max-width`，不修改全局样式。通过 `> .zs-field`、`> .form-grid` 选择器为表单内容添加 `padding-inline: --zs-space-5`，与 header/footer 的水平内边距对齐。编辑弹窗（EditOutlineDialog）同步扩大宽度以保持一致性。

4. **检查页面**：
   - `.page-layout` 从 flex 改为 2 列 grid，使检查面板和词库面板宽度严格均衡。
   - `.segmented-control` 改为 3 列 grid，确保桌面端三选项始终横排不换行。
   - 结果面板 `.result-panel` 与 `.page-layout` 共享相同的 `max-width: 1120px` 和 `margin: auto`，保持中心对齐。
   - 移动端（≤820px）断点更新：`.page-layout` 和 `.segmented-control` 都回退为单列。

## Deviations from Codex Plan

- 未执行可选的二级菜单收纳优化（将低频操作放入"更多"菜单）。当前页面操作入口数量适中，不构成明显拥挤，为避免降低可发现性决定跳过。
- EditOutlineDialog 和 OutlineEditor 的调整属于 Codex 计划中"仅当编辑大纲弹窗也存在同类贴边或宽度问题时"的一致性修改，已确认存在同类问题并执行。

## Verification Commands Run

- `npm run type-check` → ✅
- `npm run build` → ✅
- `npm run test:unit -- --run` → ✅ (8 files, 115 tests)

## Verification Results

全部通过，无类型错误、无构建错误、无测试回归。

## Known Issues

- 无法在本次执行中进行视觉验证（需要浏览器环境）。建议手动检查以下断点：
  - 1440px / 1366px：确认时间轴侧栏标题与列表间距合理、检查范围三选项横排、面板宽度均衡
  - 1024px：确认大纲弹窗不溢出
  - 390px：确认所有布局回退为单列，无横向滚动

## Suggested Next Review Points for Codex

1. 时间轴侧栏 `.left-panel` gap 从 `--zs-space-3` 降为 `--zs-space-1` 是否过于紧凑，建议实际页面查看。
2. 章节树新建按钮改为虚线+透明风格后，是否仍能被用户识别为可点击操作。
3. 检查页面 `.page-layout` 改为 2 列等宽 grid 后，检查面板（左侧）内容较少可能显得空旷，是否需要调整为不等宽（如 `minmax(280px, 1fr) minmax(0, 2fr)`）。
