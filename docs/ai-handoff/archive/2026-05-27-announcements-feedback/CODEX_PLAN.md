# Task Summary

本次任务是规划“章枢公告通知 + 用户反馈模块”。

目标：

1. 作为软件开发者，可以向所有章枢客户端发布公告通知。
2. 用户可以在章枢客户端提交反馈，反馈内容支持文本、图片和视频。
3. 不强制用户登录：公告应面向所有配置了章枢云服务的客户端；反馈应支持匿名提交，也应在已登录云账户时自动关联用户。
4. 桌面端仍然不得持有 OSS AccessKey。反馈附件应沿用服务端签名 URL 模式上传到 OSS。

Codex 未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

- 当前 `docs/ai-handoff/` 根目录没有活跃的 `CODEX_PLAN.md`、`CLAUDE_EXECUTION_REPORT.md`、`CODEX_REVIEW.md`，本次可直接创建新计划。
- 当前项目结构：
  - `frontend/`：Vue 3 + TypeScript + Vite + Tauri v2 前端。
  - `backend/`：本地 FastAPI sidecar，负责本地数据、云账户本地代理、云备份代理。
  - `cloud-server/`：独立章枢云 API 服务端，FastAPI + SQLAlchemy + Alembic + PostgreSQL/SQLite + OSS。
- 现有云服务能力：
  - `cloud-server/app/main.py` 已注册 `auth_router`、`projects_router`、`backups_router`、`account_router`。
  - `cloud-server/app/api/auth.py` 提供注册、登录、刷新 token、me。
  - `cloud-server/app/api/account.py` 提供账号资料、修改密码、会话、使用量、导出、删除账号。
  - `cloud-server/app/infrastructure/oss_storage.py` 已封装 OSS presigned PUT/GET、head、delete。
  - `cloud-server/app/services/rate_limit_service.py` 已有数据库级限流基础，可扩展反馈提交限流。
- 现有本地 sidecar 云代理：
  - `backend/app/api/cloud.py` 已代理云账户、网络诊断、云备份、账户隐私接口。
  - `backend/app/infrastructure/cloud_api_client.py` 已处理云 API 请求、JWT、网络模式、HTTPS 策略和 OSS presigned 上传。
  - `backend/app/services/cloud_auth_service.py` 负责本地加密保存云 token。
- 现有前端云入口：
  - `frontend/src/entities/cloud/api.ts` 和 `frontend/src/entities/cloud/types.ts` 是云相关 API/types 入口。
  - `frontend/src/features/cloud/` 下已有云账户、云备份、网络诊断、使用量、隐私面板。
  - `frontend/src/App.vue` 当前只挂载 `ThemeSwitcher` 与 `RouterView`，适合作为全局公告横幅的轻量挂载点，但只能做小范围改动。
  - `frontend/src/shared/api/client.ts` 已有 `apiUpload`，可用于反馈表单上传到本地 sidecar。
- 当前没有公告、站内通知、用户反馈、admin 发布接口或反馈附件模型。

# Architecture Decision

## 1. 功能边界

公告通知和用户反馈属于“章枢云服务 + 桌面端可选云能力”，不是本地写作核心业务。

实现应拆为三层：

- `cloud-server/`：权威数据源，存储公告、反馈工单、反馈附件元数据，生成附件上传/下载签名 URL，提供管理员接口。
- `backend/`：本地 sidecar 代理云 API，保存本地公告已读/关闭状态，代替前端上传附件到 OSS，避免前端直接处理 OSS 复杂错误。
- `frontend/`：展示公告、反馈表单、附件选择、提交进度和错误提示。

不得把公告/反馈的业务规则直接写进 Vue 组件，也不得把 OSS 上传逻辑写进 UI 组件。

## 2. 公告通知设计

公告分为两类展示：

- 轻提示公告：顶部横幅或全局通知条，适合版本提醒、维护通知、活动通知。
- 重要公告：可弹出详情，但不得频繁打断用户写作。用户关闭后，本机应记住已关闭状态。

公告读取不要求登录：

- 未登录用户也能看到开发者发布给所有用户的公告。
- 客户端离线或云服务不可达时，公告模块静默失败，不影响本地写作。

管理员发布不在普通桌面端暴露：

- 管理员接口放在 `cloud-server/app/api/admin_announcements.py`。
- 需要管理员身份校验。
- 建议先用现有 JWT 用户体系扩展 `users.is_admin`，并增加 `ADMIN_EMAILS` 环境变量作为管理白名单补充。
- 不建议在普通客户端内做“开发者发布公告 UI”，避免误暴露管理能力。

## 3. 用户反馈设计

反馈支持：

- 文本文字：标题、分类、详细描述。
- 图片：png、jpg/jpeg、webp、gif。
- 视频：mp4、webm、mov。
- 可选联系方式：邮箱。
- 可选诊断信息：应用版本、平台、网络模式、云服务配置状态等。默认不上传日志、不上传正文内容。

反馈不强制登录：

- 已登录：云服务端记录 `user_id`。
- 未登录：云服务端记录 `contact_email`（可选）和基础客户端信息。

附件上传流程：

1. 前端把表单和文件提交给本地 sidecar。
2. 本地 sidecar 校验文件数量、大小、MIME 类型。
3. 本地 sidecar 调用 cloud-server 创建反馈记录并获取每个附件的 presigned PUT URL。
4. 本地 sidecar 使用 `CloudApiClient` 上传附件到 OSS。
5. 本地 sidecar 调用 cloud-server complete 接口，确认附件状态。
6. 前端收到反馈编号，提示用户提交成功。

这样桌面端依然只持有 JWT token，不持有 OSS AccessKey。

## 4. 隐私与滥用防护

- 用户提交前必须看到提示：图片/视频可能包含作品内容或个人信息，请确认后提交。
- 不自动上传本地日志、数据库、正文、项目文件。
- 反馈附件必须限制数量、大小、MIME 类型和扩展名。
- 反馈创建和附件上传必须限流。
- 管理端下载附件必须通过短期 presigned GET URL。
- 账号导出/删除应覆盖已登录用户提交的反馈数据。

# Files to Create or Modify

## cloud-server

新增：

- `cloud-server/app/models/announcement.py`
- `cloud-server/app/models/feedback_ticket.py`
- `cloud-server/app/models/feedback_attachment.py`
- `cloud-server/app/repositories/announcement_repo.py`
- `cloud-server/app/repositories/feedback_repo.py`
- `cloud-server/app/schemas/announcement.py`
- `cloud-server/app/schemas/feedback.py`
- `cloud-server/app/services/announcement_service.py`
- `cloud-server/app/services/feedback_service.py`
- `cloud-server/app/api/announcements.py`
- `cloud-server/app/api/feedback.py`
- `cloud-server/app/api/admin_announcements.py`
- `cloud-server/app/api/admin_feedback.py`
- `cloud-server/alembic/versions/003_announcements_feedback.py`
- `cloud-server/tests/test_announcements_api.py`
- `cloud-server/tests/test_feedback_api.py`
- `cloud-server/tests/test_admin_announcements.py`
- `cloud-server/tests/test_admin_feedback.py`

修改：

- `cloud-server/app/main.py`：注册公告、反馈、管理员路由。
- `cloud-server/app/core/config.py`：新增公告/反馈限制、管理员邮箱配置。
- `cloud-server/app/api/deps.py`：新增可选当前用户、管理员校验依赖。
- `cloud-server/app/models/user.py`：新增 `is_admin`。
- `cloud-server/app/services/rate_limit_service.py`：新增 feedback 相关限流类型。
- `cloud-server/app/services/account_service.py`：账号导出/删除时处理用户反馈数据。
- `cloud-server/app/infrastructure/oss_storage.py`：新增反馈附件 object key builder，或扩展为通用 `build_feedback_object_key`。

## backend

新增：

- `backend/app/schemas/cloud_feedback.py`
- `backend/app/services/cloud_announcement_service.py`
- `backend/app/services/cloud_feedback_service.py`
- `backend/tests/test_cloud_announcements_api.py`
- `backend/tests/test_cloud_feedback_api.py`

修改：

- `backend/app/infrastructure/cloud_api_client.py`：新增公告和反馈相关云 API 方法。
- `backend/app/api/cloud.py`：新增本地公告和反馈代理接口。
- `backend/app/services/app_config_service.py`：可选，保存本地公告关闭状态。
- `backend/app/schemas/cloud.py`：如团队希望集中维护云类型，也可在此补充公告/反馈 schema；否则保持独立 schema 文件。

## frontend

新增：

- `frontend/src/entities/announcement/types.ts`
- `frontend/src/entities/announcement/api.ts`
- `frontend/src/entities/feedback/types.ts`
- `frontend/src/entities/feedback/api.ts`
- `frontend/src/features/announcements/GlobalAnnouncementBanner.vue`
- `frontend/src/features/announcements/AnnouncementDetailDialog.vue`
- `frontend/src/features/feedback/FeedbackDialog.vue`
- `frontend/src/features/feedback/FeedbackEntryButton.vue`

修改：

- `frontend/src/App.vue`：小范围挂载 `GlobalAnnouncementBanner` 和 `FeedbackEntryButton`。
- `frontend/src/features/app-config/AppSettingsDialog.vue`：可选，在设置里增加“反馈与公告”入口。
- `frontend/src/shared/api/client.ts`：如现有 `apiUpload` 不足以支持多文件和进度，再做小范围扩展；否则不改。

## docs

可选新增：

- `cloud-server/docs/ADMIN_ANNOUNCEMENTS_AND_FEEDBACK.md`

# Implementation Steps for Claude Code

## Phase 1: cloud-server 数据模型和迁移

1. 新增 `users.is_admin`：
   - 路径：`cloud-server/app/models/user.py`
   - 字段：`is_admin = Column(Boolean, nullable=False, server_default=sa.text("false"), index=True)`
   - Alembic 迁移在 `003_announcements_feedback.py` 中添加。

2. 新增 `announcements` 表：
   - `id`: UUID string, PK
   - `title`: String(120), not null
   - `body`: Text, not null
   - `severity`: String(24), not null, default `"info"`
     - allowed: `info`, `success`, `warning`, `critical`
   - `status`: String(24), not null, default `"draft"`
     - allowed: `draft`, `published`, `archived`
   - `audience`: String(24), not null, default `"all"`
     - first version only supports `all`
   - `platform`: String(32), nullable
     - values such as `windows`, `macos`, `linux`, nullable means all
   - `min_app_version`: String(32), nullable
   - `max_app_version`: String(32), nullable
   - `starts_at`: DateTime timezone-aware, nullable
   - `ends_at`: DateTime timezone-aware, nullable
   - `published_at`: DateTime timezone-aware, nullable
   - `created_by_id`: FK users.id, nullable
   - `created_at`, `updated_at`, `deleted_at`
   - indexes:
     - `(status, starts_at, ends_at)`
     - `(platform, status)`

3. 新增 `feedback_tickets` 表：
   - `id`: UUID string, PK
   - `user_id`: FK users.id, nullable
   - `contact_email`: String(255), nullable
   - `category`: String(32), not null
     - allowed: `bug`, `suggestion`, `data_loss`, `cloud`, `ui`, `other`
   - `title`: String(120), not null
   - `description`: Text, not null
   - `status`: String(32), not null, default `"open"`
     - allowed: `open`, `triaged`, `in_progress`, `closed`, `spam`
   - `priority`: String(16), nullable
     - allowed: `low`, `normal`, `high`, `urgent`
   - `app_version`: String(64), nullable
   - `platform`: String(64), nullable
   - `network_mode`: String(32), nullable
   - `client_diagnostics_json`: JSON/Text, nullable
   - `attachment_count`: Integer, not null default 0
   - `total_size_bytes`: BigInteger, not null default 0
   - `admin_note`: Text, nullable
   - `created_at`, `updated_at`, `deleted_at`
   - indexes:
     - `(user_id, created_at)`
     - `(status, created_at)`
     - `(category, created_at)`

4. 新增 `feedback_attachments` 表：
   - `id`: UUID string, PK
   - `feedback_id`: FK feedback_tickets.id, not null
   - `object_key`: String(512), not null
   - `filename`: String(255), not null
   - `content_type`: String(120), not null
   - `size_bytes`: BigInteger, not null
   - `checksum_sha256`: String(64), nullable
   - `status`: String(32), not null default `"uploading"`
     - allowed: `uploading`, `uploaded`, `failed`, `deleted`
   - `upload_id`: String(64), not null, unique
   - `upload_expires_at`: DateTime timezone-aware, not null
   - `created_at`, `uploaded_at`, `deleted_at`
   - indexes:
     - `(feedback_id, status)`
     - `(upload_id)`

5. 更新 `cloud-server/app/models/__init__.py`，确保 Alembic 能识别新模型。

## Phase 2: cloud-server 配置、权限和 OSS 基础能力

1. 修改 `cloud-server/app/core/config.py`，新增：
   - `admin_emails: str = ""`
   - `feedback_max_attachments: int = 5`
   - `feedback_max_attachment_size_bytes: int = 52_428_800`（50 MB）
   - `feedback_max_total_size_bytes: int = 157_286_400`（150 MB）
   - `feedback_allowed_content_types: str = "image/png,image/jpeg,image/webp,image/gif,video/mp4,video/webm,video/quicktime"`
   - `rate_limit_feedback_create_per_hour: int = 5`
   - `rate_limit_feedback_upload_per_hour: int = 20`
   - `feedback_attachment_url_expire_seconds: int = 1800`
   - 增加 `admin_email_list` 和 `feedback_allowed_content_type_set` property。

2. 修改 `cloud-server/app/api/deps.py`：
   - 保留现有 `get_current_user`。
   - 新增 `get_optional_current_user`：
     - 无 Authorization 时返回 `None`；
     - 有 Authorization 但无效时返回 401。
   - 新增 `require_admin_user`：
     - 当前用户 `is_admin == True` 或 `email in settings.admin_email_list` 才允许访问；
     - 否则 403。

3. 修改 `cloud-server/app/infrastructure/oss_storage.py`：
   - 新增 `build_feedback_object_key(feedback_id, attachment_id, filename)`：
     - 格式：`feedback/{yyyy}/{mm}/{feedback_id}/{attachment_id}/{safe_filename}`
     - 不包含用户邮箱或原始路径。
   - 复用 `generate_put_url`、`generate_get_url`、`head_object`、`delete_object`。
   - 不把 presigned URL 写入日志。

4. 扩展 `RateLimitService`：
   - 新增类型：`feedback_create`、`feedback_upload_init`
   - 支持按 `user_id` 或 `client_ip` 限流。

## Phase 3: cloud-server 公告 API

1. 新增 `cloud-server/app/schemas/announcement.py`：
   - `AnnouncementResponse`
   - `AnnouncementListResponse`
   - `AnnouncementCreateRequest`
   - `AnnouncementUpdateRequest`

2. 新增 `cloud-server/app/repositories/announcement_repo.py`：
   - `create`
   - `get_by_id`
   - `list_active(now, platform, app_version)`
   - `list_admin(status, limit, offset)`
   - `update`
   - `soft_delete`

3. 新增 `cloud-server/app/services/announcement_service.py`：
   - 只返回 `status=published` 且在有效时间窗内的公告。
   - 第一版 `app_version` 可只做字符串留存，不做复杂 semver 比较；如果实现版本过滤，必须写测试。
   - 公告正文按纯文本或安全 Markdown 处理，不允许原始 HTML。

4. 新增公开接口 `cloud-server/app/api/announcements.py`：
   - `GET /api/announcements`
   - query:
     - `platform?: str`
     - `app_version?: str`
   - response:
     ```json
     {
       "items": [
         {
           "id": "uuid",
           "title": "维护通知",
           "body": "今晚 23:00 云备份维护。",
           "severity": "warning",
           "published_at": "2026-05-27T00:00:00Z",
           "starts_at": null,
           "ends_at": null
         }
       ],
       "total": 1
     }
     ```
   - 不需要 Bearer token。
   - 云服务不可用由本地代理处理，不影响本地写作。

5. 新增管理员接口 `cloud-server/app/api/admin_announcements.py`：
   - prefix: `/api/admin/announcements`
   - 所有接口依赖 `require_admin_user`
   - `POST /api/admin/announcements`
   - `GET /api/admin/announcements`
   - `PATCH /api/admin/announcements/{announcement_id}`
   - `POST /api/admin/announcements/{announcement_id}/publish`
   - `POST /api/admin/announcements/{announcement_id}/archive`
   - `DELETE /api/admin/announcements/{announcement_id}`
   - 管理端 API 不进入普通桌面前端。

6. 在 `cloud-server/app/main.py` 注册：
   - `announcements_router`
   - `admin_announcements_router`

## Phase 4: cloud-server 反馈 API

1. 新增 `cloud-server/app/schemas/feedback.py`：
   - `FeedbackAttachmentInit`
   - `FeedbackCreateRequest`
   - `FeedbackCreateResponse`
   - `FeedbackCompleteRequest`
   - `FeedbackTicketResponse`
   - `AdminFeedbackUpdateRequest`
   - `AdminFeedbackListResponse`

2. 新增 `cloud-server/app/repositories/feedback_repo.py`：
   - ticket:
     - `create_ticket`
     - `get_ticket`
     - `list_tickets`
     - `update_ticket`
     - `soft_delete_ticket`
   - attachment:
     - `create_attachment`
     - `get_attachment`
     - `get_attachment_by_upload_id`
     - `list_attachments`
     - `mark_uploaded`
     - `mark_failed`
     - `soft_delete_attachment`

3. 新增 `cloud-server/app/services/feedback_service.py`：
   - 校验 `category`、`title`、`description`。
   - 限制：
     - 标题 1-120 字。
     - 描述 10-5000 字。
     - 附件最多 `feedback_max_attachments` 个。
     - 单附件不得超过 `feedback_max_attachment_size_bytes`。
     - 总附件不得超过 `feedback_max_total_size_bytes`。
     - MIME type 必须在白名单内。
   - 创建 ticket 后为每个附件生成 `upload_id`、`object_key`、presigned PUT URL。
   - complete 时用 `head_object` 校验 OSS 对象存在、大小一致、Content-Type 合法。
   - 若附件上传失败，ticket 可保留为 `open`，对应附件标记 `failed`，不要丢失用户文字反馈。

4. 新增公开/可选认证接口 `cloud-server/app/api/feedback.py`：
   - `POST /api/feedback`
     - auth: optional Bearer
     - request:
       ```json
       {
         "category": "bug",
         "title": "云备份按钮无响应",
         "description": "点击后没有任何提示。",
         "contact_email": "user@example.com",
         "app_version": "0.0.0",
         "platform": "windows",
         "network_mode": "auto",
         "client_diagnostics": {
           "cloud_available": true
         },
         "attachments": [
           {
             "filename": "screen.png",
             "content_type": "image/png",
             "size_bytes": 123456,
             "checksum_sha256": "optional-64-hex"
           }
         ]
       }
       ```
     - response:
       ```json
       {
         "id": "feedback_id",
         "status": "open",
         "upload_slots": [
           {
             "attachment_id": "uuid",
             "upload_id": "uuid",
             "upload_url": "https://...",
             "expires_at": "2026-05-27T00:30:00Z"
           }
         ]
       }
       ```
   - `POST /api/feedback/{feedback_id}/complete`
     - request:
       ```json
       {
         "uploads": [
           {
             "upload_id": "uuid",
             "checksum_sha256": "64hex"
           }
         ]
       }
       ```
     - response: ticket summary。

5. 新增管理员反馈接口 `cloud-server/app/api/admin_feedback.py`：
   - prefix: `/api/admin/feedback`
   - 依赖 `require_admin_user`
   - `GET /api/admin/feedback?status=&category=&limit=&offset=`
   - `GET /api/admin/feedback/{feedback_id}`
   - `PATCH /api/admin/feedback/{feedback_id}`
     - 可更新 `status`、`priority`、`admin_note`
   - `GET /api/admin/feedback/{feedback_id}/attachments/{attachment_id}/download-url`
     - 返回短期 presigned GET URL。
   - `DELETE /api/admin/feedback/{feedback_id}`
     - 软删除 ticket，并删除或软删除附件。

6. 在 `cloud-server/app/main.py` 注册：
   - `feedback_router`
   - `admin_feedback_router`

7. 审计：
   - 在创建反馈、完成上传、管理员查看下载 URL、管理员修改状态时调用 `audit_event`。
   - 审计日志不得包含反馈正文全文、附件 URL、presigned URL。

## Phase 5: 账号导出/删除和隐私处理

1. 修改 `cloud-server/app/services/account_service.py`：
   - `export_account_data(user_id)` 增加用户反馈元数据：
     - feedback id、category、title、status、created_at、attachment_count。
     - 不导出管理员备注。
     - 不导出 presigned URL。
   - `confirm_deletion(user_id, ...)`：
     - 对该用户提交的反馈执行隐私处理。
     - 推荐策略：删除用户关联和联系方式，删除附件 OSS 对象，保留匿名 ticket 用于问题统计。
     - 如果实现为完全删除，也必须删除 OSS 对象并写测试。

2. 匿名反馈：
   - 如果只有 `contact_email`，账号删除无法自动关联，隐私说明文档中应说明。
   - 管理员处理反馈时不得公开用户联系方式。

## Phase 6: backend 本地代理

1. 修改 `backend/app/infrastructure/cloud_api_client.py`：
   - 新增：
     - `list_announcements(platform=None, app_version=None)`
     - `create_feedback(payload)`
     - `upload_feedback_attachment(upload_url, content, content_type, timeout=120.0)`
     - `complete_feedback(feedback_id, uploads)`
   - 上传附件时复用 `httpx.Client`，根据当前网络模式决定是否 `trust_env`。
   - 上传失败时解析错误，不返回完整 OSS URL。

2. 新增 `backend/app/services/cloud_announcement_service.py`：
   - 调用云端 `GET /api/announcements`。
   - 合并本地关闭状态：
     - 可使用 `AppConfigService` 存储 `dismissed_announcement_ids`。
     - 或使用前端 localStorage。若使用前端 localStorage，则本服务只代理列表。
   - 云服务未配置或不可达时返回空列表，并附带 `cloud_available=false`，不要抛出会打断 UI 的异常。

3. 新增 `backend/app/services/cloud_feedback_service.py`：
   - 接收本地 API 传入的字段和 `UploadFile` 列表。
   - 校验文件数量、大小、content type。
   - 读取文件内容时注意大文件内存风险：
     - 第一版可限制 50 MB 单文件、5 个附件；
     - 如果实现为一次性读入内存，必须明确受限；
     - 更优方案是临时文件流式上传，但不要引入大依赖。
   - 计算 SHA256。
   - 调用云端 create feedback。
   - 逐个上传附件。
   - 调用 complete。
   - 返回：
     ```json
     {
       "id": "feedback_id",
       "status": "open",
       "uploaded_attachments": 2,
       "failed_attachments": 0
     }
     ```

4. 修改 `backend/app/api/cloud.py`：
   - 新增：
     - `GET /api/cloud/announcements`
     - `POST /api/cloud/announcements/{announcement_id}/dismiss`
     - `POST /api/cloud/feedback`
   - `POST /api/cloud/feedback` 使用 multipart form:
     - fields:
       - `category`
       - `title`
       - `description`
       - `contact_email`
       - `include_diagnostics`
     - files:
       - `attachments`
   - 错误返回保持 `{"detail": "错误信息"}`。

5. 新增/更新 backend tests：
   - 公告代理：云未配置返回空列表；云端返回公告可正常透传。
   - 反馈代理：文本反馈、图片反馈、超大小、非法类型、云端失败、附件上传失败。

## Phase 7: frontend 公告展示

1. 新增 `frontend/src/entities/announcement/types.ts`：
   - `Announcement`
   - `AnnouncementListResponse`

2. 新增 `frontend/src/entities/announcement/api.ts`：
   - `listAnnouncements()`
   - `dismissAnnouncement(id)`

3. 新增 `frontend/src/features/announcements/GlobalAnnouncementBanner.vue`：
   - 应用启动后拉取公告。
   - 显示优先级最高且未关闭的一条公告。
   - 支持“查看详情”和“关闭”。
   - 关闭后写入本地状态，刷新后不再显示同一公告。
   - 云服务不可达时静默隐藏，不影响本地使用。
   - UI 不要遮挡写作编辑区；横幅高度应固定，移动端适配。

4. 新增 `frontend/src/features/announcements/AnnouncementDetailDialog.vue`：
   - 展示标题、正文、发布时间。
   - 正文按纯文本展示，换行保留。
   - 不使用 `v-html`，除非引入安全 Markdown sanitizer；第一版不建议引入依赖。

5. 修改 `frontend/src/App.vue`：
   - 小范围挂载 `GlobalAnnouncementBanner`。
   - 不重写现有路由结构。
   - 保持 `ThemeSwitcher` 位置不与公告冲突。

## Phase 8: frontend 用户反馈

1. 新增 `frontend/src/entities/feedback/types.ts`：
   - `FeedbackCategory`
   - `FeedbackSubmitResponse`

2. 新增 `frontend/src/entities/feedback/api.ts`：
   - `submitFeedback(formData: FormData)`
   - 使用 `apiUpload`。

3. 新增 `frontend/src/features/feedback/FeedbackDialog.vue`：
   - 字段：
     - 分类：问题反馈、功能建议、数据风险、云服务问题、界面体验、其他。
     - 标题。
     - 详细描述。
     - 联系邮箱（可选）。
     - 附件选择：图片/视频。
     - 是否附带基础诊断信息（默认可勾选，但必须说明内容范围）。
   - 文件限制：
     - 最多 5 个。
     - 单文件 50 MB。
     - 只允许图片/视频白名单类型。
   - 提交前提示：
     - “图片和视频可能包含作品内容或个人信息，请确认后提交。”
   - 提交中显示进度状态：
     - 第一版若没有精确上传进度，至少显示“正在提交 / 正在上传附件 / 已完成”。
   - 成功后显示反馈编号。
   - 失败时显示可理解错误，不显示堆栈。

4. 新增 `frontend/src/features/feedback/FeedbackEntryButton.vue`：
   - 提供全局“反馈”入口。
   - 推荐放在右下角或设置弹窗内，不遮挡正文编辑器。
   - 如果担心常驻按钮干扰写作，可只在 `AppSettingsDialog` 和项目列表页放入口。

5. 修改 `frontend/src/App.vue` 或 `frontend/src/features/app-config/AppSettingsDialog.vue`：
   - 方案 A：全局轻量“反馈”按钮，随时可提交。
   - 方案 B：设置页中新增“反馈与帮助”区块。
   - Claude Code 执行时应优先选择不打扰写作的方案；若全局按钮遮挡编辑器，应改为设置内入口。

## Phase 9: 管理员使用说明

1. 新增 `cloud-server/docs/ADMIN_ANNOUNCEMENTS_AND_FEEDBACK.md`：
   - 如何设置 `ADMIN_EMAILS`。
   - 如何将某用户设置为管理员。
   - 如何用 Swagger 或 curl 登录并发布公告。
   - 如何查看反馈列表、下载附件、更新反馈状态。
   - OSS lifecycle 建议：
     - `feedback/` 前缀可设置 180-365 天生命周期。
     - 已关闭反馈附件可定期清理。
   - 不要把 admin token、JWT、OSS Key 写入文档示例。

2. 文档示例使用占位符：
   - `<ACCESS_TOKEN>`
   - `<ANNOUNCEMENT_ID>`
   - `<FEEDBACK_ID>`

# Constraints

- 不强制用户登录。公告对所有配置云服务的客户端可见；反馈支持匿名提交。
- 桌面端和前端不得持有 OSS AccessKey。
- 普通客户端不得暴露管理员发布公告或查看反馈的入口。
- 反馈附件只允许图片和视频白名单类型，不允许 `.exe`、脚本、压缩包等任意文件。
- 不自动上传用户正文、项目数据库、日志或本地配置。
- 反馈正文、附件文件名、联系方式不得进入普通日志。
- presigned URL 不得写入日志、审计日志或错误提示。
- 公告正文第一版使用纯文本，不使用不安全 HTML。
- 云服务不可用时，公告和反馈入口可以提示不可用，但不得影响本地写作。
- 不引入大型 UI 库。
- 不做超出本任务的客服系统、评论系统、站内私信、邮件通知、工单自动分派。
- 如果文件上传实现需要新依赖，必须先说明原因；优先使用 FastAPI、httpx、oss2、SQLAlchemy 现有栈。

# Verification Commands

Claude Code 完成后执行：

## cloud-server

```powershell
cd F:\zhangshu\cloud-server
.\.venv\Scripts\python.exe -m pytest tests/test_announcements_api.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_feedback_api.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_admin_announcements.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_admin_feedback.py -q
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -c "from app.main import app; print(app.title)"
```

如 Alembic 可用：

```powershell
cd F:\zhangshu\cloud-server
.\.venv\Scripts\alembic.exe upgrade head
```

## backend

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\python.exe -m pytest tests/test_cloud_announcements_api.py -q
.\.venv\Scripts\python.exe -m pytest tests/test_cloud_feedback_api.py -q
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

```powershell
cd F:\zhangshu\cloud-server
docker compose config
```

人工验证：

- 发布一条 `published` 公告，启动前端，确认公告出现。
- 关闭公告，刷新页面，确认同一公告不再出现。
- 云服务不可达时启动前端，确认本地写作不受影响。
- 提交纯文本反馈，确认返回反馈编号。
- 提交带图片反馈，确认附件上传成功。
- 提交超大小视频，确认被拒绝且提示清晰。
- 管理员登录后查看反馈列表，生成附件下载 URL。

# Acceptance Criteria

- 公告：
  - 管理员可以创建、发布、归档公告。
  - 普通客户端可以读取当前有效公告。
  - 未登录用户也能看到面向全体用户的公告。
  - 用户关闭公告后，本机不重复打扰。
  - 云服务不可用时不影响本地写作。
- 反馈：
  - 用户可以提交文本反馈。
  - 用户可以附加图片或视频。
  - 已登录用户反馈自动关联 `user_id`。
  - 未登录用户可以匿名提交，联系方式可选。
  - 附件通过服务端签名 URL 上传 OSS，桌面端不持有 OSS AccessKey。
  - 附件大小、数量、类型限制生效。
  - 反馈提交有清晰成功/失败提示。
  - 管理员可以查看反馈、更新状态、获取附件下载 URL。
- 安全和隐私：
  - 管理员接口普通用户不可访问。
  - 不记录 presigned URL、token、密码、OSS AccessKey。
  - 账号导出/删除覆盖已登录用户的反馈数据。
  - 公告正文不使用不安全 HTML。
- 架构：
  - cloud-server API/Service/Repository/Model/Schema 分层清晰。
  - backend 只做代理、校验和上传协调，不承载云端权威数据。
  - frontend 只负责展示、表单和交互，不直接访问 OSS Key 或实现云业务规则。

# Risks and Watchpoints

- 反馈附件可能包含用户作品内容，必须明确提示用户确认后提交。
- 视频文件可能造成 OSS 成本上升，必须限制大小、数量和频率，并建议配置 OSS lifecycle。
- 匿名反馈容易被滥用，必须按 IP 限流，并保留 spam 状态供管理员处理。
- 管理员接口如果误暴露到普通 UI，会产生安全风险；只保留 API 和文档，不接入普通客户端入口。
- 公告如果每次打开都弹窗会干扰写作，关闭状态必须本地持久化。
- 如果使用 Markdown 渲染公告，必须有 sanitizer；第一版建议纯文本，避免 XSS。
- 本地 sidecar 如果一次性读取 50 MB 视频到内存，理论上可接受但要受限；后续可再规划流式上传。
- 账号删除时反馈处理策略要谨慎：既要尊重隐私，也要保留问题追踪所需的匿名统计。
- Tauri 打包后文件选择、上传和网络代理行为要人工验收。

# Review Checklist

- [ ] 是否没有强制用户登录？
- [ ] 公告是否由 cloud-server 统一发布，普通客户端只读取？
- [ ] 管理员接口是否有 `require_admin_user` 保护？
- [ ] 普通前端是否没有暴露管理员发布入口？
- [ ] 公告关闭状态是否本地持久化？
- [ ] 公告正文是否避免 `v-html` 或不安全 HTML？
- [ ] 反馈是否支持文本、图片、视频？
- [ ] 反馈附件是否有数量、大小、MIME 类型限制？
- [ ] 反馈附件是否使用 presigned URL 上传，且桌面端不持有 OSS AccessKey？
- [ ] 反馈提交失败时是否保留用户文字内容或给出清晰提示？
- [ ] 云服务不可用时是否不影响本地写作？
- [ ] 是否没有把业务逻辑堆进 Vue 组件？
- [ ] 是否没有把数据访问逻辑写进 API router？
- [ ] 是否没有在 Repository 层写业务判断？
- [ ] 账号导出和删除是否覆盖反馈数据？
- [ ] 日志和审计是否不包含 token、密码、OSS Key、presigned URL、反馈正文全文？
- [ ] 是否补充了 cloud-server、backend、frontend 对应测试？
- [ ] 是否运行了计划中的验证命令？
