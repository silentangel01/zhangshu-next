<!-- archived: 2026-05-24; reason: writing stats dashboard V1 completed -->

# Task Summary

规划“写作统计仪表盘”功能，由 Claude Code 执行实现。Codex 本轮未修改任何业务代码。

目标是在项目内新增一个面向网文作者的写作统计页，用于展示当前作品的总字数、目标进度、今日/本周/本月净增字数、连续写作、估算写作时长、日历热力图、小时分布、分卷/章节字数分布和章节增长排行。

本任务不是做工程监控后台，也不是暴露底层数据库统计。页面应服务于作者的日常写作反馈：我写了多少、离目标多远、最近是否稳定、哪些章节进展快、哪些部分偏短或偏长。

参考的同类写作软件/应用模式：

- Scrivener：强调项目目标、会话目标、截止日期、写作历史和进度条。
  - https://www.literatureandlatte.com/blog/track-statistics-and-targets-in-your-scrivener-projects
- Ulysses：提供文本统计、阅读时间、目标进度和 deadline 类目标。
  - https://help.ulysses.app/en_US/general/text-statistics
- Novlr：将 goals、streak、日历和 analytics 作为写作习惯反馈入口。
  - https://www.novlr.org/features/goals-analytics
- The Novel Factory：以小说整体统计、章节/场景长度和进度为核心。
  - https://www.novel-software.com/knowledge-base/statistics/

本轮建议先做“可用、可靠、轻量”的 V1，不接入 AI，不新增图表库，不做过度复杂的预测或 deadline 系统。

# Current Codebase Findings

1. 当前项目结构：
   - 前端：`frontend/`，Vue 3 + TypeScript + Vite。
   - 后端：`backend/`，FastAPI + SQLAlchemy + SQLite。
   - 交接文件目录：`docs/ai-handoff/`。

2. 当前没有活跃交接文件：
   - `docs/ai-handoff/CODEX_PLAN.md` 不存在。
   - `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md` 不存在。
   - `docs/ai-handoff/CODEX_REVIEW.md` 不存在。
   - 本轮不需要归档旧交接文件。

3. 当前统计相关基础已经存在：
   - `backend/app/models/chapter.py`
     - `Chapter.word_count`
     - `Chapter.content`
     - `Chapter.volume_id`
     - `Chapter.updated_at`
     - `Chapter.deleted_at`
   - `backend/app/models/project.py`
     - `Project.target_word_count`
     - `Project.status`
   - `backend/app/models/volume.py`
     - 分卷结构可用于分卷字数统计。
   - `backend/app/models/chapter_version.py`
     - 版本记录包含 `word_count` 和 `created_at`。

4. 当前章节更新路径：
   - API：`backend/app/api/chapters.py`
   - Service：`backend/app/services/chapter_service.py`
   - Repository：`backend/app/repositories/chapter_repo.py`
   - `ChapterService.update_chapter()` 会根据正文重新计算 `word_count`。
   - 现有字数计算为非空白字符计数：`sum(1 for character in content if not character.isspace())`。

5. 当前没有可靠的每日/每小时写作历史：
   - `chapters.word_count` 只能代表当前字数。
   - `chapter_versions` 可辅助还原部分历史，但自动保存版本有间隔阈值，不能作为完整写作事件源。
   - 如果不新增统计事件表，今日、本周、本月、连续写作、小时分布都只能猜测，不应这样实现。

6. 当前前端已有项目内工具页路由模式：
   - `frontend/src/router/index.ts`
   - 已有 `/projects/:projectId/search`
   - 已有 `/projects/:projectId/review`
   - 已有 `/projects/:projectId/knowledge`
   - 写作统计适合新增为 `/projects/:projectId/stats`。

7. 当前写作工作区顶部入口：
   - `frontend/src/pages/projects/ProjectDetailPage.vue`
   - 顶部已有 `搜索`、`检查` 和 `更多` 菜单。
   - 写作统计建议作为常用工具入口，放在 `搜索`、`检查` 旁边，文案为 `统计`。

8. 当前 UI 规范已经明确统计页方向：
   - `docs/UI_Regression_Checklist.md` 中已有“统计页”检查项：
     - 今日字数、本周字数、本月字数、今日写作时长、连续写作、平均速度。
     - 热力图颜色低噪。
     - 小时图和章节排行不无限拉伸。
     - 不过度强调增删字调试字段。
   - `docs/UI_UX_Design_Guidelines.md` 中明确：
     - 统计主显示应使用净增字数。
     - 新增字数和删除字数只作为高级详情或调试数据。
     - 写作统计采用 GitHub 风格热力图，但不使用 GitHub 品牌色。
     - 全局样式已存在 `--zs-heatmap-0` 到 `--zs-heatmap-4` 和 `--zs-module-stats`。

# Architecture Decision

采用“写作统计事件表 + 后端聚合服务 + 前端轻量图表组件”的方案。

## 后端边界

1. 新增独立统计边界：
   - Model：`backend/app/models/writing_stat_event.py`
   - Repository：`backend/app/repositories/writing_stats_repo.py`
   - Schema：`backend/app/schemas/writing_stats.py`
   - Service：`backend/app/services/writing_stats_service.py`
   - API：`backend/app/api/writing_stats.py`

2. 不把统计聚合写入：
   - `backend/app/main.py`
   - `backend/app/api/chapters.py`
   - `backend/app/repositories/chapter_repo.py`

3. `ChapterService.update_chapter()` 只负责在正文变更并导致字数变化时，调用 `WritingStatsService.record_chapter_word_change()`。

4. 统计事件与章节保存处于同一数据库事务：
   - 章节保存成功，统计事件一起提交。
   - 章节保存失败，统计事件一起回滚。

5. 新建章节和导入章节的初始内容不计入“今日写作净增”：
   - 历史正文只计入“当前总字数”。
   - 从功能上线后发生的正文编辑才进入每日/每小时统计。
   - 页面需要提示：“写作趋势从统计功能启用后开始记录，历史正文不会回填到每日净增。”

6. 当前阶段不新增 deadline 或复杂目标管理：
   - 复用 `projects.target_word_count` 做全书目标进度。
   - 每日目标、截止日期、里程碑可作为后续任务。

## 数据模型建议

新增 `writing_stat_events` 表。

字段建议：

- `id: str`
- `project_id: str`
- `chapter_id: str`
- `volume_id: str | None`
- `source: str`
  - `manual`
  - `autosave`
  - 后续可扩展 `import`、`restore`、`migration`
- `old_word_count: int`
- `new_word_count: int`
- `delta_words: int`
- `added_words: int`
- `deleted_words: int`
- `occurred_at: datetime`
- `local_date: str`
  - 格式：`YYYY-MM-DD`
  - 用于避免 SQLite 时区聚合复杂度。
- `local_hour: int`
  - `0` 到 `23`

索引建议：

- `(project_id, local_date)`
- `(project_id, local_date, local_hour)`
- `(project_id, chapter_id, local_date)`
- `chapter_id`

统计语义：

- `delta_words = new_word_count - old_word_count`
- `added_words = max(delta_words, 0)`
- `deleted_words = max(-delta_words, 0)`
- 主要 UI 展示 `net_words`，即 `delta_words` 聚合值。
- `added_words` 和 `deleted_words` 仅在详情/悬浮提示/高级信息里展示，不放在核心指标第一层。

关于连续写作：

- `current_streak_days` 建议按“当天是否有正文变更事件”计算，而不是只按净增大于 0。
- 原因：删改、压缩、重写也是写作行为；如果某天净减字数，不应直接打断连续写作。
- 每日净增数字仍可为负数。

关于今日写作时长：

- 当前项目没有编辑器心跳或会话记录，不应伪装为精确时间。
- V1 可基于今日事件时间估算活跃时长：
  - 同一项目当天事件按时间排序。
  - 相邻事件间隔小于等于 5 分钟，视为同一活跃片段。
  - 单个孤立事件计 1 分钟。
  - UI 文案必须标注为 `今日活跃时长（估算）`。
- 后续如需要更准确，可新增前端编辑会话 heartbeat 表，但不放入本轮。

## API 设计

新增接口：

`GET /api/projects/{project_id}/writing-stats/overview?days=90`

参数：

- `project_id: str`
- `days: int`
  - 默认 `90`
  - 允许值建议：`30`、`90`、`365`
  - 非允许值返回 422 或自动钳制到最近允许值，二选一；建议使用 Pydantic 校验返回 422。

响应结构建议：

```json
{
  "project_id": "string",
  "generated_at": "datetime",
  "range_days": 90,
  "total_words": 120000,
  "target_words": 300000,
  "progress_percent": 40.0,
  "today_net_words": 1800,
  "week_net_words": 8600,
  "month_net_words": 32000,
  "current_streak_days": 12,
  "longest_streak_days": 28,
  "average_daily_words_30d": 1066.7,
  "estimated_today_minutes": 95,
  "estimated_words_per_hour_today": 1136.8,
  "daily": [
    {
      "date": "2026-05-24",
      "net_words": 1800,
      "added_words": 2100,
      "deleted_words": 300,
      "event_count": 14,
      "active_minutes_estimated": 95
    }
  ],
  "hourly": [
    {
      "hour": 20,
      "net_words": 900,
      "event_count": 6
    }
  ],
  "volume_breakdown": [
    {
      "volume_id": "string",
      "title": "第一卷",
      "total_words": 50000,
      "chapter_count": 20
    }
  ],
  "chapter_rankings": [
    {
      "chapter_id": "string",
      "title": "第一章",
      "volume_id": "string",
      "volume_title": "第一卷",
      "total_words": 4500,
      "delta_words_7d": 1200,
      "updated_at": "datetime"
    }
  ],
  "warnings": [
    "写作趋势从统计功能启用后开始记录，历史正文不会回填到每日净增。"
  ]
}
```

错误处理：

- 项目不存在：404，`Project not found`
- `days` 非法：422
- 服务层不得吞掉数据库错误。

## 前端边界

1. 新增页面：
   - `frontend/src/pages/stats/ProjectWritingStatsPage.vue`

2. 新增 entity：
   - `frontend/src/entities/writing-stats/types.ts`
   - `frontend/src/entities/writing-stats/api.ts`

3. 新增可复用展示组件，建议放在：
   - `frontend/src/features/stats/StatsMetricStrip.vue`
   - `frontend/src/features/stats/WritingHeatmap.vue`
   - `frontend/src/features/stats/DailyWordsChart.vue`
   - `frontend/src/features/stats/HourlyActivityChart.vue`
   - `frontend/src/features/stats/ChapterRankingTable.vue`
   - `frontend/src/features/stats/statsFormatters.ts`

4. 图表不要新增重型依赖：
   - 热力图用 CSS Grid。
   - 日/小时柱状图用 HTML/CSS 或轻量 SVG。
   - 章节排行用表格或紧凑列表。
   - 不引入 ECharts、Chart.js、D3 等，除非用户明确要求。

5. 页面导航：
   - `frontend/src/router/index.ts` 新增 `/projects/:projectId/stats`。
   - `frontend/src/pages/projects/ProjectDetailPage.vue` 顶部工具区新增 `统计` 入口。

6. UI 应使用已有主题变量：
   - `--zs-module-stats`
   - `--zs-heatmap-0` 到 `--zs-heatmap-4`
   - `--zs-color-*`
   - `--zs-space-*`

7. 统计页使用居中内容容器：
   - 宽屏不要无限拉伸。
   - 建议 `max-width: 1180px` 到 `1280px`。
   - 小窗口下指标和图表自动降为单列或两列。

# Files to Create or Modify

## Backend - Create

1. `backend/app/models/writing_stat_event.py`
   - 定义 `WritingStatEvent`。
   - 包含索引。

2. `backend/app/repositories/writing_stats_repo.py`
   - 只负责写入事件和查询聚合所需数据。
   - 不写业务判断。

3. `backend/app/schemas/writing_stats.py`
   - 定义 API 响应模型。
   - 定义 `days` 查询参数校验需要的类型或常量。

4. `backend/app/services/writing_stats_service.py`
   - 负责记录字数变化事件。
   - 负责汇总 total/today/week/month/streak/heatmap/hourly/volume/chapter ranking。
   - 负责生成用户可理解 warnings。

5. `backend/app/api/writing_stats.py`
   - 暴露 `GET /api/projects/{project_id}/writing-stats/overview`。

6. `backend/tests/test_writing_stats_service.py`
   - 覆盖服务层核心统计逻辑。

7. 可选：`backend/tests/test_writing_stats_api.py`
   - 如果现有测试环境方便使用 FastAPI TestClient，可增加 API 层 404/422/200 测试。

## Backend - Modify

1. `backend/app/main.py`
   - import `writing_stats_router`。
   - `app.include_router(writing_stats_router)`。

2. `backend/app/infrastructure/database.py`
   - 在 `init_database()` 中 import 新模型，确保 `Base.metadata.create_all()` 创建新表。
   - 不需要为新表写 `ALTER TABLE`，除非 Claude Code 发现本地 SQLite 旧表结构已存在但缺字段。

3. `backend/app/services/chapter_service.py`
   - 在 `update_chapter()` 中保存 `old_word_count`。
   - 仅当正文变更且 `new_word_count != old_word_count` 时调用 `WritingStatsService.record_chapter_word_change(...)`。
   - 调用必须在同一事务内，`commit=False` 风格，不单独提交。

## Frontend - Create

1. `frontend/src/entities/writing-stats/types.ts`
   - 与后端响应结构一一对应。

2. `frontend/src/entities/writing-stats/api.ts`
   - `getWritingStatsOverview(projectId: string, days?: 30 | 90 | 365)`。

3. `frontend/src/pages/stats/ProjectWritingStatsPage.vue`
   - 写作统计仪表盘页面。

4. `frontend/src/features/stats/StatsMetricStrip.vue`
   - 顶部核心指标条。

5. `frontend/src/features/stats/WritingHeatmap.vue`
   - 写作热力图。

6. `frontend/src/features/stats/DailyWordsChart.vue`
   - 日净增柱状图。

7. `frontend/src/features/stats/HourlyActivityChart.vue`
   - 小时分布图。

8. `frontend/src/features/stats/ChapterRankingTable.vue`
   - 章节排行。

9. `frontend/src/features/stats/statsFormatters.ts`
   - 数字、百分比、分钟、日期、热力等级计算。

10. `frontend/src/__tests__/writing-stats.spec.ts`
    - 测试格式化和热力等级等纯函数。

## Frontend - Modify

1. `frontend/src/router/index.ts`
   - 新增 `ProjectWritingStatsPage` import。
   - 新增路由：
     - path: `/projects/:projectId/stats`
     - name: `project-stats`

2. `frontend/src/pages/projects/ProjectDetailPage.vue`
   - 顶部工具区新增：
     - `<RouterLink class="toolbar-link" :to="`/projects/${projectId}/stats`">统计</RouterLink>`
   - 位置建议：`搜索`、`检查` 之后。

# Implementation Steps for Claude Code

1. 再次确认当前交接文件状态：
   - 确认本计划为当前唯一活跃 `CODEX_PLAN.md`。
   - 不读取 `docs/ai-handoff/archive/` 的历史计划，除非需要对比某个旧功能。

2. 后端新增模型：
   - 创建 `backend/app/models/writing_stat_event.py`。
   - 使用与现有 model 一致的 `utc_now()` 风格。
   - 字段和索引按本计划“数据模型建议”实现。
   - 外键：
     - `project_id -> projects.id`
     - `chapter_id -> chapters.id`
     - `volume_id -> volumes.id`，nullable。

3. 后端注册模型：
   - 修改 `backend/app/infrastructure/database.py`。
   - 在 `init_database()` 中 import `app.models.writing_stat_event`。
   - 不改动其他已有迁移辅助函数。

4. 后端新增 Repository：
   - 创建 `backend/app/repositories/writing_stats_repo.py`。
   - 至少提供：
     - `create_event(event: WritingStatEvent, *, commit: bool = True) -> WritingStatEvent`
     - `list_events(project_id: str, start_date: str | None, end_date: str | None) -> list[WritingStatEvent]`
     - `aggregate_daily(project_id: str, start_date: str, end_date: str)`
     - `aggregate_hourly(project_id: str, start_date: str, end_date: str)`
     - `aggregate_chapter_delta(project_id: str, start_date: str, end_date: str)`
   - 可使用 SQLAlchemy `func.sum` 和 `group_by`。
   - Repository 不判断 streak，不拼 UI 文案。

5. 后端新增 Schema：
   - 创建 `backend/app/schemas/writing_stats.py`。
   - 建议包含：
     - `WritingStatsDailyPoint`
     - `WritingStatsHourlyPoint`
     - `WritingStatsVolumeBreakdownItem`
     - `WritingStatsChapterRankingItem`
     - `WritingStatsOverview`
   - 所有响应字段保持英文。

6. 后端新增 Service：
   - 创建 `backend/app/services/writing_stats_service.py`。
   - 注入：
     - `ProjectRepository`
     - `ChapterRepository`
     - `VolumeRepository`
     - `WritingStatsRepository`
   - 实现：
     - `record_chapter_word_change(...)`
     - `get_overview(project_id: str, days: int = 90)`
   - `get_overview()` 必须：
     - 校验项目存在。
     - 当前总字数只统计 `deleted_at is None` 的章节。
     - 分卷统计按 active volume 汇总；无分卷章节归入 `volume_id: null`，标题可为 `未分卷`。
     - today/week/month 使用 `local_date` 聚合。
     - heatmap 使用返回的 `daily`。
     - 章节排行既显示当前 `total_words`，也显示最近 7 天 `delta_words_7d`。
     - 添加 warnings：历史正文不会回填每日净增。

7. 在章节更新路径记录事件：
   - 修改 `backend/app/services/chapter_service.py`。
   - 在读取 `values` 后、更新前保存：
     - `old_word_count = chapter.word_count`
     - `old_volume_id = chapter.volume_id`
   - 更新后得到 `new_word_count = updated_chapter.word_count`。
   - 条件：
     - `content_changed is True`
     - `new_word_count != old_word_count`
   - 调用：
     - `WritingStatsService(self.db).record_chapter_word_change(...)`
   - 传参建议：
     - `project_id=updated_chapter.project_id`
     - `chapter_id=updated_chapter.id`
     - `volume_id=updated_chapter.volume_id`
     - `source=str(save_source)`
     - `old_word_count=old_word_count`
     - `new_word_count=new_word_count`
     - `occurred_at=updated_chapter.updated_at`
   - 该方法必须 `commit=False`，由 `ChapterService.update_chapter()` 统一 commit。
   - 如果只改标题、状态、分卷，不记录字数事件。
   - 如果正文变化但字数相同，不记录字数事件；这是 V1 可接受限制。

8. 后端新增 API：
   - 创建 `backend/app/api/writing_stats.py`。
   - 路由：
     - `GET /api/projects/{project_id}/writing-stats/overview`
   - 查询参数：
     - `days: Literal[30, 90, 365] = 90` 或等价校验。
   - 404：
     - 捕获 `WritingStatsProjectNotFoundError`。
   - 注册到 `backend/app/main.py`。

9. 后端测试：
   - 创建 `backend/tests/test_writing_stats_service.py`。
   - 至少覆盖：
     - 项目不存在时报错。
     - 当前总字数只统计 active chapters。
     - `record_chapter_word_change()` 正确保存 delta/added/deleted/local_date/local_hour。
     - 字数不变时不记录事件。
     - 今日、本周、本月聚合正确。
     - 连续写作按有事件日期计算，净负数字的日期也算 active day。
     - 分卷统计包含 `未分卷`。
     - 章节排行按最近 7 天增量排序。
     - 历史已有章节不会被计入今日净增。

10. 前端新增 entity：
    - 创建 `frontend/src/entities/writing-stats/types.ts`。
    - 创建 `frontend/src/entities/writing-stats/api.ts`。
    - API 函数：
      - `getWritingStatsOverview(projectId, days = 90)`。

11. 前端新增格式化工具：
    - 创建 `frontend/src/features/stats/statsFormatters.ts`。
    - 建议函数：
      - `formatNumber(value: number): string`
      - `formatSignedWords(value: number): string`
      - `formatPercent(value: number | null): string`
      - `formatMinutes(value: number): string`
      - `getHeatmapLevel(netWords: number): 0 | 1 | 2 | 3 | 4`
    - 热力等级按 UI 文档：
      - `<= 0`: 0
      - `1-499`: 1
      - `500-1999`: 2
      - `2000-4999`: 3
      - `5000+`: 4

12. 前端新增组件：
    - `StatsMetricStrip.vue`
      - 接收 overview。
      - 展示：
        - 总字数
        - 今日净增
        - 本周净增
        - 本月净增
        - 连续写作
        - 今日活跃时长（估算）
        - 近 30 日日均
      - 不展示过多 debug 字段。
    - `WritingHeatmap.vue`
      - 接收 daily list。
      - CSS grid。
      - 使用 `--zs-heatmap-*`。
      - tooltip/title 包含日期、净增、增删详情。
    - `DailyWordsChart.vue`
      - 展示 selected range 内每日净增。
      - 支持负值，用不同轻量颜色或基线处理。
    - `HourlyActivityChart.vue`
      - 0-23 小时柱状图。
      - 空数据时显示简短空状态。
    - `ChapterRankingTable.vue`
      - 展示章节标题、分卷、当前字数、近 7 天净增、更新时间。
      - 表格宽度局部滚动，不让页面整体横向滚动。

13. 前端新增页面：
    - 创建 `frontend/src/pages/stats/ProjectWritingStatsPage.vue`。
    - 页面结构建议：
      - Header：
        - 返回写作页：`/projects/${projectId}`
        - 标题：`写作统计`
        - Range segmented control：`30天`、`90天`、`全年`
        - 刷新按钮
      - 主区域：
        - 顶部指标条
        - 目标进度条
        - 热力图
        - 日净增图
        - 小时分布图
        - 分卷字数分布
        - 章节增长排行
      - 空状态：
        - 无统计事件时，仍显示当前总字数和目标进度。
        - 图表区提示“写作趋势从现在开始记录”。
      - 错误状态：
        - 项目不存在或接口失败时显示中文错误。

14. 前端新增路由和入口：
    - 修改 `frontend/src/router/index.ts`。
    - 修改 `frontend/src/pages/projects/ProjectDetailPage.vue`。
    - 不要重写 `ProjectDetailPage.vue`，只添加一个入口链接。

15. 前端测试：
    - 创建 `frontend/src/__tests__/writing-stats.spec.ts`。
    - 覆盖：
      - 热力等级边界。
      - 正负字数格式化。
      - 分钟格式化。
      - 百分比格式化。

16. 手动验证：
    - 新建项目或使用现有项目。
    - 设置目标字数。
    - 打开写作页编辑章节正文。
    - 保存后进入统计页。
    - 检查今日净增、总字数、热力图、小时图、章节排行是否更新。
    - 修改正文删减字数，检查净增为负时 UI 是否合理。

# Constraints

1. Codex 未修改业务代码，本计划应由 Claude Code 执行。

2. Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，不要强行实现。

3. 不要把 UI、统计业务逻辑、数据库查询混在同一个文件：
   - UI 只调用 `entities/writing-stats/api.ts`。
   - API 层只做路由、参数和异常映射。
   - Service 层做统计业务。
   - Repository 层只做查询和写入。

4. 不新增大型图表库。

5. 不新增 AI、RAG、向量检索或知识图谱逻辑。

6. 不修改知识库、人物、设定、伏笔、时间线等无关模块。

7. 不重写 `ProjectDetailPage.vue`、`ChapterEditor.vue`、`ChapterTree.vue`。

8. 不改变现有章节保存 API 的请求/响应结构。

9. 不把导入历史正文计入今日写作。

10. 不把“估算写作时长”显示成精确计时。

11. 不提交或读取：
    - API keys
    - `.env`
    - 本地数据库
    - `data/`
    - `logs/`
    - `release/`

12. 用户可见 UI 文案使用简体中文。

13. 代码标识符、API 路径、数据库表名保持英文。

# Verification Commands

后端单项测试：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_writing_stats_service.py
```

如新增 API 测试：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests\test_writing_stats_api.py
```

后端全量测试：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest
```

前端类型检查：

```powershell
cd frontend
npm run type-check
```

前端单项测试：

```powershell
cd frontend
npm run test:unit -- writing-stats
```

前端构建：

```powershell
cd frontend
npm run build
```

手动运行验证：

```powershell
.\start-zhangshu-dev.bat
```

手动验证路径：

- `http://localhost:5173/projects`
- 打开某个项目。
- 修改并保存章节正文。
- 进入 `/projects/{projectId}/stats`。

# Acceptance Criteria

1. 项目详情页顶部有 `统计` 入口，能进入 `/projects/{projectId}/stats`。

2. 统计页能正常加载，项目不存在时有中文错误提示。

3. 当前总字数等于所有未删除章节 `word_count` 之和。

4. 项目设置了 `target_word_count` 时，统计页显示目标进度；未设置时显示“未设置目标”类提示。

5. 修改章节正文并保存后：
   - 如果字数增加，今日净增增加。
   - 如果字数减少，今日净增减少。
   - 如果正文变化但字数不变，不新增字数变化事件。

6. 今日、本周、本月净增统计准确。

7. 连续写作按有正文变更事件的日期计算。

8. 今日活跃时长标注为“估算”，不误导用户。

9. 热力图使用现有主题变量，浅色、护眼、黑夜主题下都可读。

10. 日净增图、小时图和章节排行不会在宽屏无限拉伸，也不会在窄屏产生页面级横向滚动。

11. 分卷统计包含未分卷章节。

12. 章节排行显示章节标题、分卷、当前字数、近 7 天净增、更新时间。

13. 页面不突出 `added_words` / `deleted_words` 这类工程调试字段，只在 tooltip 或详情里辅助展示。

14. 后端测试通过。

15. 前端类型检查、单元测试和构建通过。

# Risks and Watchpoints

1. 历史统计不可回填：
   - 当前没有完整写作事件源，不能伪造过去每日数据。
   - UI 必须说明趋势从启用后开始记录。

2. 自动保存可能造成事件较多：
   - SQLite 对本地单人写作足够，但未来如事件表过大，可增加日聚合表。
   - V1 先不做聚合表，避免过早复杂化。

3. “写作时长”只能估算：
   - 事件间隔估算不等于真实编辑时间。
   - 必须用“活跃时长（估算）”文案。

4. 字数算法为非空白字符计数：
   - 符合当前项目实现。
   - 不要在本任务中更换算法，否则会影响导入、章节保存和已有数据一致性。

5. 删除或大规模重写会产生负净增：
   - UI 要能显示负值。
   - 不要把负值当作错误。

6. 导入正文不应污染今日写作：
   - 如果 Claude Code 发现导入流程会走 `ChapterService.update_chapter()`，需要确保 source 能区分，或在导入路径禁用事件记录。
   - 如果导入只创建章节，则按本计划不会记录事件。

7. 分卷移动不应改变历史事件：
   - 历史事件保留当时的 `volume_id`。
   - 当前分卷字数用当前章节归属计算。
   - 这两者语义不同，服务层要分清楚。

8. 章节恢复版本可能导致大幅 delta：
   - 如果恢复版本走 `update_chapter()`，应记录为一次正文变化。
   - 这是合理行为，但 UI 不应将其解释为纯新增。

9. 性能：
   - `overview` 不应返回所有事件明细。
   - 只返回聚合后的 daily/hourly/chapter/volume 数据。

10. UI 密度：
    - 仪表盘不要做成一堆大型卡片。
    - 指标要紧凑，图表要可扫读。

# Review Checklist

Claude Code 执行完成后，请生成 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`，并说明实际修改文件、测试结果和偏离计划之处。

Codex 复审时应检查：

1. 是否只实现写作统计仪表盘相关文件，没有改动无关业务模块。

2. 是否新增了清晰的统计边界：
   - Model
   - Repository
   - Schema
   - Service
   - API
   - Frontend entity
   - Frontend page/components

3. `ChapterService.update_chapter()` 是否只是调用统计服务，没有把聚合逻辑写入章节服务。

4. API 层是否只做路由、参数校验和异常映射。

5. Repository 是否没有业务判断。

6. 统计事件是否与章节保存共用事务。

7. 是否避免把导入历史正文计入今日写作。

8. 是否正确处理：
   - 正 delta
   - 负 delta
   - zero delta
   - deleted chapters
   - unassigned volume
   - missing project

9. 前端是否使用已有主题变量和热力图颜色变量。

10. 前端是否没有新增大型图表依赖。

11. 页面在小窗口下是否不会横向溢出。

12. UI 是否使用简体中文文案。

13. 是否有测试覆盖服务层核心聚合逻辑。

14. `npm run type-check`、`npm run build`、后端 pytest 是否通过。

15. git diff 中是否没有：
    - API keys
    - `.env`
    - 本地数据库
    - 日志
    - 临时文件
    - 构建产物

最终复审结论应为：

- Accept
- Minor Revision
- Rework
