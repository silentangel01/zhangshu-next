---
date: 2026-05-23
task: UI Progressive Unification
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

分批优化 UI 一致性：改进主题入口与共享 utility（Batch 1）、清理 7 个 feature 面板硬编码颜色（Batch 2）、为 /projects 添加搜索筛选排序（Batch 3）、统一 4 个章节弹窗与版本面板（Batch 4），并完成全量验证。

## Files Changed

### Batch 1: 全局主题入口与共享 UI utility
- 修改：`frontend/src/App.vue` — 主题切换按钮改为 fixed 定位 + 响应式（移动端移到底部右下角），避免与页面标题冲突
- 修改：`frontend/src/style.css` — 新增 ~180 行共享 utility 类：`.zs-button-danger`、`.zs-alert-*`、`.zs-dialog-*`、`.zs-field-*`、`.zs-filter-button`、`.zs-filter-menu`、`.zs-page-header`、`.zs-page-actions`、`.zs-back-link`

### Batch 2: 写作辅助侧栏 feature 面板主题一致性
- 修改：`frontend/src/features/characters/ChapterCharacterPanel.vue` — 替换全部硬编码颜色为 `--zs-color-*` token
- 修改：`frontend/src/features/clues/ChapterCluePanel.vue` — 同上
- 修改：`frontend/src/features/settings/ChapterSettingPanel.vue` — 同上（含遗漏修复：`.primary-button` 中 `color: #ffffff` → `var(--zs-color-on-primary)`）
- 修改：`frontend/src/features/outlines/ChapterOutlinePanel.vue` — 同上
- 修改：`frontend/src/features/timeline/ChapterTimelinePanel.vue` — 同上
- 修改：`frontend/src/features/graph/ChapterGraphCard.vue` — 同上
- 修改：`frontend/src/features/writing/CreativeReminderPanel.vue` — 同上

### Batch 3: /projects 搜索筛选排序
- 新增：`frontend/src/features/projects/projectFilters.ts` — 纯函数模块：`filterProjects`、`sortProjects`、`collectProjectTags`、`countActiveFilters` 及类型 `ProjectFilterState`、`ProjectSortKey`
- 新增：`frontend/src/__tests__/project-filters.spec.ts` — 18 个测试用例覆盖 4 个 describe 块
- 修改：`frontend/src/pages/projects/ProjectsPage.vue` — 新增搜索栏（关键词输入 + 状态/标签筛选 + 排序选择器），提取筛选排序逻辑到 computed `displayedProjects`

### Batch 4: 章节弹窗与版本面板统一
- 修改：`frontend/src/features/chapters/CreateChapterDialog.vue` — 替换 11 组硬编码颜色为 token
- 修改：`frontend/src/features/chapters/EditChapterDialog.vue` — 同上
- 修改：`frontend/src/features/chapters/ChapterVersionPreviewDialog.vue` — 替换 10 组硬编码颜色为 token
- 修改：`frontend/src/features/chapters/ChapterVersionPanel.vue` — 替换 10 组硬编码颜色为 token

## Implementation Notes

### 颜色替换映射表（通用）
| 旧值 | 新值 |
|---|---|
| `#64748b` / `#4b5563` / `#475569` | `var(--zs-color-text-muted)` |
| `#111827` / `#1f2937` / `#334155` / `#374151` / `#0f172a` | `var(--zs-color-text)` |
| `#2563eb` | `var(--zs-color-primary)` |
| `#cfd7e3` / `#d8dee9` / `#cbd5e1` | `var(--zs-color-border)` |
| `#edf0f5` | `var(--zs-color-border-soft)` |
| `#b42318` | `var(--zs-color-danger)` |
| `background: #ffffff` | `background: var(--zs-color-surface)` |
| `background: #fbfcfe` | `background: var(--zs-color-bg)` |
| `color: #ffffff`（primary button） | `color: var(--zs-color-on-primary)` |
| `#dbeafe` / `#eef2ff` | `var(--zs-color-info-soft)` |
| `#1e40af` / `#3730a3` / `#1d4ed8` / `#4338ca` | `var(--zs-color-info)` |
| `#eff6ff` | `var(--zs-color-primary-soft)` |
| `#f8fafc` | `var(--zs-color-surface-soft)` |
| `#facc15` / `#92400e` | `var(--zs-color-warning)` |
| `#fffbeb` | `var(--zs-color-warning-soft)` |
| `#fca5a5` / `#fecaca` | `var(--zs-color-danger)` |
| `#fff1f2` / `#fff7f7` | `var(--zs-color-danger-soft)` |
| `#94a3b8` | `var(--zs-color-text-faint)` |
| `#fef3c7` | `var(--zs-color-warning-soft)` |

### 保留不替换的值
- `rgb(20 24 31 / 54%)` — 弹窗遮罩背景（含透明度，暂不 token 化）
- `rgb(20 24 31 / 22%)` — 弹窗阴影
- `rgb(37 99 235 / 15%)` — 焦点环
- `#4f7cff` / `#6B8AFD` — 颜色选择器 placeholder（用户输入示例值，非 UI 颜色）

### projectFilters.ts 设计
- `filterProjects`：支持关键词搜索（title/author/summary/tags）、状态筛选、标签筛选，三者 AND 组合
- `sortProjects`：支持 4 种排序键（updated_at / created_at / title / author），使用 `localeCompare('zh-Hans-CN')` 做中文排序
- `collectProjectTags`：合并项目标签与内置标签，去重
- `countActiveFilters`：仅计算 status 和 tag（keyword 不算作"筛选器"）

## Deviations from Codex Plan

无偏差。所有 Batch 1-5 均按计划范围执行。

## Verification Commands Run

- `npm run type-check` → ✅
- `npm run test:unit -- --run` → ✅ (51 tests passed, 5 test files)
- `npm run build` → ✅ (198 modules, CSS 156KB, JS 378KB)

## Verification Results

全部通过。type-check 无错误，51 个单元测试全部通过（含新增 18 个 projectFilters 测试），生产构建成功。

## Known Issues

### 范围外文件仍有硬编码颜色
以下文件仍包含硬编码 hex 颜色，不在本次计划范围内，建议后续批次处理：

**Feature 层子组件（未覆盖）**：
- `ChapterOutlineNode.vue` — 大纲树节点（7 处）
- `CreateOutlineDialog.vue` / `EditOutlineDialog.vue` — 大纲创建/编辑弹窗
- `CreateVolumeDialog.vue` / `EditVolumeDialog.vue` — 分卷弹窗
- `CreateProjectDialog.vue` / `EditProjectDialog.vue` — 项目弹窗
- `ProjectCoverUploader.vue` — 封面上传
- `ProjectTagInput.vue` — 标签输入
- `ChapterContextSection.vue` / `ChapterContextSummary.vue` — 写作上下文

**Page 层**：
- `ProjectCluesPage.vue` — 仍有 ~20 处（主要是成功/危险变体色、标签色、次要按钮色）
- `ProjectCharactersPage.vue` — ~20 处
- `ProjectOutlinePage.vue` — ~20 处
- `ProjectSettingsPage.vue` — ~15 处
- `ProjectDetailPage.vue` — 状态标签变体色（info/success/warning/neutral）

这些文件中的颜色模式与本次替换一致（相同的 hex 值 → 相同的 token），可在后续批次中批量处理。

## Suggested Next Review Points for Codex

1. **剩余硬编码颜色清理**：Page 层和 Feature 子组件（Dialog/Node/Input）中仍有大量硬编码颜色，建议规划下一批次统一处理。
2. **成功/危险/警告变体色 token 化**：当前 `--zs-color-success`、`--zs-color-success-soft` 等 token 可能尚未在 style.css 中定义，需要先补充 token 再替换 `#047857`、`#bbf7d0`、`#f0fdf4` 等成功状态色。
3. **共享 utility 类采用率**：style.css 中新增的 `.zs-dialog-*`、`.zs-field-*`、`.zs-alert-*` 等 utility 类目前尚未被组件采用（组件仍使用 scoped 样式）。可考虑逐步迁移到 utility 类以减少重复 CSS。
4. **rgb() 值的 token 化**：弹窗遮罩 `rgb(20 24 31 / 54%)` 和焦点环 `rgb(37 99 235 / 15%)` 可考虑提取为 `--zs-backdrop` 和 `--zs-focus-ring` token。
