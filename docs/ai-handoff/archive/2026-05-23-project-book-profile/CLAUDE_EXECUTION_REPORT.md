---
date: 2026-05-23
task: project-book-profile
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

升级 Project 为书籍档案：后端新增 author、tags、cover_image_path、status、target_word_count 字段；新增封面上传/删除/读取 API；前端项目列表升级为书籍卡片，创建/编辑弹窗增加新字段，项目概览增强展示封面、作者、标签、状态、目标字数。

## Files Changed

### 后端

- 修改：`backend/app/models/project.py` — 新增 author、tags、cover_image_path、status、target_word_count 字段
- 修改：`backend/app/infrastructure/database.py` — 新增 `_ensure_project_book_columns()` 并在 `init_database()` 中调用，兼容旧 SQLite
- 修改：`backend/app/schemas/project.py` — 重写 Create/Update/Read schema，增加标签 normalize/encode/decode、状态校验、作者 strip
- 修改：`backend/app/services/project_service.py` — 更新 create/update 以处理新字段和标签编码，新增 `update_project_raw()` 方法
- 新建：`backend/app/infrastructure/project_cover_storage.py` — 封面文件存储基础设施，封装目录管理、MIME 校验、路径安全检查
- 新建：`backend/app/api/project_covers.py` — 封面上传/删除/读取 API 端点
- 修改：`backend/app/main.py` — 注册 project_covers_router
- 修改：`backend/app/services/backup_service.py` — 导出备份时包含封面文件到 zip，恢复时提取封面并写入新项目目录

### 前端

- 修改：`frontend/src/entities/project/types.ts` — 扩展 Project、CreateProjectPayload、UpdateProjectPayload，新增 ProjectStatus 类型
- 修改：`frontend/src/entities/project/api.ts` — 新增 getProjectCoverUrl、uploadProjectCover、deleteProjectCover
- 新建：`frontend/src/assets/default-book-cover.svg` — 默认书籍封面 SVG
- 新建：`frontend/src/features/projects/ProjectTagInput.vue` — 标签输入组件（chip 展示、回车添加、标签库建议）
- 新建：`frontend/src/features/projects/ProjectCoverUploader.vue` — 封面选择/预览/清除组件
- 修改：`frontend/src/features/projects/CreateProjectDialog.vue` — 增加作者、标签、状态、目标字数、封面选择
- 修改：`frontend/src/features/projects/EditProjectDialog.vue` — 同步增加所有新字段，封面上传/删除通过 emit 委托父级
- 修改：`frontend/src/pages/projects/ProjectsPage.vue` — 项目卡片升级为书籍卡片（封面 + 书名 + 作者 + 题材 + 状态 + 标签 + 简介），计算 tagSuggestions 合并内置标签和已有标签
- 修改：`frontend/src/pages/projects/ProjectDetailPage.vue` — 项目概览区增加封面、作者、标签、状态、目标字数展示

## Implementation Notes

### 数据库字段

| 字段 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| author | VARCHAR(128) | NULL | 作者名 |
| tags | TEXT | `'[]'` | JSON 字符串，API 层序列化为 `list[str]` |
| cover_image_path | VARCHAR(500) | NULL | 相对 DATABASE_DIR 的路径 |
| status | VARCHAR(32) | `'planning'` | planning/writing/paused/completed/archived |
| target_word_count | INTEGER | NULL | 目标字数 |

### 封面文件存储

- 路径：`DATABASE_DIR/project_covers/{project_id}/cover.{ext}`
- 允许类型：JPEG、PNG、WebP
- 大小上限：5MB
- 不使用上传原文件名，统一命名为 `cover.<ext>`
- 上传时自动清除同项目旧封面

### 标签处理

- 后端 normalize：trim、过滤空串、截断至 24 字符、去重保持顺序、最多 20 个
- 数据库存为 JSON 字符串，API 对外暴露为 `string[]`
- `ProjectRead` 的 `tags` 字段使用 `field_validator(mode="before")` 自动从 JSON 字符串解析为列表

### 备份/恢复

- 导出：封面文件写入 zip 的 `assets/project_cover/cover.<ext>`，manifest 中记录路径
- 恢复：提取封面写入新项目目录，更新 `cover_image_path`
- 兼容旧备份（无封面时不报错）

### 前端封面 URL

- 使用 `getProjectCoverUrl(projectId, version)` 拼接 `API_BASE_URL/api/projects/{id}/cover?v={version}`
- version 参数避免浏览器缓存旧封面

### 内置标签

- 默认：玄幻、都市、科幻、悬疑、历史、仙侠、奇幻、群像、长篇、短篇
- 合并当前项目列表中已有标签，去重后传给弹窗组件

## Deviations from Codex Plan

无实质偏离。封面 API 路由独立为 `project_covers.py` 而非合入 `projects.py`，是为了避免主 API 文件过大；功能和路由前缀完全一致。

## Verification Commands Run

- `npm run type-check` → ✅ 通过
- `npm run test:unit` → ✅ 通过（3 测试文件，20 测试用例）
- `npm run build` → ✅ 通过（191 模块，570ms）
- `python -m compileall app` → ✅ 通过
- `pytest` → ⚠️ 未安装 pytest 模块，无法运行

## Verification Results

全部可用验证命令通过。构建产物：CSS 146KB (gzip 19.8KB)，JS 374KB (gzip 112.4KB)。

## Known Issues

- pytest 未安装在后端虚拟环境中，后端单元测试无法执行。
- 封面文件存储在 `data/project_covers/`，已被 `.gitignore` 忽略。
- `ProjectDetailPage` 项目概览中未加入封面上传/编辑功能（仅在列表页的编辑弹窗中操作），这是有意为之，保持写作页简洁。

## Suggested Next Review Points for Codex

- 封面上传失败后是否需要在 UI 上自动重试或提供更详细的错误恢复流程。
- `project_covers` 路由独立文件是否可接受，还是应合并回 `projects.py`。
- 标签是否需要支持颜色、排序等高级功能（当前仅字符串数组）。
- 目标字数是否应在项目概览中展示完成进度（需要后端统计实际字数）。
