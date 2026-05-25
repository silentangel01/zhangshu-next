---
date: 2026-05-23
task: 设定模块交互优化：搜索上移、筛选折叠、拖拽移动
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

在上一轮设定树基础上完成三项交互优化：搜索框从左侧移到页面顶部工具条，筛选 select 收进"筛选"按钮弹出面板，支持拖拽设定页到目录并做三态类型变更确认。

## Files Changed

- 修改：`frontend/src/pages/settings/ProjectSettingsPage.vue` — 主改文件，新增工具条、筛选面板、拖拽逻辑、三态确认面板、CSS
- 修改：`frontend/src/__tests__/settings-tree.spec.ts` — 新增 4 个拖拽类型判断测试用例

## Implementation Notes

1. **搜索与筛选布局**：
   - 新增 `.settings-toolbar` 位于 page-header 下方、error/success 提示上方
   - 搜索框绑定 `filters.keyword`，支持回车和按钮触发
   - "筛选"按钮显示激活数量（如"筛选（2）"），点击展开/收起面板
   - 面板含三个 select + "应用筛选" / "清空筛选"按钮
   - 清空只清除结构化筛选（item_type/canon_status/importance），保留搜索词
   - 左侧 list-panel 只保留 boundary-card 和树

2. **拖拽移动**：
   - 只允许 `node_kind === 'page'` 的设定页被拖拽
   - 只允许 `node_kind === 'folder'` 的目录作为 drop target
   - 拖到同一目录不发起 API 请求
   - 使用原生 HTML Drag and Drop API，无新依赖

3. **三态确认面板**：
   - 当目标目录默认类型与设定页当前类型不同时，弹出 `pendingMove` 确认面板
   - 三个按钮："自动更改类型"（不传 item_type，后端继承）、"仅移动"（显式传原 item_type）、"取消"
   - 使用组件内 overlay + panel 实现，不用 window.confirm，避免"取消"语义歧义
   - 目标目录无默认类型或类型相同时直接移动

4. **移动后行为**：
   - 成功后调用 `refreshSettings()` 刷新数据（不改本地数组）
   - 保留当前搜索/筛选条件
   - 更新选中状态到移动后的设定
   - 失败时显示错误提示

## Deviations from Codex Plan

无。严格按照 CODEX_PLAN.md 执行。

## Verification Commands Run

- `python -m compileall app` → ✅ pass
- `npm run type-check` → ✅ pass
- `npm run test:unit` → ✅ 8/8 pass (4 new drag tests + 4 existing)
- `npm run build` → ✅ 184 modules, 构建成功

## Verification Results

| 命令 | 结果 |
|---|---|
| `python -m compileall app` | ✅ pass |
| `npm run type-check` | ✅ pass |
| `npm run test:unit` | ✅ 8/8 pass |
| `npm run build` | ✅ pass |

## Known Issues

1. 后端 pytest 仍未运行（venv 在当前 bash 环境不可用），但本任务不涉及后端修改，上一轮代码已通过 compileall 验证
2. 原生 HTML Drag and Drop 在移动端支持较弱，本任务验收重点为桌面端
3. 筛选面板关闭逻辑仅通过"应用筛选"和"清空筛选"按钮触发，未实现点击外部关闭（Codex 计划明确标注为可选）

## Suggested Next Review Points for Codex

1. 手动浏览器验证：搜索框位置、筛选面板交互、拖拽移动的三种路径
2. 移动端是否需要额外适配拖拽交互
3. 是否需要在后续任务中支持目录拖拽移动
4. 筛选面板是否需要点击外部关闭
