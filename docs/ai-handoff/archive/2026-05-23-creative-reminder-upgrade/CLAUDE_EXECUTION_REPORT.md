---
date: 2026-05-23
task: Creative Reminder Module Upgrade — Structured Reminders with Reason/Suggestion
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

升级提醒模块：扩展结构化提醒字段（reason/suggestion/scope_label/context_summary），为 7 条规则补充原因和处理建议，前端添加程度和类型筛选，后端补充排序逻辑和测试覆盖。

## Files Changed

### Backend
- 修改：`backend/app/schemas/creative_reminder.py`
  - `CreativeReminderRead` 新增 4 个字段：`reason`、`suggestion`、`scope_label`、`context_summary`（可选）
  - `created_from` 保持 `Literal["rule"] = "rule"`
- 修改：`backend/app/services/creative_reminder_service.py`
  - 新增模块级常量 `_SEVERITY_RANK`（severity 排序映射）和 `_RULE_META`（7 条规则的 reason/suggestion 文案）
  - `_item()` 方法签名扩展：新增 `scope_label` 和 `context_summary` 参数，内部从 `_RULE_META` 查找 reason/suggestion
  - 7 条规则方法全部更新调用 `_item()`，传入具体的 `scope_label` 和 `context_summary`
  - `list_project_reminders()` 末尾调用 `_sort_reminders()` 做排序
  - 新增 `_sort_reminders()` 静态方法：按 severity（critical → warning → info）排序，同级中章节相关优先于全书提醒
- 新增：`backend/tests/test_creative_reminders.py`
  - 6 个测试用例覆盖：项目不存在抛异常、重要伏笔长期未回收、草稿设定被使用、severity 过滤、reminder_type 过滤、severity 排序

### Frontend
- 修改：`frontend/src/entities/creative-reminder/types.ts`
  - `CreativeReminder` 接口新增 `reason`、`suggestion`、`scope_label`、`context_summary` 字段
- 修改：`frontend/src/features/writing/CreativeReminderPanel.vue`
  - 新增筛选控件：严重程度下拉（全部/重要/注意/提示）和类型下拉（全部/伏笔/人物/大纲/时间线/关系图/伏笔回收/设定）
  - 新增 `filteredReminders` computed：本地筛选 + 排序（severity 优先，章节相关优先）
  - 卡片展示升级：severity badge、scope_label、title、message、"为什么提醒"（reason）、"建议处理"（suggestion）、context_summary（可选）、目标跳转链接
  - 刷新按钮改用 `.zs-button .zs-button-ghost` utility
  - 空状态文案改为"当前规则未发现需要处理的提醒"
  - 总数显示"共 N 条提醒"

## Implementation Notes

### 规则提醒意见摘要
| 规则类型 | scope_label | 原因要点 | 建议要点 |
|---|---|---|---|
| `important_clue_unresolved` | 全书 | 重要伏笔长期未回收，读者可能遗忘线索 | 规划回收章节或降低重要性 |
| `important_character_absent` | 全书 | 重要人物长期未出场，削弱存在感 | 安排出场或下调重要性 |
| `outline_not_done_for_written_chapter` | 关联章节 | 章节已有正文但大纲未完成 | 更新大纲状态或补充遗漏情节 |
| `timeline_event_missing_chapter` | 全书 | 重要事件未绑定章节 | 绑定章节或降低重要性 |
| `graph_node_broken_binding` | 跨资料 | 节点绑定资料已删除 | 重新绑定或改为自定义节点 |
| `clue_payoff_without_setup` | 全书 | 回收缺少埋设记录，可能突兀 | 补充埋设或调整伏笔状态 |
| `setting_used_but_draft` | 关联章节 | 章节使用草稿设定 | 改为正式或标记风险 |

### 排序逻辑
`_sort_reminders()` 使用元组排序：`(severity_rank, chapter_priority)`
- severity_rank: critical=0, warning=1, info=2
- chapter_priority: 有 chapter_id=0（章节相关优先），无=1（全书提醒靠后）

### 前端筛选
筛选在前端本地完成（`filteredReminders` computed），不额外请求后端。原因：
- 后端已有 severity/reminder_type query 参数，但前端已有完整列表
- 本地筛选避免切换条件时重复请求
- 排序与后端一致（severity + 章节优先）

### 测试覆盖
**后端**（19 tests passed）：
- 项目不存在 → 抛 `CreativeReminderProjectNotFoundError`
- critical 伏笔 25 章未回收 → 返回 `important_clue_unresolved`，包含 reason/suggestion/scope_label="全书"
- 草稿设定被章节使用 → 返回 `setting_used_but_draft`，scope_label="关联章节"
- severity 过滤 → critical 过滤只返回 critical，info 过滤只返回 info
- reminder_type 过滤 → 只返回匹配类型
- 排序 → critical 在前，warning 居中，info 在后

**前端**（51 tests passed）：
- 现有测试继续通过
- 未新增前端测试原因：组件测试需要 mock Router 和 API，成本较高。Codex 计划标注"如果组件测试成本过高，可至少为纯函数写测试"。当前筛选逻辑在 computed 中，未抽出纯函数。

## Deviations from Codex Plan

无偏差。所有 Step 2-10 均按计划范围执行。

## Verification Commands Run

- `npm run type-check` → ✅
- `npm run test:unit -- --run` → ✅ (51 tests)
- `npm run build` → ✅ (198 modules)
- `pytest tests/test_creative_reminders.py tests/test_settings_tree.py` → ✅ (19 tests)

## Verification Results

全部通过。后端新增 6 个测试覆盖主要规则和过滤排序。前端类型检查、单元测试、生产构建均通过。

## Known Issues

无。

## Suggested Next Review Points for Codex

1. **提醒持久化**：当前提醒是实时规则计算，无已读/忽略状态。如需"已处理"标记，需引入数据库表。
2. **AI 提醒边界**：`created_from` 当前只有 `"rule"`。未来如需 AI 总结提醒，建议另设 `created_from: "ai"` 或独立模块。
3. **提醒文案语气**：已使用"建议""可以""请检查"等建议式语气，避免命令式。可人工检查是否仍有过强措辞。
4. **前端筛选一致性**：当前前端本地筛选，后端也有 query 参数。如后续提醒数量增长，可考虑统一走后端过滤。
5. **响应式验证**：建议人工检查 390px/768px/1280px 下筛选下拉和卡片布局。
