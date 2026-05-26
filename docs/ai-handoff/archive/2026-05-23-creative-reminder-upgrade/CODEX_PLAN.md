# Task Summary

规划升级当前“提醒”模块。当前提醒模块是基于规则的创作提醒，不是 AI 生成提醒。本轮目标是在保持规则引擎边界的前提下，让提醒从“发现问题”升级为“问题 + 原因 + 建议处理意见 + 目标跳转 + 可筛选排序”的可执行辅助面板。

Codex 本轮只写计划，不修改业务代码。本计划交由 Claude Code 执行。

# Current Codebase Findings

1. 已阅读 Claude Code 最新执行报告。上一轮任务为 `Design System Round 2 - Convergence`，已完成全局 token、utility、项目/卷/大纲弹窗、项目页、资料管理页和写作上下文组件的 UI 收敛。
2. 旧交接文件已归档到：
   - `docs/ai-handoff/archive/2026-05-23-design-system-round-2/CODEX_PLAN.md`
   - `docs/ai-handoff/archive/2026-05-23-design-system-round-2/CLAUDE_EXECUTION_REPORT.md`
3. 当前提醒模块后端入口：
   - `backend/app/api/creative_reminders.py`
   - `GET /api/projects/{project_id}/creative-reminders`
   - 支持 query：`scope`、`chapter_id`、`severity`、`reminder_type`
4. 当前提醒模块后端 schema：
   - `backend/app/schemas/creative_reminder.py`
   - `CreativeReminderRead` 当前字段包括：`id`、`project_id`、`chapter_id`、`type`、`severity`、`title`、`message`、`target_type`、`target_id`、`action_label`、`created_from`
5. 当前提醒模块后端 service：
   - `backend/app/services/creative_reminder_service.py`
   - 所有提醒由 `CreativeReminderService.list_project_reminders()` 调用内部规则方法生成。
   - 当前已有规则：
     - `important_clue_unresolved`
     - `important_character_absent`
     - `outline_not_done_for_written_chapter`
     - `timeline_event_missing_chapter`
     - `graph_node_broken_binding`
     - `clue_payoff_without_setup`
     - `setting_used_but_draft`
6. 当前提醒模块前端入口：
   - `frontend/src/features/writing/WritingAidPanel.vue` 中的 `reminders` tab
   - `frontend/src/features/writing/CreativeReminderPanel.vue`
7. 当前提醒模块前端 entity：
   - `frontend/src/entities/creative-reminder/types.ts`
   - `frontend/src/entities/creative-reminder/api.ts`
8. 当前前端提醒展示较轻：
   - 仅显示严重程度、标题、message、目标跳转。
   - 没有前端筛选控件。
   - 没有“建议处理意见”字段。
   - 没有规则说明、影响范围、是否可暂时忽略等辅助信息。
9. 当前提醒模块没有独立测试。后端已有 `backend/tests/test_settings_tree.py` 可作为 in-memory SQLite service 测试写法参考；前端已有 Vitest 测试目录 `frontend/src/__tests__/`。

# Architecture Decision

1. 本轮提醒模块继续保持“规则提醒”定位，不接入真实 AI，不接入 RAG，不调用外部模型。
2. 提醒结果应从单一 message 扩展为结构化提醒：
   - 发生了什么：`title`、`message`
   - 为什么提醒：`reason`
   - 建议怎么处理：`suggestion`
   - 影响范围：`scope_label` 或 `context_summary`
   - 可执行动作：`action_label`、`target_type`、`target_id`
3. 后端仍由 Service 层聚合规则，不新增数据库表。提醒结果可以保持“实时计算”，避免现在就引入提醒持久化、已读状态、忽略状态等复杂功能。
4. 前端只展示、筛选和跳转，不在前端复刻提醒规则。
5. 若后续要接入 AI 总结/梳理，建议将 AI 生成的提醒另设 `created_from: "ai"` 或独立模块。本轮只允许 `created_from: "rule"`，最多在类型定义中预留扩展，不实际启用 AI。
6. 后端规则方法可以继续保留在 `CreativeReminderService` 内，但建议抽出规则元信息映射，避免每条规则的标题、建议文案散落在多个分支中。

# Files to Create or Modify

建议 Claude Code 修改或新增以下文件：

1. 后端 schema：
   - 修改 `backend/app/schemas/creative_reminder.py`
2. 后端 service：
   - 修改 `backend/app/services/creative_reminder_service.py`
3. 后端 API：
   - 视需要小改 `backend/app/api/creative_reminders.py`
4. 后端测试：
   - 新增 `backend/tests/test_creative_reminders.py`
5. 前端 entity：
   - 修改 `frontend/src/entities/creative-reminder/types.ts`
   - 修改 `frontend/src/entities/creative-reminder/api.ts`，仅在新增 query 参数时需要
6. 前端 UI：
   - 修改 `frontend/src/features/writing/CreativeReminderPanel.vue`
   - 视需要小改 `frontend/src/features/writing/WritingAidPanel.vue`
7. 前端测试：
   - 可选新增 `frontend/src/__tests__/creative-reminder.spec.ts`
8. 交接文件：
   - 新增 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`

# Implementation Steps for Claude Code

1. 执行前检查
   - 阅读本计划。
   - 执行 `git status --short`，记录当前工作区状态。
   - 不要读取或修改 `docs/ai-handoff/archive/` 下的历史计划。
   - 不要修改数据库文件、启动脚本、依赖文件。

2. 扩展提醒 schema
   - 在 `backend/app/schemas/creative_reminder.py` 的 `CreativeReminderRead` 中新增字段：
     - `reason: str`
     - `suggestion: str`
     - `scope_label: str`
     - `context_summary: str | None = None`
   - `created_from` 继续保持 `Literal["rule"] = "rule"`。
   - 不要新增数据库 model，因为提醒仍是实时规则计算结果。

3. 为规则提醒补充“提醒意见”
   - 修改 `backend/app/services/creative_reminder_service.py`。
   - 调整 `_item()` 方法签名，接收：
     - `reason`
     - `suggestion`
     - `scope_label`
     - `context_summary`
   - 为所有现有规则补充具体提醒意见。
   - 建议文案如下，可按实际中文语气微调：
     - `important_clue_unresolved`
       - reason：重要伏笔从埋设后经过较多章节仍未回收，读者可能遗忘或认为线索断裂。
       - suggestion：检查该伏笔是否仍需要保留；如需要，请规划回收章节或在近期章节补一次提示；如不需要，请将伏笔状态调整为废弃或降低重要性。
     - `important_character_absent`
       - reason：重要人物长时间未出场或未被章节绑定，可能削弱人物存在感。
       - suggestion：考虑安排该人物出场、被其他角色提及，或在人物资料中下调重要性。
     - `outline_not_done_for_written_chapter`
       - reason：章节已有正文，但关联大纲仍处于未完成状态，可能导致进度记录不准确。
       - suggestion：确认正文是否已覆盖该大纲目标；如果已完成，请更新大纲状态；如果未完成，请补充遗漏情节。
     - `timeline_event_missing_chapter`
       - reason：重要时间线事件没有绑定章节，后续查找和一致性检查会变弱。
       - suggestion：为该事件绑定发生章节；如果它只是背景事件，请在备注中说明并降低重要性。
     - `graph_node_broken_binding`
       - reason：关系图节点绑定的资料不存在或已删除，图谱可能显示失效信息。
       - suggestion：重新绑定到有效资料，或将节点改为自定义节点并更新说明。
     - `clue_payoff_without_setup`
       - reason：伏笔有回收记录但缺少埋设记录，读者可能感到回收突兀。
       - suggestion：补充埋设章节或设置埋设关系；如果回收本身不需要前置伏笔，请调整伏笔状态和说明。
     - `setting_used_but_draft`
       - reason：章节已使用草稿设定，可能导致正文引用未定稿内容。
       - suggestion：确认该设定是否已经稳定；如果稳定，请将设定状态改为正式；如果仍在试验，请在章节备注中标记风险。
   - `scope_label` 建议：
     - 全书规则：`全书`
     - 章节相关：`本章` 或 `关联章节`
     - 图谱、时间线等跨模块：`跨资料`
   - `context_summary` 可填入短上下文，例如章节名、伏笔名、人物名、距离章节数。没有合适上下文时为 `None`。

4. 优化提醒排序和过滤
   - 保持后端现有 `severity`、`reminder_type` 过滤。
   - 确认 `scope=chapter` 时不会把与当前章节无关的全书提醒塞得过多。
   - 建议后端排序顺序：
     - severity：`critical` > `warning` > `info`
     - 同级中章节相关优先于全书提醒。
     - 同级中保持现有规则生成顺序。
   - 如果排序逻辑开始变复杂，新增私有方法 `_sort_reminders()`，不要在 API 层排序。

5. 前端类型同步
   - 在 `frontend/src/entities/creative-reminder/types.ts` 中同步新增：
     - `reason`
     - `suggestion`
     - `scope_label`
     - `context_summary`
   - 如果后端没有新增 query 参数，则 `api.ts` 不需要改。

6. 升级前端提醒面板
   - 修改 `frontend/src/features/writing/CreativeReminderPanel.vue`。
   - 面板结构建议：
     - 顶部：标题、刷新按钮、提醒总数。
     - 工具区：严重程度筛选、类型筛选、范围说明。
     - 列表卡片：
       - 严重程度 badge。
       - `scope_label`。
       - 标题。
       - message。
       - “为什么提醒”：展示 `reason`。
       - “建议处理”：展示 `suggestion`。
       - `context_summary` 有值时展示为次要信息。
       - 底部保留目标跳转。
   - 筛选控件：
     - 严重程度：全部、重要、注意、提示。
     - 类型：全部、伏笔、人物、大纲、时间线、关系图、设定。
   - 筛选可以先在前端本地完成，也可以调用现有后端 query。建议使用现有后端 query，避免前端和后端过滤逻辑不一致。
   - 刷新按钮使用 `.zs-button` 或当前项目已采用的共享 utility。
   - 状态展示使用 `.zs-state` 或 `.zs-alert-*`。

7. 前端交互细节
   - 切换筛选条件时重新请求提醒列表。
   - 切换章节时保留当前筛选条件，但刷新提醒内容。
   - 如果无提醒，空状态文案应说明“当前规则未发现需要处理的提醒”，避免暗示系统已经做了 AI 全面审稿。
   - 卡片中的建议文案不应使用命令式“必须”，建议使用“建议”“可以”“请检查”。
   - 不要在提醒卡片中加入自动修改正文按钮。

8. 后端测试
   - 新增 `backend/tests/test_creative_reminders.py`。
   - 参考 `backend/tests/test_settings_tree.py` 使用 in-memory SQLite。
   - 至少覆盖：
     - 项目不存在时 service 抛出 `CreativeReminderProjectNotFoundError`。
     - 重要伏笔长期未回收时返回 `important_clue_unresolved`，且包含 `reason`、`suggestion`、`scope_label`。
     - 草稿设定被章节使用时返回 `setting_used_but_draft`。
     - `severity` 过滤有效。
     - `reminder_type` 过滤有效。
     - 返回列表按 severity 排序。

9. 前端测试
   - 如果项目当前测试环境方便挂载组件，新增 `frontend/src/__tests__/creative-reminder.spec.ts`：
     - mock `listCreativeReminders`。
     - 验证 reason 和 suggestion 被展示。
     - 验证严重程度筛选会触发带 `severity` 的请求。
     - 验证空状态文案。
   - 如果组件测试成本过高，可至少为新增的类型映射或筛选参数构造函数写纯函数测试；若没有抽出纯函数，则在执行报告中说明未新增前端测试原因。

10. 执行后报告
   - 创建 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
   - 报告必须包括：
     - 实际修改文件。
     - 新增字段说明。
     - 每条规则新增的提醒意见摘要。
     - 验证命令和结果。
     - 未采纳建议及原因。
     - 是否存在兼容性风险。

# Constraints

1. 本轮提醒仍是规则提醒，不接入真实 AI、不接入 RAG、不调用外部模型。
2. 不新增数据库表，不做提醒持久化，不做已读、忽略、稍后提醒等状态功能。
3. 不要把提醒规则写进前端组件。
4. 不要把复杂业务逻辑写进 `backend/app/api/creative_reminders.py`。
5. Service 层可以协调多个 model 查询，但应避免难以维护的大段重复 SQL。
6. 不要修改与提醒模块无关的业务文件。
7. 不要破坏现有 Project、Chapter、Character、Setting、Clue、Timeline、Graph API。
8. 所有用户可见文案必须为简体中文。
9. 不要让提醒建议自动修改正文或资料。
10. 不要提交本地数据库、日志、密钥、本地配置或临时文件。

# Verification Commands

后端：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
pytest
```

如果全量后端测试耗时过长，至少执行：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
pytest backend\tests\test_creative_reminders.py
```

前端：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit -- --run
npm run build
```

手动检查：

```text
打开任意项目写作页
进入右侧“提醒”tab
检查全书提醒和本章提醒
切换严重程度筛选
切换类型筛选
点击提醒目标跳转
在默认、护眼、黑夜主题下检查提醒卡片可读性
```

# Acceptance Criteria

1. 提醒接口返回的每条提醒都包含 `reason`、`suggestion`、`scope_label` 字段。
2. 当前已有 7 类规则提醒都补充了明确的处理建议。
3. 前端提醒卡片展示“为什么提醒”和“建议处理”。
4. 前端支持按严重程度和提醒类型筛选。
5. 提醒仍明确标注为规则提醒，不暗示 AI 已自动审稿。
6. 切换章节后提醒内容能刷新，且不会丢失当前筛选条件。
7. 点击目标跳转仍可进入对应资料页或关系图页面。
8. 后端新增测试覆盖主要规则、过滤和排序。
9. 前端类型检查、单元测试、构建通过。
10. 未修改提醒模块无关的业务文件。

# Risks and Watchpoints

1. 现有 `CreativeReminderRead` schema 被前端直接消费，新增字段需要前后端同步，否则 type-check 或运行时展示会出错。
2. 提醒建议文案如果写得过强，可能让用户感觉系统在替作者决策。应保持建议式语气。
3. `scope=chapter` 当前过滤逻辑会保留部分全书提醒，需要确认不会让本章提醒列表过吵。
4. 如果新增类型过滤 UI，应复用后端已有 `reminder_type` 参数，不要前后端各做一套不一致映射。
5. 后端规则当前集中在一个 service 文件中，新增文案时要避免继续堆成难读的大函数。必要时可抽出常量映射或私有 helper。
6. 不要把未来 AI/RAG 边界提前混入当前规则提醒实现。
7. 如果测试需要创建较多模型数据，应保持 fixture 简洁，避免把测试写成难维护的大型场景。

# Review Checklist

Codex 复审时应检查：

1. 是否读取并遵守本计划。
2. 是否符合 AGENTS.md 中 Codex/Claude 分工。
3. 是否只升级规则提醒，没有接入 AI、RAG 或外部模型。
4. 是否新增 `reason`、`suggestion`、`scope_label` 并前后端同步。
5. 是否每条现有规则都有清晰提醒意见。
6. 是否保持 API 层轻量，业务判断仍在 Service 层。
7. 是否出现 UI、业务逻辑、数据访问、AI 调用混杂。
8. 是否新增了不必要的数据库表或依赖。
9. 前端提醒面板是否清晰展示问题、原因、建议和目标跳转。
10. 筛选和排序是否符合预期。
11. 是否补充后端测试，前端测试缺失时是否说明原因。
12. 验证命令是否通过。
13. 是否有不该提交的密钥、本地配置、临时文件、数据库或日志。
14. 最终建议应明确为 Accept、Minor Revision 或 Rework。
