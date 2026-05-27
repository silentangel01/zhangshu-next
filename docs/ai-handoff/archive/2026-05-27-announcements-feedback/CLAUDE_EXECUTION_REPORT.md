---
date: 2026-05-27
task: 章枢公告通知 + 用户反馈模块
codex_plan: docs/ai-handoff/CODEX_PLAN.md (公告通知 + 用户反馈)
---

## Task Summary
实现"章枢公告通知 + 用户反馈模块"，覆盖 cloud-server 数据模型/API/管理员接口、backend 本地代理、frontend 公告展示与反馈表单，共 9 个 Phase。

## Files Changed

### cloud-server（新增 15 个文件，修改 6 个文件）

新增：
- `cloud-server/app/models/announcement.py` — 公告 ORM 模型
- `cloud-server/app/models/feedback_ticket.py` — 反馈工单 ORM 模型
- `cloud-server/app/models/feedback_attachment.py` — 反馈附件 ORM 模型
- `cloud-server/app/schemas/announcement.py` — 公告请求/响应 schema
- `cloud-server/app/schemas/feedback.py` — 反馈请求/响应 schema
- `cloud-server/app/repositories/announcement_repo.py` — 公告数据访问层
- `cloud-server/app/repositories/feedback_repo.py` — 反馈数据访问层
- `cloud-server/app/services/announcement_service.py` — 公告业务逻辑
- `cloud-server/app/services/feedback_service.py` — 反馈业务逻辑（含 OSS 上传协调）
- `cloud-server/app/api/announcements.py` — 公开公告 API（无需认证）
- `cloud-server/app/api/feedback.py` — 公开反馈 API（可选认证）
- `cloud-server/app/api/admin_announcements.py` — 管理员公告管理 API
- `cloud-server/app/api/admin_feedback.py` — 管理员反馈管理 API
- `cloud-server/alembic/versions/003_announcements_feedback.py` — 数据库迁移
- `cloud-server/docs/ADMIN_ANNOUNCEMENTS_AND_FEEDBACK.md` — 管理员操作文档
- `cloud-server/tests/test_announcements_api.py` — 公告 API 测试（9 项）
- `cloud-server/tests/test_admin_announcements.py` — 管理员公告测试（8 项）
- `cloud-server/tests/test_feedback_api.py` — 反馈 API 测试（10 项）
- `cloud-server/tests/test_admin_feedback.py` — 管理员反馈测试（7 项）

修改：
- `cloud-server/app/models/user.py` — 新增 `is_admin` 字段
- `cloud-server/app/models/__init__.py` — 导出所有模型
- `cloud-server/app/core/config.py` — 新增公告/反馈/管理员配置项和属性
- `cloud-server/app/api/deps.py` — 新增 `get_optional_current_user` 和 `require_admin_user`
- `cloud-server/app/infrastructure/oss_storage.py` — 新增 `build_feedback_object_key`
- `cloud-server/app/services/rate_limit_service.py` — 新增 `FEEDBACK_CREATE`/`FEEDBACK_UPLOAD_INIT` 限流
- `cloud-server/app/services/account_service.py` — 导出/删除时处理反馈数据隐私
- `cloud-server/app/main.py` — 注册公告、反馈、管理员路由
- `cloud-server/alembic/env.py` — 导入新模型
- `cloud-server/tests/conftest.py` — 导入新模型

### backend（新增 4 个文件，修改 2 个文件）

新增：
- `backend/app/schemas/cloud_feedback.py` — 本地代理 schema
- `backend/app/services/cloud_announcement_service.py` — 公告代理服务
- `backend/app/services/cloud_feedback_service.py` — 反馈代理服务（含文件校验、SHA256、OSS 上传协调）
- `backend/tests/test_cloud_announcements_api.py` — 公告代理测试（3 项）
- `backend/tests/test_cloud_feedback_api.py` — 反馈代理测试（4 项）

修改：
- `backend/app/infrastructure/cloud_api_client.py` — 新增公告/反馈 API 方法
- `backend/app/api/cloud.py` — 新增公告/反馈代理路由（含 multipart form）

### frontend（新增 8 个文件，修改 1 个文件）

新增：
- `frontend/src/entities/announcement/types.ts` — 公告类型定义
- `frontend/src/entities/announcement/api.ts` — 公告 API 客户端
- `frontend/src/entities/feedback/types.ts` — 反馈类型定义
- `frontend/src/entities/feedback/api.ts` — 反馈 API 客户端（apiUpload）
- `frontend/src/features/announcements/GlobalAnnouncementBanner.vue` — 全局公告横幅
- `frontend/src/features/announcements/AnnouncementDetailDialog.vue` — 公告详情弹窗
- `frontend/src/features/feedback/FeedbackDialog.vue` — 反馈提交表单
- `frontend/src/features/feedback/FeedbackEntryButton.vue` — 全局反馈入口按钮

修改：
- `frontend/src/App.vue` — 挂载公告横幅和反馈按钮

## Implementation Notes

1. **公告无需认证**：`GET /api/announcements` 不需要 Bearer token，未登录用户也能看到公告
2. **反馈可选认证**：`POST /api/feedback` 使用 `get_optional_current_user`，已登录用户自动关联 user_id
3. **管理员权限双重校验**：`require_admin_user` 同时检查 `user.is_admin` 和 `ADMIN_EMAILS` 白名单
4. **附件上传流程**：前端 → sidecar → cloud-server（获取 presigned URL）→ OSS（直传）→ cloud-server（确认）
5. **隐私保护**：公告正文拒绝 HTML 标签；presigned URL 不写入日志；账号删除时反馈自动匿名化并删除 OSS 附件
6. **公告关闭状态持久化**：使用 localStorage `zhangshu:dismissed-announcements` 存储已关闭的公告 ID
7. **限流**：反馈提交和附件上传均有独立限流 scope，支持按 user_id 或 IP 限流
8. **前端安全**：公告正文使用纯文本展示（逐行 `<p>` 渲染），不使用 `v-html`

## Deviations from Codex Plan

- `App.vue` 需要添加包裹 `<div class="app-root">` 以支持公告横幅和反馈按钮的 flex 布局，这是必要的结构变更
- 后端 `cloud.py` 新增了 `get_announcement_service` 和 `get_feedback_service` 依赖注入函数（计划中未明确提及，但遵循了已有的依赖注入模式）

## Verification Commands Run

### cloud-server
- `.venv/Scripts/python.exe -m pytest tests/ -q` → ✅ 140 passed（新增 31 项）
- `.venv/Scripts/python.exe -c "from app.main import app; print(app.title)"` → ✅ "Zhangshu Cloud API"

### backend
- `.venv/Scripts/python.exe -m pytest tests/ -q` → ✅ 461 passed（新增 7 项）
- `.venv/Scripts/python.exe -c "from app.main import app; print('ok')"` → ✅ ok

### frontend
- `npm run type-check` → ✅ passed
- `npm run test:unit` → ✅ 115 passed
- `npm run build` → ✅ built in 722ms

## Verification Results

全部通过。

| 模块 | 测试数 | 状态 |
|------|--------|------|
| cloud-server | 140 | ✅ 全部通过 |
| backend | 461 | ✅ 全部通过 |
| frontend type-check | — | ✅ 通过 |
| frontend unit tests | 115 | ✅ 全部通过 |
| frontend build | — | ✅ 通过 |

## Known Issues

- 前端 `npm run build` 有一个 chunk 大小警告（525 KB > 500 KB），建议后续使用动态 import 做代码分割
- 管理员接口仅在 API/Swagger 层暴露，未做普通客户端 UI 入口（这是设计要求）
- 反馈附件上传为一次性读入内存（限制 50 MB 单文件），后续可考虑流式上传
- Alembic 迁移需要在生产环境手动执行 `alembic upgrade head`

## Production Deployment Notes

### 服务器信息
- IP: 121.40.247.143, 域名: api.emailbs.xin
- 部署目录: `/opt/zhangshu-cloud/`
- Docker Compose: postgres + cloud-api

### 部署修复记录
1. **缺失文件**：服务器缺少多个文件（`002_account_privacy.py`、`app/core/audit.py`、`app/core/logging.py`、`app/core/security_headers.py`、`app/repositories/rate_limit_repo.py`），已通过 SFTP 批量同步修复
2. **DATABASE_URL 错误**：本地 `.env` 使用 SQLite，同步到服务器后导致 app 使用 SQLite 而非 PostgreSQL。已修复为 `postgresql+psycopg://zhangshu:zhangshu@postgres:5432/zhangshu_cloud`
3. **PostgreSQL 密码认证**：pg_hba.conf 对非 localhost 连接要求 scram-sha-256，但密码不同步。通过 `ALTER USER zhangshu WITH PASSWORD 'zhangshu'` 修复
4. **管理员账号**：`2553341751@qq.com` / `@Zlc20040613`，已注册并通过 ADMIN_EMAILS 白名单获得管理员权限
5. **测试公告**：已成功发布一条测试公告"测试公告"（正文"测试下公告通知"），通过公开 API 可正常获取

### 操作指南
完整操作指南已写入 `docs/CLOUD_SERVER_OPS_GUIDE.md`，涵盖：
- 服务架构和目录结构
- 常用运维命令（SSH、日志、重启、文件传输）
- 数据库操作（连接、查询、迁移、备份）
- 全部 API 接口总览（含参数和效果说明）
- 环境变量参考
- Nginx 配置
- 故障排查

## Suggested Next Review Points for Codex

1. 公告的 `app_version` 过滤目前仅做字段存储，未实现 semver 比较——是否需要实现？
2. 反馈附件 OSS 生命周期规则是否已在 OSS 控制台配置？
3. 是否需要在前端设置页面中也添加"反馈与帮助"入口（当前仅全局浮动按钮）？
4. `ADMIN_EMAILS` 环境变量是否需要加入 `validate_production_config` 的生产检查？
5. Tauri 打包后文件选择对话框和 multipart 上传行为需要人工验收
6. 服务器 `JWT_SECRET_KEY` 仍为默认值 `change-me-in-production`，生产环境需更换
7. 服务器 `ENVIRONMENT` 仍为 `development`，切换为 `production` 前需先更换 JWT_SECRET_KEY 和配置 CORS
8. 域名 `api.emailbs.xin` 的 ICP 备案可能影响外网访问，需确认
