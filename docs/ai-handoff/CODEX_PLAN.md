# Task Summary

本次任务规划两个相关但边界不同的能力：

1. 章枢云后台管理系统：
   - 面向开发者/管理员，不进入桌面客户端。
   - 可以通过部署在服务器上的章枢云 API 查看生产数据。
   - 首期重点是反馈管理、用户活跃情况、用户列表、公告管理和基础运营概览。

2. 客户端云账户体验升级：
   - 优化登录/注册窗口 UI，解决表单组件左右边距贴边的问题。
   - 新增独立个人页面，用户登录后可查看个人信息、软件版本号、云账户状态。
   - 支持头像、签名、显示名等个人资料。
   - 强化修改登录密码流程，尽力保护用户账号安全。

Codex 未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

- 已按要求归档上一轮“公告通知 + 用户反馈模块”交接文件到：
  - `docs/ai-handoff/archive/2026-05-27-announcements-feedback/CODEX_PLAN.md`
  - `docs/ai-handoff/archive/2026-05-27-announcements-feedback/CLAUDE_EXECUTION_REPORT.md`
- 当前 `docs/ai-handoff/` 根目录无活跃旧计划，可创建新的 `CODEX_PLAN.md`。
- `cloud-server/` 已有公告和反馈基础能力：
  - `cloud-server/app/api/admin_feedback.py`
  - `cloud-server/app/api/admin_announcements.py`
  - `cloud-server/app/api/feedback.py`
  - `cloud-server/app/api/announcements.py`
  - `cloud-server/app/models/feedback_ticket.py`
  - `cloud-server/app/models/feedback_attachment.py`
  - `cloud-server/app/models/announcement.py`
  - `cloud-server/app/services/feedback_service.py`
  - `cloud-server/app/services/announcement_service.py`
- `cloud-server/app/api/deps.py` 已有 `require_admin_user`，基于 `users.is_admin` 或 `ADMIN_EMAILS` 白名单判断管理员权限。
- 当前审计 `cloud-server/app/core/audit.py` 只写结构化日志，没有数据库审计/活跃事件表。要做“用户活跃情况”仪表盘，不能只依赖日志，需要新增持久化 activity/metric 数据或基于现有表计算基础指标。
- 当前云账户资料仅包含：
  - `id`
  - `email`
  - `display_name`
  - `created_at`
- `cloud-server/app/models/user.py` 已有：
  - `is_active`
  - `is_admin`
  - `password_changed_at`
  - 删除/匿名化相关字段
  - 但没有头像、签名、最后活跃时间、最后登录时间、登录次数等字段。
- 当前修改密码已具备基础安全能力：
  - 需要旧密码。
  - 服务端校验密码强度。
  - 修改后撤销所有 refresh token。
  - 本地 sidecar 调用后会清理本地 token，强制重新登录。
- 当前修改密码仍可加强：
  - 没有单独的密码修改限流。
  - UI 侧提示和确认不足。
  - 没有明确阻止新旧密码相同。
  - 账号安全事件没有进入可查询的持久化活动表。
- 当前客户端 UI：
  - `frontend/src/features/cloud/CloudAccountDialog.vue` 是登录/注册弹窗。
  - `.cloud-account-dialog` 只设置了 `max-width`、`display:grid` 和 `gap`，实际内边距依赖全局 `.zs-dialog-content`；用户反馈表单左右贴边，说明需要组件内增加稳定的 body padding 和表单布局。
  - `frontend/src/features/cloud/CloudAccountPrivacyPanel.vue` 已包含显示名、修改密码、退出全部设备、导出数据、删除账号等能力，但它嵌在设置弹窗内，不是独立个人页面。
- 当前前端路由没有个人页面：
  - `frontend/src/router/index.ts` 没有 `/account` 或 `/profile` 路由。
- 当前前端软件版本可从 `frontend/package.json` 得到 `0.0.0`，但运行时页面没有稳定版本展示入口。

# Architecture Decision

## 1. 后台管理系统必须独立于桌面客户端

新增一个独立的管理前端项目：

`cloud-admin/`

原因：

- 后台管理是开发者/管理员使用，不应该打包进 Tauri 桌面客户端。
- 管理后台访问生产数据和反馈附件，风险比普通客户端更高。
- 独立项目便于部署到云服务器同源路径，例如 `https://api.example.com/admin/` 或独立域名 `https://admin.example.com/`。

后台管理前端只通过 `cloud-server` 的 admin API 访问数据，不允许浏览器直连 PostgreSQL，不允许暴露数据库账号、OSS AccessKey 或服务器环境变量。

## 2. 管理端首期不做“万能后台”

首期只做必要运营闭环：

- 管理员登录。
- 仪表盘概览。
- 用户活跃统计。
- 用户列表和用户详情只读查看。
- 反馈列表、反馈详情、附件下载、状态流转。
- 公告管理复用已实现 admin announcement API。

暂不做：

- 直接编辑用户密码。
- 直接删除用户账号。
- 批量封禁。
- 财务/支付。
- 权限组系统。
- 任意 SQL 查询面板。

## 3. 活跃统计使用服务端持久化活动事件

为避免只靠日志分析，新增数据库表：

`user_activity_events`

用来记录低敏、可统计的用户行为：

- 注册。
- 登录成功。
- token refresh。
- 云备份 init/complete/delete。
- 反馈提交。
- 公告读取可选，不建议首期记录每次公告读取，避免噪音。
- 个人资料更新。
- 修改密码。

统计指标由 `AdminMetricsService` 聚合，不在 API router 中拼 SQL。

## 4. 管理端认证要更严格

推荐新增独立 admin auth 接口，使用 HttpOnly Secure Cookie 管理后台会话：

- `POST /api/admin/auth/login`
- `POST /api/admin/auth/refresh`
- `POST /api/admin/auth/logout`
- `GET /api/admin/auth/me`

管理后台部署时应与 cloud-server 同源或同站点，Cookie 设置：

- `HttpOnly`
- `Secure` 在 production 必须为 true
- `SameSite=Lax`
- 管理端 access token 有效期建议 30 分钟
- 管理端 refresh token 有效期建议 8 小时或 24 小时，不沿用普通用户 30 天

为兼容测试，可让 admin 依赖同时支持 Bearer token，但后台 Web UI 优先使用 Cookie。

## 5. 客户端个人页面仍走本地 sidecar

桌面客户端不直接调用 cloud-server。

客户端个人页面应走：

`frontend -> backend local sidecar -> cloud-server`

这样可以继续复用本地加密 token、网络模式、代理/兼容模式、错误提示和 HTTPS 策略。

## 6. 头像上传继续使用 presigned URL

头像属于云账户资料，不存入本地业务数据库。

流程：

1. 前端在个人页面选择头像图片。
2. 本地 sidecar 校验类型和大小。
3. 本地 sidecar 调用 cloud-server 初始化头像上传，拿到 presigned PUT URL。
4. 本地 sidecar 上传头像到 OSS。
5. 本地 sidecar 调用 complete。
6. cloud-server 保存 `avatar_object_key` 并返回短期 `avatar_url`。

限制：

- 只允许 `image/png`、`image/jpeg`、`image/webp`。
- 单文件建议 2 MB。
- 不引入图片裁剪依赖，首期只在前端用 CSS 圆形裁切预览。

## 7. 修改密码作为高风险流程单独加固

必须保留：

- 当前密码。
- 新密码。
- 确认新密码。
- 服务端密码强度校验。
- 修改成功后撤销所有 refresh token。
- 本地 sidecar 清理 token 并强制重新登录。

必须新增：

- 服务端密码修改限流。
- 新密码不得与旧密码相同。
- UI 明确提示“修改后所有设备需要重新登录”。
- 二次确认或至少明确确认按钮文案。
- 错误提示不得泄露账号状态细节。
- 审计和活动事件记录，但不得记录密码。

# Files to Create or Modify

## cloud-server

新增：

- `cloud-server/app/models/user_activity_event.py`
- `cloud-server/app/repositories/user_activity_repo.py`
- `cloud-server/app/services/activity_service.py`
- `cloud-server/app/services/admin_metrics_service.py`
- `cloud-server/app/services/admin_user_service.py`
- `cloud-server/app/api/admin_auth.py`
- `cloud-server/app/api/admin_dashboard.py`
- `cloud-server/app/api/admin_users.py`
- `cloud-server/app/schemas/admin_auth.py`
- `cloud-server/app/schemas/admin_dashboard.py`
- `cloud-server/app/schemas/admin_user.py`
- `cloud-server/alembic/versions/004_admin_dashboard_profile.py`
- `cloud-server/tests/test_admin_auth.py`
- `cloud-server/tests/test_admin_dashboard.py`
- `cloud-server/tests/test_admin_users.py`
- `cloud-server/tests/test_profile_avatar_signature.py`
- `cloud-server/tests/test_password_change_security.py`

修改：

- `cloud-server/app/main.py`
  - 注册 admin auth/dashboard/users routers。
- `cloud-server/app/api/deps.py`
  - 增加 admin cookie 读取依赖，保留 Bearer 测试路径。
- `cloud-server/app/core/config.py`
  - 新增 admin cookie、admin token、头像上传限制、管理后台 CORS/部署配置。
- `cloud-server/app/models/user.py`
  - 新增头像、签名、活跃统计字段。
- `cloud-server/app/models/__init__.py`
  - 导出新模型。
- `cloud-server/app/schemas/account.py`
  - 扩展 profile schema。
- `cloud-server/app/api/account.py`
  - 增加签名/头像相关接口，强化修改密码限流。
- `cloud-server/app/services/account_service.py`
  - 扩展资料更新、头像上传、密码修改安全逻辑。
- `cloud-server/app/services/auth_service.py`
  - 登录成功时更新 `last_login_at`、`last_seen_at`、`login_count`，记录 activity event。
- `cloud-server/app/services/rate_limit_service.py`
  - 新增 `password_change`、`admin_login` 限流类型。
- `cloud-server/app/infrastructure/oss_storage.py`
  - 新增 avatar object key builder。

## cloud-admin

新增独立管理前端项目：

- `cloud-admin/package.json`
- `cloud-admin/package-lock.json`
- `cloud-admin/index.html`
- `cloud-admin/vite.config.ts`
- `cloud-admin/tsconfig.json`
- `cloud-admin/tsconfig.app.json`
- `cloud-admin/env.d.ts`
- `cloud-admin/src/main.ts`
- `cloud-admin/src/App.vue`
- `cloud-admin/src/router/index.ts`
- `cloud-admin/src/shared/api/client.ts`
- `cloud-admin/src/shared/styles/base.css`
- `cloud-admin/src/entities/admin-auth/api.ts`
- `cloud-admin/src/entities/admin-auth/types.ts`
- `cloud-admin/src/entities/admin-dashboard/api.ts`
- `cloud-admin/src/entities/admin-dashboard/types.ts`
- `cloud-admin/src/entities/admin-feedback/api.ts`
- `cloud-admin/src/entities/admin-feedback/types.ts`
- `cloud-admin/src/entities/admin-user/api.ts`
- `cloud-admin/src/entities/admin-user/types.ts`
- `cloud-admin/src/entities/admin-announcement/api.ts`
- `cloud-admin/src/entities/admin-announcement/types.ts`
- `cloud-admin/src/pages/LoginPage.vue`
- `cloud-admin/src/pages/DashboardPage.vue`
- `cloud-admin/src/pages/FeedbackListPage.vue`
- `cloud-admin/src/pages/FeedbackDetailPage.vue`
- `cloud-admin/src/pages/UsersPage.vue`
- `cloud-admin/src/pages/UserDetailPage.vue`
- `cloud-admin/src/pages/AnnouncementsPage.vue`
- `cloud-admin/src/components/AdminLayout.vue`
- `cloud-admin/src/components/StatTile.vue`
- `cloud-admin/src/components/DataTable.vue`

约束：

- 使用 Vue 3 + TypeScript + Vite。
- 不引入大型 UI 库。
- 不接入 Tauri。
- 页面风格应是后台工具，不做营销式首页。

## backend local sidecar

新增：

- `backend/app/schemas/cloud_profile.py`
- `backend/app/services/cloud_profile_service.py`
- `backend/tests/test_cloud_profile_api.py`

修改：

- `backend/app/infrastructure/cloud_api_client.py`
  - 新增 profile/avatar/signature/password 相关 API 方法。
- `backend/app/api/cloud.py`
  - 新增本地代理接口。
- `backend/app/services/cloud_auth_service.py`
  - 扩展 profile 方法，保持修改密码后本地 token 清理。
- `backend/app/schemas/cloud.py`
  - 或新增独立 schema 后只在 API 层引用，避免 cloud.py 继续膨胀。

## frontend desktop client

新增：

- `frontend/src/pages/account/CloudProfilePage.vue`
- `frontend/src/features/cloud/CloudProfileCard.vue`
- `frontend/src/features/cloud/CloudAvatarUploader.vue`
- `frontend/src/features/cloud/CloudSignatureEditor.vue`
- `frontend/src/features/cloud/CloudPasswordChangePanel.vue`
- `frontend/src/features/cloud/AppVersionPanel.vue`

修改：

- `frontend/src/features/cloud/CloudAccountDialog.vue`
  - 优化登录/注册 UI 布局和左右内边距。
- `frontend/src/features/cloud/CloudAccountPrivacyPanel.vue`
  - 可拆分复用密码修改、会话、导出、删除等能力，避免重复逻辑。
- `frontend/src/entities/cloud/api.ts`
  - 新增 profile/avatar/signature API。
- `frontend/src/entities/cloud/types.ts`
  - 扩展 `CloudAccountProfile`、`CloudAccountStatus`。
- `frontend/src/router/index.ts`
  - 新增 `/account` 路由。
- `frontend/src/pages/projects/ProjectsPage.vue`
  - 在云账户入口旁增加“个人中心”入口，或登录后点击云账户进入个人页面。
- `frontend/vite.config.ts`
  - 注入软件版本号常量。
- `frontend/env.d.ts`
  - 声明版本常量类型。

## docs

新增：

- `cloud-server/docs/CLOUD_ADMIN_DEPLOYMENT.md`
- `docs/Cloud_Client_Profile_And_Admin_Plan.md`（可选，如果 Claude 认为需要沉淀说明）

# Implementation Steps for Claude Code

## Phase 1: cloud-server 账号资料字段和迁移

1. 修改 `cloud-server/app/models/user.py`，新增字段：
   - `avatar_object_key: String(512), nullable=True`
   - `avatar_content_type: String(80), nullable=True`
   - `avatar_updated_at: DateTime(timezone=True), nullable=True`
   - `signature: String(160), nullable=True`
   - `last_login_at: DateTime(timezone=True), nullable=True`
   - `last_seen_at: DateTime(timezone=True), nullable=True`
   - `login_count: Integer, nullable=False, default=0, server_default="0"`

2. 新增 `cloud-server/app/models/user_activity_event.py`：
   - `id: String(36), primary_key`
   - `user_id: String(36), nullable=True, index=True`
   - `event_type: String(64), nullable=False, index=True`
   - `client_ip_hash: String(64), nullable=True`
   - `user_agent: String(255), nullable=True`
   - `metadata_json: Text, nullable=True`
   - `created_at: DateTime(timezone=True), default=utc_now, index=True`

3. 新增 Alembic：
   - `cloud-server/alembic/versions/004_admin_dashboard_profile.py`
   - 注意兼容 SQLite 和 PostgreSQL。
   - 对已有 users 表使用 `op.add_column`。
   - 新建 `user_activity_events` 表和必要索引。

4. 更新 `cloud-server/app/models/__init__.py` 导出新模型。

## Phase 2: cloud-server 活跃事件和指标服务

1. 新增 `cloud-server/app/repositories/user_activity_repo.py`：
   - `create(event)`
   - `count_distinct_users_since(since)`
   - `count_events_by_day(event_type, since, days)`
   - `list_recent_by_user(user_id, limit)`

2. 新增 `cloud-server/app/services/activity_service.py`：
   - `record(user_id, event_type, request, metadata=None)`
   - 对 IP 做 SHA-256 hash，不保存明文 IP。
   - `metadata` 只允许白名单字段，例如 `status_code`、`category`、`size_bytes`。
   - 不记录 token、密码、presigned URL、反馈正文。

3. 在以下位置调用活动记录：
   - `cloud-server/app/api/auth.py`
     - 注册成功：`user_registered`
     - 登录成功：`login_success`
     - refresh 成功：`token_refreshed`
   - `cloud-server/app/services/auth_service.py`
     - 登录成功后更新 `last_login_at`、`last_seen_at`、`login_count`。
   - `cloud-server/app/api/feedback.py`
     - 反馈创建成功：`feedback_created`
   - `cloud-server/app/api/backups.py`
     - backup init/complete/delete。
   - `cloud-server/app/api/account.py`
     - profile update、password_changed。

4. 新增 `cloud-server/app/services/admin_metrics_service.py`：
   - `get_summary()`
     - 总用户数。
     - 近 24 小时活跃用户。
     - 近 7 日活跃用户。
     - 近 30 日活跃用户。
     - 今日注册数。
     - 总云项目数。
     - 总云备份数。
     - 总存储用量。
     - open feedback 数。
     - urgent/high feedback 数。
   - `get_activity_series(days=14)`
     - 每日活跃用户。
     - 每日注册。
     - 每日反馈。
     - 每日备份成功数。
   - `get_feedback_stats()`
     - 按状态计数。
     - 按分类计数。

5. 新增 `cloud-server/app/api/admin_dashboard.py`：
   - prefix: `/api/admin/dashboard`
   - `GET /summary`
   - `GET /activity?days=14`
   - `GET /feedback-stats`
   - 全部依赖管理员权限。

## Phase 3: cloud-server 管理端认证

1. 新增 `cloud-server/app/schemas/admin_auth.py`：
   - `AdminLoginRequest`
   - `AdminMeResponse`

2. 新增 `cloud-server/app/api/admin_auth.py`：
   - `POST /api/admin/auth/login`
     - request: `{ "email": str, "password": str }`
     - 验证账号密码。
     - 必须是 `is_admin` 或 `ADMIN_EMAILS`。
     - 设置 HttpOnly Cookie。
     - 返回 `{ "id", "email", "display_name" }`，不返回 token 给前端。
   - `POST /api/admin/auth/refresh`
     - 轮换 refresh cookie。
   - `POST /api/admin/auth/logout`
     - 撤销当前 refresh token 并清理 cookie。
   - `GET /api/admin/auth/me`
     - 返回当前管理员信息。

3. 修改 `cloud-server/app/api/deps.py`：
   - 新增 `get_current_user_from_admin_cookie`。
   - 新增 `require_admin_user_cookie_or_bearer`。
   - 现有 admin API 可逐步切换到新依赖。
   - 测试中允许 Bearer，以便复用现有测试工具。

4. 修改 `cloud-server/app/core/config.py`：
   - `admin_cookie_secure: bool = True`
   - `admin_access_token_expire_minutes: int = 30`
   - `admin_refresh_token_expire_hours: int = 8`
   - `admin_cookie_samesite: str = "lax"`
   - production 下如果 `admin_cookie_secure=False` 应由 `validate_production_config` 报错。

5. 管理登录限流：
   - 在 `RateLimitService` 中新增 `admin_login`。
   - 按 IP + email 限流。
   - 失败返回 429，不暴露账号是否存在。

## Phase 4: cloud-server 管理用户 API

1. 新增 `cloud-server/app/schemas/admin_user.py`：
   - `AdminUserListItem`
   - `AdminUserDetail`
   - `AdminUserListResponse`

2. 新增 `cloud-server/app/services/admin_user_service.py`：
   - `list_users(keyword, status, limit, offset)`
   - `get_user_detail(user_id)`
   - 详情包含：
     - id、email、display_name、signature。
     - is_active、is_admin。
     - created_at、last_login_at、last_seen_at、login_count。
     - 云项目数、云备份数、存储用量。
     - 反馈数和最近反馈。
     - 最近活动事件。
   - 不返回 password_hash、refresh token、OSS object key 的完整敏感路径。

3. 新增 `cloud-server/app/api/admin_users.py`：
   - `GET /api/admin/users?keyword=&status=&limit=&offset=`
   - `GET /api/admin/users/{user_id}`
   - 第一版保持只读，不做禁用/删除用户操作。

## Phase 5: cloud-server 个人资料、头像、签名和密码安全

1. 修改 `cloud-server/app/schemas/account.py`：
   - `ProfileResponse` 增加：
     - `signature: str | None`
     - `avatar_url: str | None`
     - `avatar_updated_at: datetime | None`
     - `password_changed_at: datetime | None`
   - `UpdateProfileRequest` 增加：
     - `display_name: str | None`
     - `signature: str | None`
   - 新增：
     - `AvatarInitRequest`
     - `AvatarInitResponse`
     - `AvatarCompleteRequest`
     - `AvatarResponse`

2. 修改 `cloud-server/app/services/account_service.py`：
   - `update_profile` 支持显示名和签名。
   - 显示名限制 1-128 字。
   - 签名限制 0-160 字。
   - `get_profile` 返回短期 avatar_url。
   - 新增：
     - `init_avatar_upload(user_id, filename, content_type, size_bytes)`
     - `complete_avatar_upload(user_id, upload_id)`
     - `delete_avatar(user_id)`
   - 头像限制：
     - MIME: `image/png`、`image/jpeg`、`image/webp`
     - max size: 2 MB
   - 上传完成后删除旧 avatar object，失败时不破坏旧头像。

3. 修改 `cloud-server/app/infrastructure/oss_storage.py`：
   - 新增 `build_avatar_object_key(user_id, avatar_id, filename)`：
     - `avatars/{user_id}/{avatar_id}/{safe_filename}`
   - 复用 PUT/GET signed URL。

4. 强化修改密码：
   - `cloud-server/app/services/account_service.py`
     - 校验新旧密码不能相同。
     - 保留现有强度校验。
     - 修改成功后撤销全部 refresh token。
     - 更新 `password_changed_at`。
   - `cloud-server/app/api/account.py`
     - 在 change password 前调用 `RateLimitService.check_password_change`。
     - 审计 `password_change_failed`、`password_changed`。
   - 错误消息不要泄露过多安全细节。

## Phase 6: cloud-admin 前端项目

1. 创建 `cloud-admin/`：
   - 使用 Vue 3 + TypeScript + Vite。
   - 复用项目偏好的朴素 CSS 和设计变量，不引入大型 UI 库。
   - 配置：
     - `VITE_CLOUD_ADMIN_API_BASE_URL`
     - 默认同源为空字符串。

2. `cloud-admin/src/shared/api/client.ts`：
   - `fetch` 默认 `credentials: "include"`，用于 HttpOnly Cookie。
   - 统一解析 `{"detail": "..."}`
   - 401 自动跳转登录页。
   - 不把错误堆栈显示给用户。

3. 页面结构：
   - `LoginPage.vue`
     - 管理员登录。
     - 明确“仅管理员使用”。
   - `DashboardPage.vue`
     - StatTile:
       - 总用户数。
       - 今日新增。
       - 24h 活跃。
       - 7d 活跃。
       - open feedback。
       - 总存储。
     - 简单活动趋势表或轻量条形图，不引入图表库也可。
   - `FeedbackListPage.vue`
     - 筛选：状态、分类、优先级。
     - 搜索：标题、邮箱、用户 ID。
     - 列表字段：标题、分类、状态、优先级、附件数、创建时间。
   - `FeedbackDetailPage.vue`
     - 查看正文、诊断信息、附件列表。
     - 更新状态、优先级、管理员备注。
     - 获取附件下载 URL 后打开，不直接暴露永久链接。
   - `UsersPage.vue`
     - 用户列表、搜索邮箱/显示名。
     - 显示注册时间、最后登录、最后活跃、项目数、备份数、反馈数。
   - `UserDetailPage.vue`
     - 查看用户资料、云用量、最近活动、最近反馈。
     - 第一版只读。
   - `AnnouncementsPage.vue`
     - 复用现有 admin announcement API。
     - 创建草稿、发布、归档、删除。

4. `AdminLayout.vue`：
   - 左侧导航：概览、反馈、用户、公告。
   - 顶部显示当前管理员和退出。
   - 不做大面积宣传式 hero，保持后台工具密度。

5. 安全 UI：
   - 登录页不记住密码。
   - 退出时调用 `/api/admin/auth/logout`。
   - 所有正文按纯文本展示，不使用 `v-html`。
   - 附件下载按钮显示风险提示：不要打开可疑视频或图片中的外链内容。

## Phase 7: backend sidecar 个人资料代理

1. 修改 `backend/app/infrastructure/cloud_api_client.py`：
   - 新增：
     - `get_account_profile()`
     - `update_account_profile(display_name=None, signature=None)`
     - `init_avatar_upload(filename, content_type, size_bytes)`
     - `upload_avatar(upload_url, content, content_type)`
     - `complete_avatar_upload(upload_id, checksum_sha256)`
     - `delete_avatar()`
     - `change_password(old_password, new_password)`
   - 如果已有同名方法，扩展参数和响应结构即可。

2. 新增 `backend/app/services/cloud_profile_service.py`：
   - 获取 profile。
   - 更新 display_name/signature。
   - 接收头像 UploadFile，校验类型和大小，计算 SHA256，调用云端上传。
   - 修改密码后调用 `CloudAuthService.logout()` 清理本地 token。

3. 修改 `backend/app/api/cloud.py`：
   - 新增或扩展：
     - `GET /api/cloud/account/profile`
     - `PATCH /api/cloud/account/profile`
     - `POST /api/cloud/account/avatar`
     - `DELETE /api/cloud/account/avatar`
     - `POST /api/cloud/account/password/change`
   - 头像上传使用 multipart form。
   - 错误返回保持 `{"detail": "错误信息"}`。

4. 测试：
   - profile 获取。
   - 签名更新。
   - 头像非法类型拒绝。
   - 头像超大小拒绝。
   - 修改密码成功后本地 token 被清理。
   - 修改密码失败不清理本地 token。

## Phase 8: frontend 登录/注册弹窗 UI 优化

1. 修改 `frontend/src/features/cloud/CloudAccountDialog.vue`：
   - 保留现有登录/注册逻辑。
   - 增加稳定结构：
     - `.dialog-header`
     - `.dialog-body`
     - `.dialog-footer` 如需要
   - `.cloud-account-dialog` 设置：
     - `width: min(460px, calc(100vw - 32px))`
     - `box-sizing: border-box`
     - 不让表单直接贴容器边。
   - `.dialog-body` 设置：
     - `padding: var(--zs-space-4) var(--zs-space-5)`
     - mobile 降低为 `var(--zs-space-4)`
   - `form`、`.auth-section`、`.not-configured`、`.logged-in-section` 不应左右贴边。
   - 输入框和按钮宽度保持一致。
   - 登录/注册切换 tab 高度稳定，不随文本变化跳动。
   - 错误提示和诊断区域也放在 body 内部，不贴边。

2. UI 文案：
   - 登录失败显示通用错误。
   - 网络失败显示“运行连接诊断”。
   - 注册时提示密码规则：至少 10 个字符，避免过长。

3. 不要在这一步重写整个登录流程，不要把个人中心塞进登录弹窗。

## Phase 9: frontend 独立个人页面

1. 新增 `frontend/src/pages/account/CloudProfilePage.vue`：
   - 路由：`/account`
   - 未登录：
     - 显示云账户登录入口。
     - 不阻止用户返回项目列表。
   - 已登录：
     - 头像。
     - 显示名。
     - 邮箱。
     - 签名。
     - 账号创建时间。
     - 最近密码修改时间。
     - 云存储用量。
     - 软件版本号。
     - 修改密码入口。
     - 退出登录。
     - 可链接到账户隐私/删除账号区域。

2. 新增 `CloudAvatarUploader.vue`：
   - 本地预览。
   - 支持 png/jpg/webp。
   - 超过 2 MB 前端直接提示。
   - 上传成功后刷新 profile。

3. 新增 `CloudSignatureEditor.vue`：
   - 160 字以内。
   - 显示剩余字数。
   - 保存后刷新 profile。

4. 新增 `CloudPasswordChangePanel.vue`：
   - 当前密码。
   - 新密码。
   - 确认新密码。
   - 密码规则提示。
   - 新旧密码不能相同。
   - 提交前提示“修改后所有设备将需要重新登录”。
   - 成功后清理本地登录状态并跳转登录。

5. 新增 `AppVersionPanel.vue`：
   - 显示 `frontend/package.json` 注入的版本。
   - 如 Tauri 环境后续可读取 Tauri 版本，首期不新增 Tauri API 依赖。

6. 修改 `frontend/vite.config.ts`：
   - 读取 `package.json` version。
   - define:
     - `__ZHANGSHU_APP_VERSION__`

7. 修改 `frontend/env.d.ts`：
   - 声明 `const __ZHANGSHU_APP_VERSION__: string`

8. 修改 `frontend/src/router/index.ts`：
   - 新增：
     - `path: "/account"`
     - `name: "cloud-account-profile"`
     - `component: CloudProfilePage`

9. 修改 `frontend/src/pages/projects/ProjectsPage.vue`：
   - 登录后云账户入口可跳转 `/account`。
   - 未登录仍打开登录/注册弹窗。
   - 不要破坏项目列表布局。

## Phase 10: 文档和部署

1. 新增 `cloud-server/docs/CLOUD_ADMIN_DEPLOYMENT.md`：
   - 如何设置管理员账号：
     - `ADMIN_EMAILS=admin@example.com`
     - 或数据库中 `users.is_admin=true`
   - 如何构建 `cloud-admin`。
   - 如何通过 Nginx 部署到 `/admin/`。
   - Cookie、HTTPS、CORS 要求。
   - 不要在文档中写真实 token、密钥、数据库密码。

2. 更新 `cloud-server/README.md` 或只新增文档引用：
   - 指向后台部署文档。

# Constraints

- 本任务不得把后台管理能力打包进 Tauri 客户端。
- 管理后台不得直接连接数据库；必须通过 cloud-server admin API 访问数据。
- 管理后台不得暴露 OSS AccessKey、JWT_SECRET_KEY、数据库 URL、`.env`。
- 用户列表和详情首期只读，不做删除用户、重置密码、封禁等高风险操作。
- 管理端附件下载只能获取短期 presigned URL，不保存永久外链。
- 管理端所有富文本/反馈正文/公告正文按纯文本展示，不使用不安全 `v-html`。
- 活跃统计只记录低敏事件，不保存明文 IP，不保存 token、密码、presigned URL、反馈全文到活动表。
- 客户端个人页面仍通过本地 sidecar 访问云服务，不直接绕过 sidecar。
- 修改密码必须保留当前密码校验，成功后撤销所有 refresh token 并清理本地登录状态。
- 头像只允许图片，签名只允许短文本。
- 不引入大型 UI 库或复杂图表库；后台图表首期可用 CSS/表格实现。
- 不做任务范围外的支付、权限组、客服 IM、邮件通知、任意 SQL 控制台。

# Verification Commands

## cloud-server

```powershell
cd F:\zhangshu\cloud-server
.\.venv\Scripts\python.exe -m pytest tests/test_admin_auth.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_admin_dashboard.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_admin_users.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_profile_avatar_signature.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_password_change_security.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -c "from app.main import app; print(app.title)"
```

如 Alembic 可用：

```powershell
cd F:\zhangshu\cloud-server
.\.venv\Scripts\alembic.exe upgrade head
```

## cloud-admin

```powershell
cd F:\zhangshu\cloud-admin
npm install
npm run type-check
npm run build
```

如果 Claude Code 新增了 unit tests：

```powershell
cd F:\zhangshu\cloud-admin
npm run test:unit
```

## backend

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\python.exe -m pytest tests/test_cloud_profile_api.py -q
.\.venv\Scripts\python.exe -m pytest tests/ -q
.\.venv\Scripts\python.exe -c "from app.main import app; print('ok')"
```

## frontend

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit
npm run build
```

## manual smoke test

- 使用管理员账号登录 `cloud-admin`。
- 打开后台概览，确认用户数、活跃数、反馈数可显示。
- 查看反馈列表，打开反馈详情，更新状态。
- 对带附件反馈生成下载链接，确认链接短期可用。
- 查看用户列表和用户详情，确认不显示 password_hash、token、OSS Key。
- 客户端打开云账户登录/注册弹窗，确认左右边距正常。
- 客户端登录后进入 `/account`，确认头像、签名、版本号显示。
- 修改密码成功后，确认本地退出登录，旧 refresh token 不可用。

# Acceptance Criteria

- 后台管理：
  - 有独立 `cloud-admin/` 前端项目。
  - 管理员可以安全登录和退出。
  - 非管理员不能访问后台 API。
  - 后台可查看运营概览、用户活跃、用户列表、用户详情。
  - 后台可查看用户反馈、反馈详情、附件下载、状态更新。
  - 后台可管理公告。
  - 管理后台不直接连接数据库。
- 用户活跃：
  - 服务端有可持久化的低敏 activity event。
  - 可统计 24h、7d、30d 活跃用户。
  - 可展示注册、反馈、备份等趋势。
- 客户端云账户：
  - 登录/注册弹窗左右边距正常，输入框不贴容器边。
  - 登录/注册弹窗在窄屏下仍可用。
  - 登录后可进入独立个人页面。
  - 个人页面显示头像、邮箱、显示名、签名、软件版本号。
  - 用户可更新头像、显示名、签名。
  - 用户可修改登录密码。
- 密码安全：
  - 修改密码必须输入当前密码。
  - 新密码符合强度规则。
  - 新旧密码不能相同。
  - 修改密码有服务端限流。
  - 修改成功后所有 refresh token 被撤销，本地 token 被清理。
  - 日志、审计、活动事件不包含密码。
- 隐私和安全：
  - 不提交 `.env`、数据库、日志、真实 token、OSS Key。
  - 后台 API 不返回 password_hash、refresh token、presigned URL 长期链接。
  - 头像上传限制大小和 MIME 类型。

# Risks and Watchpoints

- 后台管理系统一旦部署到公网，安全风险高于普通客户端，必须强制 HTTPS 和管理员权限。
- 如果管理后台使用 localStorage 保存 token，XSS 风险更高；优先使用 HttpOnly Cookie。
- 活跃统计不要过度采集隐私，尤其不要保存明文 IP 和完整 user-agent 指纹。
- 反馈附件可能包含用户作品内容，后台展示和下载都要保持短期授权。
- 头像上传如果不限制类型和大小，会造成 OSS 成本和安全风险。
- 修改密码失败提示如果过细，可能帮助攻击者判断账号状态。
- 修改密码成功后会让所有设备退出，UI 必须明确告知用户。
- 新增 `cloud-admin/` 会带来一套独立构建流程，部署文档必须写清楚。
- 不要为了后台图表引入大型依赖；首期用表格和轻量 CSS 足够。
- 如果已有公告/反馈 API 和新计划冲突，Claude Code 应停止反馈，不要强行重写。

# Review Checklist

- [ ] 是否已归档上一轮交接文件？
- [ ] 是否只在计划中要求新增实现，Codex 未改业务代码？
- [ ] `cloud-admin/` 是否独立于桌面客户端？
- [ ] 管理后台是否只通过 admin API 访问数据？
- [ ] 管理员认证是否有权限校验、限流和安全 Cookie？
- [ ] 非管理员访问 admin API 是否返回 403？
- [ ] 用户活跃统计是否来自低敏持久化事件？
- [ ] 活动事件是否不保存明文 IP、token、密码、presigned URL？
- [ ] 用户列表/详情是否不返回 password_hash 和 refresh token？
- [ ] 反馈附件下载是否使用短期 presigned URL？
- [ ] 登录/注册弹窗是否修复左右贴边问题？
- [ ] 个人页面是否独立路由，而不是继续塞进设置弹窗？
- [ ] 头像上传是否限制类型和大小？
- [ ] 签名长度是否有限制？
- [ ] 修改密码是否要求当前密码、新密码确认、服务端强度校验？
- [ ] 修改密码是否有服务端限流？
- [ ] 修改密码成功后是否撤销 refresh token 并清理本地 token？
- [ ] 是否补充 cloud-server、backend、frontend、cloud-admin 测试？
- [ ] 是否运行计划中的验证命令？
