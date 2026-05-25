---
date: 2026-05-23
task: Design System Round 2 — Convergence
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

设计系统第二轮收敛：补齐全局 token 和 utility 类，在 6 个弹窗中实际采用共享 utility，清理 5 个管理页面和 3 个写作上下文组件的硬编码颜色，提升 ProjectsPage 可访问性。

## Files Changed

### Step 2: 全局 token 和 utility 补齐
- 修改：`frontend/src/style.css`
  - 新增 token：`--zs-color-backdrop`、`--zs-shadow-dialog`、`--zs-shadow-card-hover`、`--zs-focus-ring`、`--zs-color-overlay-text`
  - dark 主题新增 `--zs-color-backdrop`、`--zs-shadow-dialog`、`--zs-shadow-card-hover` 覆盖
  - `.zs-dialog` 改用 `var(--zs-color-backdrop)`，`.zs-dialog-content` 改用 `var(--zs-shadow-dialog)`
  - 新增 utility 类：`.zs-button-ghost`、`.zs-icon-button`、`.zs-state`（含 `[data-state]` 变体）、`.zs-state-compact`、`.zs-meta`、`.zs-form-grid`、`.zs-form-grid-row`、`.zs-overlay`、`.zs-menu`、`.zs-menu-item`

### Step 3: 弹窗组件采用共享 utility + token 化
- 修改：`frontend/src/features/projects/CreateProjectDialog.vue`
- 修改：`frontend/src/features/projects/EditProjectDialog.vue`
- 修改：`frontend/src/features/volumes/CreateVolumeDialog.vue`
- 修改：`frontend/src/features/volumes/EditVolumeDialog.vue`
- 修改：`frontend/src/features/outlines/CreateOutlineDialog.vue`
- 修改：`frontend/src/features/outlines/EditOutlineDialog.vue`

**统一变更内容：**
- 模板：`dialog-backdrop` → `zs-dialog`，`dialog` → `zs-dialog-content`，`dialog-header` → `zs-dialog-header`，`dialog-actions` → `zs-dialog-footer`，`icon-button` → `zs-icon-button`，`primary-button` → `zs-button zs-button-primary`，`secondary-button` → `zs-button zs-button-secondary`，表单 `<label>` 添加 `class="zs-field"`
- scoped CSS：移除被 utility 覆盖的块（`.dialog-backdrop`、`.dialog`、`.dialog-header`、`.dialog-actions`、`button`、`.icon-button`、`.primary-button`、`.secondary-button`、`label`、`input/textarea/select` + `:focus`）
- 所有硬编码颜色替换为 token

### Step 4: 项目组件主题适配
- 修改：`frontend/src/features/projects/ProjectCoverUploader.vue` — 替换 8 组硬编码颜色（边框、背景、文字、危险态、提示色）
- 修改：`frontend/src/features/projects/ProjectTagInput.vue` — 替换 11 组硬编码颜色（标签 chip、建议 chip、输入框、按钮）
- 修改：`frontend/src/pages/projects/ProjectsPage.vue` — 添加 `aria-expanded`、`aria-controls` 和 `id` 属性提升筛选面板可访问性

### Step 5: 页面级管理视图统一
- 修改：`frontend/src/pages/projects/ProjectDetailPage.vue` — 状态标签变体色 token 化（`var()` fallback 保留）
- 修改：`frontend/src/pages/characters/ProjectCharactersPage.vue` — ~25 处颜色替换（横幅、卡片、按钮、标签、边框等）
- 修改：`frontend/src/pages/settings/ProjectSettingsPage.vue` — ~18 处颜色替换 + 修复遗漏的 `#dbeafe`
- 修改：`frontend/src/pages/clues/ProjectCluesPage.vue` — ~20 处颜色替换
- 修改：`frontend/src/pages/outlines/ProjectOutlinePage.vue` — ~20 处颜色替换

### Step 6: 写作上下文与大纲节点视觉优化
- 修改：`frontend/src/features/writing/ChapterContextSection.vue` — 3 处颜色替换
- 修改：`frontend/src/features/writing/ChapterContextSummary.vue` — 14 处颜色替换
- 修改：`frontend/src/features/outlines/ChapterOutlineNode.vue` — 7 处颜色替换

## Implementation Notes

### 新增 token 值
| Token | 默认值 | 暗色主题 |
|---|---|---|
| `--zs-color-backdrop` | `rgb(15 23 42 / 54%)` | `rgb(0 0 0 / 60%)` |
| `--zs-shadow-dialog` | `0 24px 80px rgb(15 23 42 / 22%)` | `0 24px 80px rgb(0 0 0 / 40%)` |
| `--zs-shadow-card-hover` | `0 4px 16px rgb(15 23 42 / 12%)` | `0 4px 16px rgb(0 0 0 / 30%)` |
| `--zs-focus-ring` | `var(--zs-color-primary-soft)` | 继承 |
| `--zs-color-overlay-text` | `#ffffff` | 继承 |

### 弹窗 utility 采用效果
6 个弹窗的 scoped CSS 显著缩减。以 CreateProjectDialog 为例：原始 scoped CSS 约 150 行 → 缩减至约 50 行（仅保留表单布局、field-error、@media）。

### 主题入口评估（Step 7）
当前 `ThemeSwitcher` 固定在右上角（`top: 16px, right: 16px, z-index: 90`），移动端固定在右下角。评估结果：
- 桌面端：页面 header 使用 `padding: 24px`，返回链接在左侧，操作按钮在左侧，不与右上角主题切换冲突
- 移动端：底部固定不与页面内容冲突
- z-index 90 低于弹窗 200，不会被弹窗遮挡
- **结论：当前定位合理，无需调整**

### ProjectsPage 可访问性改进
- 筛选按钮新增 `:aria-expanded="isFilterPanelOpen"`
- 筛选面板新增 `id="projects-filter-panel"` 和按钮的 `aria-controls="projects-filter-panel"`

## Deviations from Codex Plan

无偏差。所有 Step 2-9 均按计划范围执行。

**未采纳的建议及原因：**
- **ProjectsPage Escape 关闭筛选面板和点击外部关闭**：计划标注"如果实现会明显增加复杂度，可以只在执行报告中说明暂不采纳"。当前筛选面板是静态展开的 div（不是浮层菜单），Escape 关闭和外部点击关闭的实际价值有限，暂不采纳。
- **ProjectsPage 局部按钮迁移到共享 utility**：当前 ProjectsPage 的 scoped 按钮样式与全局 `.zs-button` 存在细微差异（min-height、font-weight），贸然替换可能影响页面视觉节奏。本轮仅做颜色 token 化，布局迁移留待后续批次。

## Verification Commands Run

- `npm run type-check` → ✅
- `npm run test:unit -- --run` → ✅ (51 tests, 5 files)
- `npm run build` → ✅ (198 modules, CSS 155.63KB, JS 378.71KB)

## Verification Results

全部通过。CSS 产出从上一轮的 156.38KB 降至 155.63KB（减少 0.75KB），说明 utility 采用和 token 替换确实减少了重复 CSS。

## 剩余硬编码颜色清单

### 合法保留（非 UI 颜色）
| 文件 | 行 | 值 | 说明 |
|---|---|---|---|
| `GraphInspector.vue` | 167 | `#4f7cff` | 颜色选择器 placeholder，用户输入示例 |
| `ProjectTimelinePage.vue` | 1750 | `#6B8AFD` | 颜色选择器 placeholder，用户输入示例 |
| `ProjectDetailPage.vue` | 1132-1140 | `#eef2ff`, `#f0f4ff`, `#3730a3` | `var()` fallback 值，正确用法 |

### 范围外文件（未在本轮处理）
无。本轮覆盖了计划中列出的所有文件。部分页面仍有 `rgb(...)` 值（弹窗遮罩和阴影），这些已通过 token 引用（`var(--zs-color-backdrop)` 和 `var(--zs-shadow-dialog)`），无需替换。

## Known Issues

- **CSS fallback 值一致性**：`ProjectDetailPage.vue` 中有 `var(--zs-color-info-soft, #eef2ff)` 和 `var(--zs-color-info-soft, #f0f4ff)` 两处不同 fallback。功能上不影响（token 存在时 fallback 不生效），但不够统一。可在后续清理中移除 fallback。
- **GraphCanvas / GraphNode**：这些是画布组件，使用 `--zs-canvas-*` token，不在本轮范围内。

## Suggested Next Review Points for Codex

1. **utility 类实际采用率**：本轮新增的 `.zs-button-ghost`、`.zs-state`、`.zs-meta`、`.zs-form-grid`、`.zs-overlay`、`.zs-menu`、`.zs-menu-item` 尚未被组件采用（仅声明在 style.css 中）。建议在后续新增功能时优先使用这些 utility，或在下一轮做定向迁移。
2. **CSS fallback 值清理**：部分文件使用 `var(--zs-color-*, #hex)` 双重写法，可考虑统一移除 fallback 以简化 CSS。
3. **Canvas token 审计**：确认所有画布组件（GraphCanvas、TimelineCanvas）正确使用 `--zs-canvas-*` 而非 `--zs-color-*`。
4. **响应式人工验证**：建议 Codex 提醒人工验证 390px/768px/1280px/1440px 下的弹窗和筛选菜单行为。
