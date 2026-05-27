---
date: 2026-05-26
archived_at: 2026-05-26
archive_reason: superseded by cloud network resilience planning
task: 统一前端时间显示格式
codex_plan: N/A（Codex Plan 不存在此任务，为用户直接指派的 bug 修复）
---

## Task Summary

修复前端时间显示不一致的 bug：10 个 Vue 组件各自实现了日期格式化函数，产出 3 种不同格式（Intl locale、zh-CN 硬编码、手动 pad 拼接），导致用户在同一界面看到不同时间格式。

## Files Changed

- 新增：`frontend/src/shared/utils/formatDateTime.ts` — 统一日期格式化工具函数
- 修改：`frontend/src/pages/projects/ProjectsPage.vue` — 移除本地 `formatUpdatedAt`，改用共享 `formatDateTime`
- 修改：`frontend/src/pages/projects/ProjectDetailPage.vue` — 移除本地 `formatDate`，改用共享 `formatDateTime`
- 修改：`frontend/src/pages/versions/ProjectVersionsPage.vue` — 移除本地 `formatDate`，改用共享 `formatDateTime`
- 修改：`frontend/src/pages/search/SearchPage.vue` — 移除本地 `formatUpdatedAt`，改用共享 `formatDateTime`
- 修改：`frontend/src/features/cloud/CloudBackupPanel.vue` — 移除本地 `formatDate`，改用共享 `formatDateTime`
- 修改：`frontend/src/features/outlines/OutlineEditor.vue` — 移除本地 `formatDate`，改用共享 `formatDateTime`
- 修改：`frontend/src/features/stats/ChapterRankingTable.vue` — 移除本地 `formatUpdatedAt`（zh-CN 硬编码 + 缺年份），改用共享 `formatDateTime`
- 修改：`frontend/src/features/chapters/ChapterEditor.vue` — 移除本地 `formatDateTime`（手动 pad），改用共享 `formatDateTimeFull`
- 修改：`frontend/src/features/chapters/ChapterVersionPanel.vue` — 移除本地 `formatDateTime`（手动 pad），改用共享 `formatDateTimeFull`
- 修改：`frontend/src/features/chapters/ChapterVersionPreviewDialog.vue` — 移除本地 `formatDateTime`（手动 pad），改用共享 `formatDateTimeFull`

## Implementation Notes

### 共享工具设计

`shared/utils/formatDateTime.ts` 导出两个函数：

- `formatDateTime`：短格式（`Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })`），适用于列表、卡片等常规时间展示
- `formatDateTimeFull`：完整格式（含秒），适用于版本历史等需要精确时间的场景

两个函数都接受 `string | null | undefined`，空值返回 `'—'`。`Intl.DateTimeFormat` 实例在模块顶层创建，避免重复实例化。

### Group 分配

| 组 | 原格式 | 文件数 | 改用 |
|---|---|---|---|
| A | `Intl.DateTimeFormat(undefined, ...)` 重复 6 份 | 6 | `formatDateTime` |
| B | `Intl.DateTimeFormat('zh-CN', ...)` 缺年份 | 1 | `formatDateTime` |
| C | 手动 `pad()` 拼接 `YYYY-MM-DD HH:mm:ss` | 3 | `formatDateTimeFull` |

### Bug 修复细节

1. **ChapterRankingTable.vue**：原硬编码 `'zh-CN'` locale 且缺少年份字段，现统一为浏览器 locale + 完整日期
2. **ChapterEditor / ChapterVersionPanel / ChapterVersionPreviewDialog**：原手动拼接不随浏览器 locale 适配，现统一为 `Intl` 格式化
3. **DRY 违反**：10 处重复代码合并为 1 个共享模块

## Deviations from Codex Plan

无（Codex Plan 不存在此任务）。

## Verification Commands Run

- 代码审查（Grep 验证）：
  - `Intl.DateTimeFormat` 在 `.vue` 文件中 → 0 匹配 ✅（全部移入共享工具）
  - `function formatDate|formatUpdatedAt|formatDateTime` 在 `.vue` 文件中 → 仅 `formatDateForFilename`（文件名用途，不受影响）✅
  - `formatDateTime` / `formatDateTimeFull` 导入和使用 → 10 个文件全部正确 ✅
- `npm run type-check` → ⚠️ 无法执行（sandbox 环境无 shell 命令访问权限）

## Verification Results

代码审查验证通过。`npm run type-check` 因 sandbox 限制无法运行，需要在本地手动执行确认。

修改不涉及类型签名变更（所有替换的函数都接受 `string` 参数，新函数接受 `string | null | undefined` 是超集），类型检查预期通过。

## Known Issues

- 无法在当前环境运行 `npm run type-check`，需要用户本地验证
- `formatDateTimeFull` 的输出格式（如 `2026/05/26 14:30:00`）与原手动拼接格式（`2026-05-26 14:30:00`）略有差异（分隔符从 `-` 变为 `/`），这是 `Intl.DateTimeFormat` 在中文 locale 下的标准行为

## Suggested Next Review Points for Codex

1. 是否需要将 `formatDateTimeFull` 的输出格式调整为与原 `YYYY-MM-DD HH:mm:ss` 一致（使用自定义格式化而非 `Intl`）
2. 是否还有其他前端格式化函数可以抽取为共享工具（如 `formatBytes` 在 `CloudBackupPanel.vue` 中）
