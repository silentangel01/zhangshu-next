---
date: 2026-05-23
task: back-link-unification
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

统一章枢各页面的"返回"按钮位置、文案和目标路由。所有项目内子页面的主返回入口统一位于 `page-header` 左上角，使用 `.back-link` class，文案 `返回写作页`，目标 `/projects/{projectId}`；顶层/独立页面文案统一为 `返回项目列表`，目标 `/projects`。

## Files Changed

- 修改：`frontend/src/pages/projects/ProjectDetailPage.vue`
  - 在 header 左侧 eyebrow 前新增 `<RouterLink class="back-link" to="/projects">返回项目列表</RouterLink>`
  - 移除右侧 `header-actions` 中的 `<RouterLink class="toolbar-link" to="/projects">项目列表</RouterLink>`
  - 新增 `.back-link` CSS 块

- 修改：`frontend/src/pages/imports/ImportPage.vue`
  - 将原 header 右侧 `secondary-link` 返回入口移至左侧 `.back-link`
  - 文案从 `返回项目` 改为 `返回项目列表`
  - 新增 `.back-link` CSS 块

- 修改：`frontend/src/pages/imports/ProjectBackupPage.vue`
  - 文案从条件判断 `返回项目` / `返回项目列表` 改为 `返回写作页` / `返回项目列表`
  - 移除右侧 `secondary-link` 项目列表入口（与主返回重复）

- 修改：`frontend/src/pages/search/SearchPage.vue`
  - 主返回文案从 `返回项目` 改为 `返回写作页`
  - 右侧 `secondary-link` 保留为 `项目列表`（次级入口）

- 修改：`frontend/src/pages/review/ReviewCheckPage.vue`
  - 主返回（`.back-link`）目标从 `/projects` 改为 `/projects/${projectId}`，文案从 `返回项目列表` 改为 `返回写作页`
  - 右侧 `secondary-link` 目标从 `/projects/${projectId}` 改为 `/projects`，文案从 `返回写作页` 改为 `项目列表`
  - 实质上互换了两个链接的目标路由

- 修改：`frontend/src/pages/timeline/ProjectTimelinePage.vue`
  - 移除工具栏操作区内重复的 `<RouterLink class="toolbar-link" :to="...">返回写作页</RouterLink>`
  - 保留 `page-header` 左上角 `.back-link`

## Implementation Notes

- 5 个页面已符合规范，未做修改：`ProjectCharactersPage.vue`、`ProjectSettingsPage.vue`、`ProjectCluesPage.vue`、`ProjectOutlinePage.vue`、`ProjectGraphPage.vue`
- `SearchPage` 和 `ReviewCheckPage` 保留了到项目列表的次级入口（`.secondary-link`），避免导航断点
- 未修改全局样式文件 `style.css`，各页面 scoped `.back-link` 风格已视觉一致，不需要额外抽取
- 未新增组件、路由或依赖

## Deviations from Codex Plan

无。

## Verification Commands Run

- `npm run type-check` → ✅ 通过
- `npm run test:unit` → ✅ 通过（3 测试文件，20 测试用例）
- `npm run build` → ✅ 通过（184 模块，624ms）

## Verification Results

全部验证通过。构建产物：CSS 140KB (gzip 18.8KB)，JS 361KB (gzip 107.5KB)。

## Known Issues

无。

## Suggested Next Review Points for Codex

- 可选 UI 建议 A（统一页面标题区结构）已在修改页面中间接遵循，但未强制约束未来新页面。如未来新增页面较多，可考虑抽取 `PageHeader` 组件。
- `ProjectTimelinePage` 工具栏移除返回链接后，工具栏仅剩"刷新"按钮，视觉上可能略空；可后续评估是否需要补充其他操作入口。
