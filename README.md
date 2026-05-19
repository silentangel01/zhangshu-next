# 掌书 Next

掌书 Next 是一个本地优先的网络小说写作应用原型。当前阶段聚焦项目、分卷、章节管理，以及基础章节编辑与保存。

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

## 编码说明

- 所有源文件和文档都应使用 UTF-8。
- 避免把文件保存为 GBK/ANSI。
- 如果遇到编码、权限或文件锁问题，避免把项目放在中文路径或 OneDrive 同步路径中。
- 推荐路径：`C:\dev\zhangshu-next`
