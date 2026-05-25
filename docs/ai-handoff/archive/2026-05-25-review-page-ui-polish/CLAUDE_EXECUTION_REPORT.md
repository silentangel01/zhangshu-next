---
archived_at: 2026-05-25
archive_reason: review page ui polish completed; deciding next work
date: 2026-05-25
task: 检查页面深层视觉优化
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

对检查页面（ReviewCheckPage.vue）做深层视觉优化，解决用户截图反馈的"信息密度过低、空状态过大、按钮层级过重"问题。

## Files Changed

- 修改：`frontend/src/pages/review/ReviewCheckPage.vue` — 深层视觉优化

## Implementation Notes

### 检查面板紧凑化
- 将面板标题区改为 `.panel-header-compact`（gap: 2px），合并 eyebrow/h2/hint 为一体
- 将 `检查功能只提示，不会自动修改正文` 缩短为 `只提示，不自动修改正文`，使用 `.panel-hint` 样式（更小的字号和更淡的颜色）
- 面板 gap 从 `--zs-space-4` 降为 `--zs-space-3`，padding 从 `--zs-space-5` 降为 `--zs-space-4 --zs-space-5`
- "开始检查"按钮改为右对齐中等宽度按钮（`min-width: 120px`，不再满宽）

### Segmented Control 轻量化
- gap 从 `--zs-space-2` 降为 `--zs-space-1`
- padding 从 `10px 8px` 降为 `6px 8px`
- 边框从 `--zs-color-border` 改为更淡的 `--zs-color-border-soft`
- 隐藏 radio input，使用 `:has(input:checked)` 为选中项添加 primary 色边框和背景

### 词库表单紧凑化
- 从纵向全铺改为 2 行 flex 布局：
  - 第一行：匹配词（flex-grow）+ 严重程度（固定 100px）
  - 第二行：建议（flex-grow: 2）+ 添加词条按钮（flex-shrink: 0）
- 按钮不再满宽，视觉层级更轻

### 导入/导出收纳到二级菜单
- 移除顶部 `导入词库` / `导出词库` 两个一级按钮
- 改为单个 `更多 ▾` 按钮，点击展开下拉菜单
- 使用 `showMoreMenu` ref 控制显隐，菜单项点击后自动关闭
- 菜单使用 absolute 定位、border、shadow，样式轻量

### 空状态缩减
- `.empty-state` min-height 从 120px 降为 64px
- 字号从默认降为 0.88rem，font-weight 从 800 降为 700

### 全局间距压缩
- 页面顶部 padding 从 `--zs-space-8` 降为 `--zs-space-6`
- 页面 header margin-bottom 从 `--zs-space-6` 降为 `--zs-space-4`
- 结果面板 gap 从 `--zs-space-3` 降为 `--zs-space-2`
- input/select padding 从 `12px` 改为 `8px 12px`
- button min-height 从 38px 降为 34px

### 移动端适配
- `.term-form-row` 在 ≤820px 回退为纵向排列
- `.check-button` 和 `.term-submit-button` 在移动端回退为满宽

## Deviations from Codex Plan

无偏差。所有计划中的检查页面优化项均已实施。

未执行 WritingAidPanel 的可选收纳（计划标注"不建议主动重构"）。

## Verification Commands Run

- `npm run type-check` → ✅
- `npm run build` → ✅
- `npm run test:unit -- --run` → ✅ (8 files, 115 tests)

## Verification Results

全部通过，无类型错误、无构建错误、无测试回归。

## Known Issues

- `:has()` CSS 选择器需要现代浏览器支持（Chrome 105+, Firefox 121+, Safari 15.4+）。如需兼容旧浏览器，可改用 JS class 切换。
- 无法在本次执行中进行视觉验证。建议手动检查以下断点：
  - 1440px / 1366px：确认检查面板紧凑度、segemented control 样式、按钮层级
  - 1024px：确认两列布局不溢出
  - 390px：确认所有布局回退为单列，按钮满宽

## Suggested Next Review Points for Codex

1. "更多"下拉菜单使用 `@click.stop` 阻止冒泡来防止点击菜单外部时关闭，但目前没有点击外部自动关闭逻辑，用户需要再次点击"更多"按钮关闭。可考虑后续添加 document click listener。
2. `.panel-hint` 字号 0.78rem + faint 色可能在某些显示器上可读性不足，建议实际查看。
3. `:has()` 选择器的浏览器兼容性需确认是否满足项目目标用户群。
