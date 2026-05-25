# 掌书 Next

掌书 Next 是一个本地优先的网络小说写作应用原型。当前阶段聚焦项目、分卷、章节管理，以及基础章节编辑与保存。

## 技术栈

- Frontend: Vue 3 + TypeScript + Vite
- Backend: Python + FastAPI + SQLAlchemy + SQLite
- Local Database: SQLite
- Desktop Shell: Tauri v2（已实现 V1）
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
- 写作工作区三栏布局：左侧分卷/章节树、中间正文编辑器、右侧写作资料面板
- 左侧章节树与右侧写作资料面板支持折叠/展开，并记住每个项目的工作区状态
- 编辑器外观设置：字号、行距、首行缩进、编辑宽度、护眼/深色显示模式、字体预设与自定义字体名称
- 编辑器会话统计：当前字数、本次写作时长、估算写作速度
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
- 伏笔库与本章伏笔绑定
- 设定集与本章设定绑定
- 时间轴事件、轨道和连接关系管理
- 时间轴事件 / 大纲条目与人物、设定、伏笔等创作资料的显式联动
- 关系图节点与关系画布
- 违禁词 / 敏感词检查
- 违禁词 / 敏感词词库 JSON 导入导出

## 写作工作区与编辑器

- 写作页以正文创作为中心，左侧保留分卷/章节树，右侧提供大纲、人物、设定、关系图、时间轴、伏笔和版本等写作资料。
- 左侧章节树和右侧资料面板可以折叠，折叠状态保存在 `localStorage` 的 `zhangshu:workspace:{project_id}` 中。
- 分卷/章节树支持右键菜单、章节选择和拖拽排序；新建章节、新建分卷入口放在对应列表底部。
- 编辑器正文仍使用原生 `<textarea>`，章节正文以纯文本保存，不写入 HTML、样式标签或富文本片段。
- 编辑器顶部显示当前字数、本次写作时长、估算速度、上次保存时间和保存状态。
- 写作会话统计只存在于当前前端会话中，不上传后端；连续 3 分钟无输入会暂停本次写作计时。
- 编辑器外观设置保存在 `localStorage` 的 `zhangshu:editor:appearance` 中，仅影响本机显示，不改变章节正文内容。
- 可调整字号、行距、首行缩进、编辑宽度、段间距、护眼/深色显示模式、字体预设和自定义字体名称。
- 字体通过 CSS `font-family` 调用本机已安装字体；项目不复制、不打包、不随 release 分发 Windows、macOS 或其他专有字体文件。
- 如果用户希望使用特定字体，需要先在自己的系统中安装该字体；未安装时浏览器会按后备字体自动回退。

## 检查与词库

- 检查入口：项目写作页顶部工具栏点击“检查”，进入 `/projects/{project_id}/review`。
- 当前检查功能基于用户维护的违禁词 / 敏感词词库，不做 AI 审稿、语义分析或云端检查。
- 检查范围支持当前章节、当前分卷和全书。
- 检查结果会显示命中词、严重程度、位置、建议和对应章节，并可跳回写作页打开章节。
- 词库条目包括匹配词、严重程度、替换/处理建议和启用状态。
- 词库支持 JSON 导出：`GET /api/review/prohibited-terms/export`。
- 词库支持 JSON 导入：`POST /api/review/prohibited-terms/import`。
- 导入 JSON 使用 `term` 文本去重；已存在词条会更新严重程度、建议和启用状态，不会创建完全重复的词条。
- 导入导出只处理词库数据，不执行导入文件中的任何内容。

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

## 创作资料显式联动

- 时间轴事件现在可以显式关联人物、设定和伏笔，分别使用 `timeline_event_characters`、`timeline_event_settings`、`timeline_event_clues`。
- 大纲条目现在可以显式关联人物、设定、伏笔和时间轴事件，分别使用 `outline_item_characters`、`outline_item_settings`、`outline_item_clues`、`outline_item_timeline_events`。
- 这些关系由用户手动维护，用于后续写作页、时间轴、关系图和资料面板复用稳定的显式绑定结果。
- 当前仍不做 AI 自动抽取、语义匹配、RAG 或章节正文推断。

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
- 时间轴连接支持点击选择、右侧详情查看和编辑；可维护起点事件、终点事件、关系类型、时序关系、线条样式、标签、批注和可见性。
- 时间轴连接支持删除；隐藏或弱化连接会影响画布显示。
- 时间轴画布会在右侧详情面板打开/关闭、浏览器尺寸变化、轨道显隐变化后重新计算连接线位置。
- 跨轨道连接默认使用曲线展示，并对相近连接做轻微偏移，以减少连接线穿过节点的情况。
- 时间轴事件支持 `事件类型`、`故事日期`、`故事时间`、`排序序号`、`重要程度`、`状态`、`关联章节`、`关联地点设定` 和备注。
- 事件类型包括 `plot`（剧情事件）、`background`（背景事件）、`character`（人物事件）、`world`（世界事件）、`clue`（伏笔事件）、`conflict`（冲突事件）、`custom`（自定义）。
- 状态包括 `planned`（计划中）、`happened`（已发生）、`revised`（已调整）、`deprecated`（已废弃）。
- 重要程度包括 `low`（低）、`normal`（普通）、`high`（重要）、`critical`（核心）。
- 写作页右侧“时间轴”Tab 会显示当前章节绑定的时间轴事件，按章节查看故事推进、剧情节点和发生顺序。
- 时间轴事件已经提供与人物、设定、伏笔的显式关联表和 API；时间轴卡片仍然基于显式绑定结果，不做 AI 或语义匹配。

## 关系图

- 关系图入口：项目详情页顶部和写作页右侧资料面板都可以跳转到 `/projects/{project_id}/graph`。
- 后端数据表：`graph_nodes`、`graph_edges`。
- 图节点支持绑定人物、设定、伏笔、时间轴事件，也支持纯手工创建的自定义节点。
- 图节点支持保存 `x / y` 坐标，拖动后会持久化，刷新页面后仍然保留位置。
- 图关系支持关系类型、方向、强度、线条样式、可见性、标签和批注。
- 当前阶段的图谱仍然基于显式创建和显式绑定，不做 AI 自动抽取、语义匹配或章节内容推断。
- 写作页右侧“关系图”Tab 会显示当前章节的关系图卡片，只抽取与本章人物、设定、伏笔、时间轴事件显式绑定的本章相关节点、直接关系和关联节点。
- 右侧关系图卡片目前不做 AI / 语义匹配，后续如果需要扩展，可以再叠加关键词、共现或 AI 候选匹配，但这一阶段不做。

## 桌面版（Tauri）

章枢支持通过 Tauri v2 作为 Windows 桌面应用运行。桌面版会自动启动 FastAPI 后端作为 sidecar，并加载 Vue 前端。

### Web 开发与桌面开发的区别

| | Web 开发 | 桌面开发 |
|---|---|---|
| 启动方式 | 分别启动前后端 | `npm run tauri:dev` 一键启动 |
| 数据目录 | 仓库内 `data/` | `%LOCALAPPDATA%/com.zhangshu.desktop/data/` |
| 后端端口 | 8000 | 8765（固定） |
| 前端端口 | 5180 | 由 Tauri 加载静态资源 |

注意：Web 开发和桌面版使用不同的数据库，同一项目在两种模式下数据不互通。

### 环境要求

- Node.js ≥ 20.19.0
- Rust stable（MSVC 工具链）
- Python 3.x + PyInstaller（用于打包 sidecar）

### 桌面开发

```powershell
cd frontend
npm run tauri:dev
```

该命令会启动 Vite 开发服务器和 Tauri 桌面窗口，后端 sidecar 会自动启动。

### 桌面打包

```powershell
cd frontend
npm run tauri:build
```

打包输出位于 `frontend/src-tauri/target/release/bundle/`。

### 数据目录

桌面版数据存储在系统应用数据目录：

```text
%LOCALAPPDATA%\com.zhangshu.desktop\
├── data/
│   └── zhangshu.sqlite3
└── logs/
```
