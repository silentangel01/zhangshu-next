# 章枢

章枢是一个本地优先的网络小说写作应用原型。当前阶段聚焦项目、分卷、章节管理，以及基础章节编辑与保存。

## 技术栈

- Frontend: Vue 3 + TypeScript + Vite
- Backend: Python + FastAPI + SQLAlchemy + SQLite
- Local Database: SQLite
- Desktop Shell: Tauri，后续阶段规划
- Search: SQLite FTS5，后续阶段规划
- AI/RAG: 后续阶段规划

## 开发环境

推荐仓库路径：

```text
C:\dev\zhangshu-next
```

### 启动后端

```powershell
cd C:\dev\zhangshu-next\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端 API 文档：

```text
http://127.0.0.1:8000/docs
```

### 启动前端

```powershell
cd C:\dev\zhangshu-next\frontend
npm run dev
```

前端入口：

```text
http://localhost:5173/projects
```

## 当前功能

- 项目 CRUD
- 分卷 CRUD
- 章节 CRUD
- 项目列表页
- 项目详情页
- 分卷/章节树
- 基础章节编辑器
- 手动保存章节正文
- 2 秒防抖自动保存
- 浏览器本地恢复稿原型
- 章节版本历史
- 手动创建版本快照
- 从历史版本恢复正文
- 旧版 JSON 导入预览与确认导入
- 文件夹压缩包导入预览与确认导入
- 基础大纲模块
- 章节细纲与章节编辑器联动
- 人物库与人物卡
- 本章人物绑定与写作页人物资料查看

## 章节版本历史

- 手动保存正文时，如果内容发生变化，后端会创建 `manual` 版本快照。
- 自动保存仍会保存当前正文，但版本快照会节流：距离上一条版本超过 5 分钟，或正文非空白字符变化达到 200 字以上时，才创建 `autosave` 版本。
- 用户可以在章节详情中点击“创建版本快照”手动保存当前版本。
- 恢复历史版本前，系统会先创建 `before_restore` 快照，再用历史版本覆盖当前章节正文，并记录 `restore` 快照。
- 当前阶段不实现完整版本对比、云备份或同步。

## 导入作品

- 导入入口：`http://localhost:5173/imports`。
- 当前支持旧版 JSON：`.json`。
- 当前支持文件夹压缩包：`.zip`，压缩包内支持 `.txt` 和 `.md` 章节文件。
- 文件夹压缩包会按顶层目录推断项目名，第一层文件夹作为分卷，文本文件作为章节。
- 解析文本时按 `UTF-8`、`UTF-8-SIG`、`GBK` 的顺序尝试编码，无法识别的文件会进入导入报告的失败文件列表。
- 导入前会先调用 `POST /api/imports/preview` 生成预览，不会立即写入 SQLite。
- 确认导入会调用 `POST /api/imports/{import_id}/confirm` 创建新项目、分卷和章节。
- 当前只支持创建新项目，不会覆盖现有项目。
- 导入报告保存在 `data/imports/reports/`，预览和临时文件保存在 `data/imports/`。

## 大纲与细纲

- 大纲入口：项目详情页点击“打开大纲”，进入 `/projects/{project_id}/outlines`。
- 后端数据表：`outline_items`。
- 大纲条目支持父子层级，使用 `parent_id` 和 `order_index` 组织树形结构。
- 条目类型包括 `book_outline`、`volume_outline`、`chapter_outline`、`scene`、`plot_point`、`note`。
- 状态包括 `planned`、`writing`、`done`、`abandoned`。
- 重要程度包括 `normal`、`important`、`critical`。
- 大纲条目可以绑定分卷或章节，用于“大纲规划 → 绑定章节 → 写作时查看细纲”的基础流程。
- 章节编辑器旁会显示“当前章节细纲”，内容来自 `GET /api/chapters/{chapter_id}/outlines`。
- 当前阶段不实现 AI 大纲生成、拖拽排序、复杂图谱或角色/线索/设定联动。

## 人物库

- 人物库入口：项目写作页点击“人物库”，进入 `/projects/{project_id}/characters`。
- 后端数据表：`characters` 和 `chapter_characters`。
- 人物卡字段包括姓名、角色定位、重要程度、状态、所属势力、简介、人物小传、外貌、性格、背景、能力、动机、秘密、成长线、备注。
- 章节人物绑定通过 `POST /api/chapters/{chapter_id}/characters` 创建，支持关系类型 `appears`、`mentioned`、`pov`、`conflict`、`supports`。
- 写作页右侧“人物”Tab 会显示当前章节绑定的人物、角色定位、关系类型、简介和备注。
- 删除人物使用软删除；删除章节人物关联会直接移除关联记录。
- 当前阶段不实现关系图、AI 抽取人物、时间线或设定联动。

## 编码说明

- 所有源文件和文档都应使用 UTF-8。
- 避免把文件保存为 GBK/ANSI。
- 如果遇到编码、权限或文件锁问题，避免把项目放在中文路径或 OneDrive 同步路径中。
- 推荐路径：`C:\dev\zhangshu-next`

## 伏笔库

- 伏笔库入口：项目写作页右侧资料面板点击“打开伏笔库”，进入 `/projects/{project_id}/clues`。
- 后端数据表：`clues`、`chapter_clues`、`clue_characters`、`clue_settings`。
- 伏笔状态包括 `planned`（计划中）、`planted`（已埋设）、`developing`（推进中）、`resolved`（已回收）、`abandoned`（已废弃）。
- 可见程度包括 `hidden`（隐藏）、`hinted`（暗示）、`revealed`（已揭示）。
- 伏笔支持记录埋设章节、回收章节、重要程度、描述、回收计划、实际回收和备注。
- 本章伏笔绑定通过 `POST /api/chapters/{chapter_id}/clues` 创建，关系类型包括 `setup`（埋设）、`mention`（提及）、`develop`（推进）、`payoff`（回收）、`related`（相关）。
- 写作页右侧“伏笔”Tab 会显示当前章节绑定的伏笔、关系类型、生命周期状态、可见程度、重要程度、描述、回收计划和备注。
- 伏笔删除使用软删除；章节伏笔、人物伏笔、设定伏笔关联删除会直接移除关联记录。
- 当前阶段不实现关系图、时间轴、AI 自动提取伏笔、RAG、同步、Tauri 写作房间、全文搜索或检查功能。

## 时间轴

- 时间轴入口：项目写作页右侧资料面板点击“打开时间轴”，进入 `/projects/{project_id}/timeline`。
- 后端数据表：`timeline_events`。
- 时间轴连接使用 `timeline_edges`，并支持 `temporal_relation`（过去 / 前置、并行、滞后、后续、无明确时序）来描述两个事件的时序关系。
- 时间轴事件支持 `事件类型`、`故事日期`、`故事时间`、`排序序号`、`重要程度`、`状态`、`关联章节`、`关联地点设定` 和备注。
- 事件类型包括 `plot`（剧情事件）、`background`（背景事件）、`character`（人物事件）、`world`（世界事件）、`clue`（伏笔事件）、`conflict`（冲突事件）、`custom`（自定义）。
- 状态包括 `planned`（计划中）、`happened`（已发生）、`revised`（已调整）、`deprecated`（已废弃）。
- 重要程度包括 `low`（低）、`normal`（普通）、`high`（重要）、`critical`（核心）。
- 写作页右侧“时间轴”Tab 会显示当前章节绑定的时间轴事件，按章节查看故事推进、剧情节点和发生顺序。
- 当前阶段未实现时间轴事件与人物、设定、伏笔的额外关联表，后续可按既有章节绑定模式补齐；时间轴卡片仍然基于显式绑定结果，不做 AI 或语义匹配。

## 关系图

- 关系图入口：项目详情页顶部和写作页右侧资料面板都可以跳转到 `/projects/{project_id}/graph`。
- 后端数据表：`graph_nodes`、`graph_edges`。
- 图节点支持绑定人物、设定、伏笔、时间轴事件，也支持纯手工创建的自定义节点。
- 图节点支持保存 `x / y` 坐标，拖动后会持久化，刷新页面后仍然保留位置。
- 图关系支持关系类型、方向、强度、线条样式、可见性、标签和批注。
- 当前阶段的图谱仍然基于显式创建和显式绑定，不做 AI 自动抽取、语义匹配或章节内容推断。
- 写作页右侧“关系图”Tab 会显示当前章节的关系图卡片，只抽取与本章人物、设定、伏笔、时间轴事件显式绑定的本章相关节点、直接关系和关联节点。
- 右侧关系图卡片目前不做 AI / 语义匹配，后续如果需要扩展，可以再叠加关键词、共现或 AI 候选匹配，但这一阶段不做。
