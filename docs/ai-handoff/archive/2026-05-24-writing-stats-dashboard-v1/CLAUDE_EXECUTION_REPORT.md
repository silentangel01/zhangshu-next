---
archived_at: 2026-05-24
archive_reason: writing-stats-dashboard-v1 completed
date: 2026-05-24
task: 写作统计仪表盘 V1
codex_plan: docs/ai-handoff/CODEX_PLAN.md (当前版本)
---

## Task Summary
实现"写作统计仪表盘"功能，包括后端统计事件表、聚合服务、API 端点，以及前端统计页面和组件。另含 3 项运行时 Hotfix。

## Files Changed

### 新增

- `backend/app/models/writing_stat_event.py` — WritingStatEvent ORM 模型，记录每次章节字数变化事件
- `backend/app/repositories/writing_stats_repo.py` — 统计事件 Repository，负责事件写入和聚合查询
- `backend/app/schemas/writing_stats.py` — Pydantic 响应 Schema，定义 API 返回结构
- `backend/app/services/writing_stats_service.py` — 统计业务逻辑 Service，包含事件记录和 overview 聚合
- `backend/app/api/writing_stats.py` — FastAPI Router，暴露 `GET /api/projects/{project_id}/writing-stats/overview`
- `backend/tests/test_writing_stats_service.py` — 33 个后端单元测试，覆盖核心统计逻辑
- `frontend/src/entities/writing-stats/types.ts` — 前端 TypeScript 类型定义
- `frontend/src/entities/writing-stats/api.ts` — 前端 API client
- `frontend/src/features/stats/statsFormatters.ts` — 格式化工具函数（数字、百分比、分钟、热力等级）
- `frontend/src/features/stats/StatsMetricStrip.vue` — 顶部核心指标条组件
- `frontend/src/features/stats/WritingHeatmap.vue` — GitHub 风格写作日历热力图组件
- `frontend/src/features/stats/DailyWordsChart.vue` — 每日净增柱状图组件
- `frontend/src/features/stats/HourlyActivityChart.vue` — 小时分布图组件
- `frontend/src/features/stats/ChapterRankingTable.vue` — 章节增长排行表格组件
- `frontend/src/features/stats/VolumeBreakdown.vue` — 分卷字数分布组件（Codex 计划未明确列出，但属于必要的展示组件）
- `frontend/src/pages/stats/ProjectWritingStatsPage.vue` — 写作统计仪表盘页面
- `frontend/src/__tests__/writing-stats.spec.ts` — 25 个前端单元测试，覆盖格式化纯函数

### 修改

- `backend/app/main.py` — 新增 `writing_stats_router` import 和 `app.include_router()`；CORS 白名单新增 `localhost:5180` 和 `127.0.0.1:5180`（Hotfix 0）
- `backend/app/infrastructure/database.py` — 在 `init_database()` 中 import `writing_stat_event` 模型；新增 `_ensure_writing_stat_event_columns()` 迁移函数，在 `create_all()` 之前执行，处理旧表 schema 不兼容问题（Hotfix 2）
- `backend/app/services/chapter_service.py` — 在 `update_chapter()` 中：正文变化且字数变化时调用 `WritingStatsService.record_chapter_word_change()`，同一事务内
- `backend/app/api/writing_stats.py` — `days` 参数从 `Literal[30, 90, 365]` 改为 `int` + 手动校验（Hotfix 1）
- `frontend/src/router/index.ts` — 新增 `ProjectWritingStatsPage` import 和 `/projects/:projectId/stats` 路由
- `frontend/src/pages/projects/ProjectDetailPage.vue` — 顶部工具区新增 `统计` 入口链接

## Implementation Notes

1. **WritingStatEvent 模型未添加 ForeignKey 约束**：作为高频追加写入的事件表，省略外键约束以提升性能，应用层通过 Service 保证引用完整性。
2. **local_date / local_hour 使用系统本地时区**：通过 `datetime.now().astimezone()` 获取本地时间，避免 SQLite 时区聚合复杂度。
3. **连续写作按"有事件日期"计算**：净增为负的日期也算活跃日，不打断连续写作。
4. **活跃时长估算**：基于事件间隔 ≤ 5 分钟视为同一活跃片段，孤立事件计 1 分钟。UI 标注为"估算"。
5. **ChapterService 调用 WritingStatsService 而非直接操作 Repository**：保持服务边界清晰，事件创建逻辑集中在 WritingStatsService。
6. **VolumeBreakdown 组件**：Codex 计划中"分卷字数分布"部分只提到功能需求，未单独列出组件文件名，实际新增了 `VolumeBreakdown.vue`。

## Deviations from Codex Plan

- 新增 `VolumeBreakdown.vue` 组件（Codex 计划文件清单中未列出，但功能需求中明确要求"分卷字数分布"展示）。
- 其余所有文件与 Codex 计划一致，无偏差。

## Verification Commands Run

- `npm run type-check` → ✅ 通过
- `npm run test:unit -- writing-stats` → ✅ 25 tests passed
- `npm run build` → ✅ 构建成功（460.74 kB JS + 214.78 kB CSS）
- `pytest tests/test_writing_stats_service.py` → ✅ 33 tests passed
- `pytest tests/`（全量） → ✅ 340 tests passed
- `TestClient` 直接调用 API → ✅ 200 OK，返回完整 overview 结构

## Verification Results

所有验证命令均通过，无失败。

## Known Issues

1. **历史正文不会回填**：统计功能启用前的章节编辑不会生成事件，UI 已包含相应提示。
2. **字数不变的内容编辑不记录事件**：如替换等量字符，这是 V1 可接受限制。
3. **DailyWordsChart 的负值显示**：目前负值柱状图使用 flex-start 对齐，视觉上从顶部向下生长，后续可优化为双向柱状图。
4. **Heatmap 月份标签布局**：使用 gridColumn 定位，在极窄窗口下可能不完全精确，但不影响功能。

## Suggested Next Review Points for Codex

1. WritingStatEvent 模型是否需要添加 ForeignKey 约束（当前省略以提升写入性能）。
2. 活跃时长估算算法（5 分钟间隔阈值）是否合理。
3. 章节排行限制为 Top 20 是否足够，是否需要分页。
4. DailyWordsChart 负值可视化是否需要改进为双向柱状图。
5. 是否需要在后续版本中添加每日目标、截止日期等进阶目标管理功能。

## Hotfix

### Hotfix 0: CORS 白名单缺少 5180 端口

- **问题**：前端 `localhost:5180` 请求后端 `127.0.0.1:8000` 时被 CORS 策略拦截，浏览器报 `No 'Access-Control-Allow-Origin' header`。与毕设项目端口冲突无关。
- **原因**：`backend/app/main.py` 中 CORS `allow_origins` 只配了 `5173` 端口，未包含章枢前端实际使用的 `5180`。可能是早期章枢前端用过 5173，后来改为 5180 避免与毕设冲突，但忘了同步更新后端 CORS 配置。
- **修复**：在 `allow_origins` 中新增 `"http://localhost:5180"` 和 `"http://127.0.0.1:5180"`。
- **影响文件**：`backend/app/main.py`

### Hotfix 1: API days 参数 422 错误

- **问题**：`GET /api/projects/{project_id}/writing-stats/overview?days=90` 返回 422 Unprocessable Entity。
- **原因**：FastAPI + Pydantic v2 + Python 3.14 环境下，`Literal[30, 90, 365]` 类型的 query 参数无法自动将字符串 `"90"` 转为 int，导致校验失败。
- **修复**：`backend/app/api/writing_stats.py` 将 `days: Literal[30, 90, 365]` 改为 `days: int`，在函数体内手动校验 `days in ALLOWED_RANGE_DAYS`，不合法时返回 422 并附带中文错误信息。
- **影响文件**：`backend/app/api/writing_stats.py`

### Hotfix 2: writing_stat_events 旧表 schema 不兼容导致 500 错误

- **问题**：API 返回 500 Internal Server Error，日志显示 `sqlite3.OperationalError: no such column: writing_stat_events.delta_words`（以及 `local_date`）。浏览器端因 500 未带 CORS header 而表现为 CORS 错误。
- **原因**：本地 SQLite 数据库中已存在一个早期版本的 `writing_stat_events` 表，列名与当前模型完全不同：

  | 旧列名 | 新列名 |
  |---|---|
  | `words_added` | `added_words` |
  | `words_removed` | `deleted_words` |
  | `net_words_delta` | `delta_words` |
  | `event_date` | (已移除) |
  | `total_word_count` | (已移除) |
  | `created_at` | `occurred_at` |
  | (不存在) | `old_word_count`, `new_word_count`, `volume_id`, `local_date`, `local_hour` |

  `Base.metadata.create_all()` 只创建不存在的表，不会修改已存在的表结构。
- **修复**：在 `backend/app/infrastructure/database.py` 中新增 `_ensure_writing_stat_event_columns()` 迁移函数，在 `create_all()` 之前执行：检测现有表是否包含所有 13 个必需列（`required_columns.issubset(existing_columns)`），若不兼容则 `DROP TABLE`，由 `create_all()` 重建。旧表无有效历史数据（统计事件是从功能启用后才开始记录的），重建不影响功能。
- **影响文件**：`backend/app/infrastructure/database.py`
