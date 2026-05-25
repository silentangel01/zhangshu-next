---
date: 2026-05-24
task: Knowledge UI Fix — 新建入口、布局收紧、主题修正
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

修正知识库页面三个 UI 问题：新建资料入口不够明显、页面空白过大、全局主题部分失效。仅修改前端 UI，不涉及后端逻辑、RAG、向量检索或导入功能。

## Files Changed

- 修改：`frontend/src/pages/knowledge/ProjectKnowledgePage.vue`
  - 列表面板顶部加"资料 / 新建"操作条
  - 空状态改为引导式卡片（含"新建第一条资料"按钮）
  - 空详情区加"或新建资料"按钮
  - 非浏览视图加"← 返回资料列表"路径
  - 整体 CSS 对齐 material page 规范（`--zs-space-*` token、`minmax()` grid、`--zs-radius-*`、`--zs-shadow-*`）
  - 移除 `--zs-canvas-bg` 误用
  - 移除所有 hex fallback（6 处）和 rgb fallback（1 处）
  - 响应式断点从 1100px/760px 对齐为 1366px/900px

- 修改：`frontend/src/features/knowledge/KnowledgeImportDialog.vue`
  - 去掉 2 处 hex fallback（`#f0fdf4`、`#22c55e`）
  - 去掉 3 处 `--zs-color-border-soft` 的 double-token fallback
  - border-radius 改用 `var(--zs-radius-sm)`

- 修改：`frontend/src/features/knowledge/KnowledgeAskPanel.vue`
  - AI 警告文案去掉 `⚠` emoji，改为纯文本
  - `.ai-warning` 使用 `--zs-space-*`、`--zs-radius-sm` token

- 修改：`frontend/src/features/knowledge/KnowledgeSummaryPanel.vue`
  - AI 警告文案去掉 `⚠` emoji，改为纯文本
  - `.ai-warning` 使用 `--zs-space-*`、`--zs-radius-sm` token

## Implementation Notes

### 新建资料入口

1. **列表面板操作条**：在 `.list-panel` 顶部新增 `.list-header`，左侧"资料"标题，右侧"新建"按钮。
2. **空状态引导**：原纯文字替换为 `.empty-state` 卡片，含说明文字和"新建第一条资料"主按钮，使用 dashed border 视觉风格。
3. **空详情引导**：`.empty-detail` 从纯文字改为居中卡片，含"或新建资料"次按钮。
4. **非浏览视图返回**：`viewMode !== 'browse'` 时在子面板上方显示"← 返回资料列表"次按钮。

### 布局收紧

- `.knowledge-page`：padding 从硬编码 `20px` 改为 `var(--zs-space-6)`（24px），背景从 `--zs-canvas-bg` 改为 `--zs-color-bg`
- `.knowledge-layout`：grid 从 `260px 1fr 300px` 改为 `minmax(260px,320px) minmax(0,1fr) minmax(260px,320px)`，gap 使用 `--zs-space-4`
- 三个面板统一为 `.list-panel, .detail-panel, .right-panel` 共享样式块，使用 token-based padding/border/radius/shadow
- 移除所有 `max-height: calc(100vh - 260px)`（其他 material page 不设 max-height，用 `align-items: start` 自然撑开）
- 添加 `max-width: 1480px` 居中约束（与其他 material page 一致）
- h1 从 1.25rem 改为 1.6rem（对齐 material page）

### 主题 token 修正

| 修正项 | 修正前 | 修正后 |
|---|---|---|
| 页面背景 | `var(--zs-canvas-bg, var(--zs-color-bg))` | `var(--zs-color-bg)` |
| success-banner | 3 处 hex fallback | 纯 `--zs-color-success*` |
| archived badge | `var(--zs-color-text-faint-bg, #f1f5f9)` | `var(--zs-color-surface-muted)` |
| credibility high | 2 处 hex fallback | 纯 `--zs-color-success*` |
| filter shadow | `var(--zs-shadow-card, 0 4px 16px rgb(...))` | `var(--zs-shadow-md)` |
| border-soft | 3 处 double-token fallback | `var(--zs-color-border-soft)` |

硬编码颜色检查结果：**0 匹配**（全部清除）。

## Deviations from Codex Plan

无偏差。

## Verification Commands Run

- `npm run type-check` → ✅
- `npm run test:unit -- --run` → ✅ 51 passed
- `npm run build` → ✅ (186.85KB CSS + 419.78KB JS)
- `rg -e "--zs-canvas" -e "#[0-9a-fA-F]" -e "rgb(" -e "rgba(" src/pages/knowledge src/features/knowledge` → ✅ 0 matches

## Verification Results

全部通过。知识库相关文件已无 `--zs-canvas-*` 误用、无 hex fallback、无 rgb/rgba 硬编码颜色。

## Known Issues

1. `KnowledgeSearchPanel.vue` 未修改（已完全合规，无 hex fallback、无 canvas token）。
2. 子面板（Search/Ask/Summary）内部仍有较多硬编码 px 值（gap、padding），但与全局 token 系统的 `--zs-space-*` 值接近，视觉差异很小，后续可统一。

## Suggested Next Review Points for Codex

1. 子面板内部间距是否也需要统一为 `--zs-space-*` token。
2. 知识库页面的 `max-width: 1480px` 是否与其他页面一致（characters 页为 1280px，settings 为 1480px）。
3. 是否需要为知识库页面增加写作页快捷入口（目前只在 ProjectDetailPage 的"更多"菜单中）。
