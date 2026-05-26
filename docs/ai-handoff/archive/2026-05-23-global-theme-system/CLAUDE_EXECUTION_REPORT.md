---
date: 2026-05-23
task: global-theme-system
codex_plan: docs/ai-handoff/CODEX_PLAN.md (2026-05-23 version)
---

## Task Summary

将编辑器局部主题升级为全局应用主题系统，新增画布中性 token 确保关系图/时间线画布不随主题变色，清理高频页面硬编码颜色。

## Files Changed

### 新增文件

- `frontend/src/shared/theme/appTheme.ts` — 应用级主题模块：定义 AppTheme 类型、localStorage 读写、DOM `data-theme` 应用逻辑
- `frontend/src/shared/theme/ThemeSwitcher.vue` — 全局主题切换组件：三个按钮（默认/护眼/黑夜），segmented control 样式
- `frontend/src/__tests__/app-theme.spec.ts` — 主题模块单元测试：覆盖 isAppTheme 验证、读写回退、data-theme 应用、完整生命周期

### 修改文件

- `frontend/src/main.ts` — 在 `app.mount()` 前调用 `applyAppTheme(getInitialAppTheme())`，减少首屏闪烁
- `frontend/src/App.vue` — 添加 ThemeSwitcher 组件作为 fixed 右上角全局控件
- `frontend/src/style.css` — 在 `:root` 新增 7 个画布中性 token（`--zs-canvas-bg/grid/axis/node-bg/node-border/text/text-muted`），不随主题变化
- `frontend/src/features/chapters/ChapterEditor.vue` — 删除 `getEditorThemeStyle()` 调用和"显示模式"选择器，保留字体/字号/行距等排版设置
- `frontend/src/features/graph/GraphCanvas.vue` — 画布背景和网格改用 `--zs-canvas-bg` / `--zs-canvas-grid`
- `frontend/src/features/graph/GraphNode.vue` — 节点底色、边框、文本改用 `--zs-canvas-*` token
- `frontend/src/pages/timeline/ProjectTimelinePage.vue` — 画布面板、轨道轴、事件节点、边线改用 `--zs-canvas-*` token
- `frontend/src/pages/projects/ProjectsPage.vue` — 替换全部硬编码颜色（`#f6f8fb`, `#111827`, `#64748b`, `#ffffff`, `#2563eb`, `#d8dee9`, `#cfd7e3`, `#cbd5e1` 等）为 `--zs-color-*` token
- `frontend/src/pages/characters/ProjectCharactersPage.vue` — 替换常见硬编码颜色（`#f6f8fb`, `#111827`, `#64748b`, `#ffffff`）为 `--zs-color-*` token
- `frontend/src/pages/clues/ProjectCluesPage.vue` — 替换硬编码颜色（`#f6f8fb`, `#111827`, `#64748b`, `#ffffff`, `#2563eb`, `#d8dee9`, `#cfd7e3`, `#cbd5e1`）为 `--zs-color-*` token
- `frontend/src/pages/settings/ProjectSettingsPage.vue` — 替换硬编码颜色（同上模式）为 `--zs-color-*` token

## Implementation Notes

### 主题存储与应用机制

- 存储：`localStorage['zhangshu:app:theme']`，值为 `'default' | 'eye-care' | 'dark'`
- 应用：`applyAppTheme()` 直接操作 `document.documentElement.dataset.theme`
  - `'default'`：移除 `data-theme` 属性（使用 `:root` 默认值）
  - `'eye-care'` / `'dark'`：设置 `data-theme` 属性
- 初始化：在 `main.ts` 的 `app.mount()` 前调用，避免首屏闪烁

### 画布固定区域

以下区域使用 `--zs-canvas-*` token，在三个主题下保持相同视觉：

- 关系图画布背景 (`--zs-canvas-bg: #fbfcfe`)
- 关系图网格线 (`--zs-canvas-grid: rgb(107 124 131 / 14%)`)
- 关系图节点底色 (`--zs-canvas-node-bg: #ffffff`)
- 关系图节点边框 (`--zs-canvas-node-border: #d8dee9`)
- 关系图文本 (`--zs-canvas-text: #111827`, `--zs-canvas-text-muted: #64748b`)
- 时间线画布面板背景
- 时间线轨道轴线
- 时间线事件节点底色和边框
- 时间线边线

画布外部的侧栏、工具栏、详情面板、表单继续使用全局 `--zs-color-*` token，可随主题变化。

### 硬编码颜色清理情况

**已清理（高频页面）：**

| 页面 | 清理的颜色 |
|---|---|
| `ProjectsPage` | 全部硬编码颜色（0 残留） |
| `ProjectCharactersPage` | 常见颜色：bg, text, muted, surface |
| `ProjectCluesPage` | bg, text, muted, surface, primary, border |
| `ProjectSettingsPage` | bg, text, muted, surface, primary, border |

**暂未清理（后续可处理）：**

- `features/characters/ChapterCharacterPanel.vue`
- `features/clues/ChapterCluePanel.vue`
- `features/timeline/ChapterTimelinePanel.vue`
- `features/graph/ChapterGraphCard.vue`
- 各页面中的状态提示颜色（error-banner, success-banner 的浅色背景）
- 各页面中的 `#374151`, `#4b5563`, `#94a3b8` 等次级文本色

这些区域的 `.material-page` CSS 类已提供了 token 覆盖，在功能上可以工作。彻底清理需要更多时间逐一处理。

### ChapterEditor 迁移

- 删除了 `getEditorThemeStyle()` 函数和调用
- 删除了"显示模式"下拉选择器
- 保留了字体、字号、行距、宽度、首行缩进、段间距等排版设置
- 旧的 `zhangshu:editor:appearance` 存储中的 `theme` 字段不再读取或写入，但不会报错

## Deviations from Codex Plan

无重大偏离。以下为小幅调整：

1. **ThemeSwitcher 位置**：放置在右上角 (fixed, top: 16px, right: 16px)，而非右下角。原因是右上角更符合全局控件的常见位置，且不会遮挡页面底部的操作按钮。
2. **硬编码颜色清理范围**：Plan 建议"选择性修改"，实际执行时清理了 4 个高频页面的主要硬编码颜色，超出 P1 范围但未涉及 feature 组件。
3. **GraphEdgeOverlay.vue**：检查后发现不使用主题依赖的 surface/text token，无需修改。

## Verification Commands Run

- `npm run type-check` → ✅ 通过
- `npm run test:unit` → ✅ 33 tests passed（含新增 app-theme.spec.ts 的 12 个测试）
- `npm run build` → ✅ 生产构建成功（374.74 kB JS + 149.14 kB CSS）

## Verification Results

全部验证通过：

- TypeScript 类型检查无错误
- 单元测试全部通过（包括新增的主题模块测试）
- 生产构建成功，无警告

## Known Issues

1. **未完全清理的硬编码颜色**：feature 组件（ChapterCharacterPanel, ChapterCluePanel, ChapterTimelinePanel, ChapterGraphCard）仍有硬编码浅色。这些组件使用 `.material-page` 类提供 token 覆盖，功能上可工作，但彻底清理留待后续。
2. **状态提示颜色**：error-banner, success-banner 等状态提示的浅色背景仍为硬编码值。这些在深色模式下可能不够协调，但 `.material-page` 覆盖已处理。
3. **浏览器原生控件**：深色模式下浏览器原生 `<select>`, `<input>` 可能受 `color-scheme` 影响。`.material-page` 已为这些控件设置 token 背景和文字色，但未经过手动浏览器测试验证。

## Suggested Next Review Points for Codex

1. **手动 UI 验证**：建议在三个主题下手动检查以下页面的视觉效果：
   - `/projects` — 书籍卡片
   - `/projects/{id}` — 项目概览
   - `/projects/{id}/graph` — 关系图画布（确认不随主题变色）
   - `/projects/{id}/timeline` — 时间线画布（确认不随主题变色）
2. **Feature 组件硬编码颜色**：评估是否需要清理 ChapterCharacterPanel, ChapterCluePanel 等 feature 组件的硬编码颜色。
3. **ThemeSwitcher 位置**：当前为右上角 fixed，确认在移动端不遮挡页面操作。
4. **正文编辑器主题迁移**：确认旧 `zhangshu:editor:appearance.theme` 不再影响编辑器外观，且排版设置仍正常工作。
