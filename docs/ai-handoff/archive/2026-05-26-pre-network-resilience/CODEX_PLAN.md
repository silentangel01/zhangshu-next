<!-- archived: 2026-05-26; reason: superseded by cloud network resilience planning -->

# Task Summary

为章枢新增一个独立远程服务端项目：`F:\zhangshu\cloud-server\`，项目名为“章枢云 API”。该服务端负责用户注册、登录、JWT 鉴权、云端项目管理、阿里云 OSS presigned URL 上传/下载、备份记录管理，并严格兼容桌面端现有 `CloudApiClient` 已调用的 12 个端点契约。

本计划只规划实现，不由 Codex 修改业务代码。Codex 未创建 `cloud-server` 项目、未修改桌面端、未改动后端或前端业务文件。本计划应由 Claude Code 作为 Local Executor 执行。Claude Code 执行前必须再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，不要强行实现。

# Current Codebase Findings

- 当前桌面端已经具备云备份客户端侧边界：
  - `backend/app/infrastructure/cloud_api_client.py`：远程章枢云 HTTP 客户端，读取 `ZHANGSHU_CLOUD_API_BASE_URL`，持有 JWT access token。
  - `backend/app/services/cloud_auth_service.py`：本地登录状态和 token 加密存储，调用远程 `/api/auth/login`、`/api/auth/register`、`/api/auth/refresh`、`/api/auth/me`。
  - `backend/app/services/cloud_backup_service.py`：本地项目备份 zip 生成、云项目启用、云备份上传/恢复流程协调。
  - `backend/app/api/cloud.py`：桌面端本地 API，转发云登录、云启用、云备份操作。
  - `frontend/src/features/cloud/CloudAccountDialog.vue`、`frontend/src/features/cloud/CloudBackupPanel.vue`：云账号与云备份 UI。
- 当前仓库中不存在 `F:\zhangshu\cloud-server\`，本次应新建独立项目。
- 章枢桌面端的远程 API 契约已经由 `CloudApiClient` 固定，服务端必须兼容以下路径和字段：
  - `POST /api/auth/login`
  - `POST /api/auth/register`
  - `POST /api/auth/refresh`
  - `GET /api/auth/me`
  - `POST /api/projects`
  - `GET /api/projects`
  - `POST /api/projects/{project_id}/backups/init`
  - `PUT {upload_url}`：由阿里云 OSS 接收，不在 FastAPI 服务内实现。
  - `POST /api/projects/{project_id}/backups/complete`
  - `GET /api/projects/{project_id}/backups`
  - `GET /api/projects/{project_id}/backups/{backup_id}/download-url`
  - `DELETE /api/projects/{project_id}/backups/{backup_id}`
- 当前桌面端不会持有 OSS AccessKey，云服务端必须唯一持有 OSS AccessKey，并只向桌面端返回短时有效的 OSS 签名 URL。
- 安全参考边界：
  - 密码存储应遵循 OWASP Password Storage Cheat Sheet：使用慢哈希算法、每个密码独立盐值、合理 cost 参数。
  - 登录错误和认证流程应遵循 OWASP Authentication Cheat Sheet：避免泄露账号是否存在，限制暴力尝试。
  - JWT / refresh token 应支持过期、轮换、撤销或服务端可控失效策略，避免长期不可控 token。

# Architecture Decision

## 1. 独立项目边界

- 在 `F:\zhangshu\cloud-server\` 创建独立 FastAPI 项目。
- `cloud-server` 不依赖 `F:\zhangshu\backend\` 的任何代码，不 import 桌面端 `app.*` 模块。
- 只通过 HTTP 契约与桌面端通信。
- 桌面端通过 `ZHANGSHU_CLOUD_API_BASE_URL` 指向该服务端，例如 `http://127.0.0.1:9000` 或生产域名。

## 2. 分层结构

建议目录结构：

```text
cloud-server/
  README.md
  .env.example
  .gitignore
  Dockerfile
  docker-compose.yml
  requirements.txt
  alembic.ini
  app/
    main.py
    api/
      __init__.py
      deps.py
      auth.py
      projects.py
      backups.py
    core/
      __init__.py
      config.py
      errors.py
      security.py
    db/
      __init__.py
      base.py
      session.py
    infrastructure/
      __init__.py
      oss_storage.py
    models/
      __init__.py
      user.py
      refresh_token.py
      cloud_project.py
      cloud_backup.py
    repositories/
      __init__.py
      user_repo.py
      refresh_token_repo.py
      cloud_project_repo.py
      cloud_backup_repo.py
    schemas/
      __init__.py
      auth.py
      project.py
      backup.py
    services/
      __init__.py
      auth_service.py
      token_service.py
      project_service.py
      backup_service.py
  alembic/
    env.py
    script.py.mako
    versions/
  tests/
    conftest.py
    test_auth_api.py
    test_project_api.py
    test_backup_api.py
    test_security.py
```

## 3. 技术选型

- Web：FastAPI + uvicorn。
- ORM：SQLAlchemy 2.0。
- 数据库：生产使用 PostgreSQL；测试和本地快速开发可使用 SQLite。
- 迁移：Alembic。
- 配置：pydantic-settings + `.env`。
- JWT：PyJWT，算法默认 `HS256`。
- 密码哈希：bcrypt，推荐通过 `passlib[bcrypt]` 封装；bcrypt rounds 默认 12，可通过环境变量调整。
- OSS：`oss2`。
- 测试：pytest + FastAPI TestClient / httpx。

## 4. 安全策略

- 注册和登录不向前端返回 `password_hash`、内部 token hash、OSS object 内部策略等敏感字段。
- 用户 email 统一做 trim + lowercase normalize，并设置唯一索引。
- 密码要求：
  - 最小长度建议 10 或 12，Claude 可根据 UI 体验最终选择，但不得低于 8。
  - bcrypt 受 72 bytes 限制，服务端必须显式校验或截断前拒绝过长密码，避免用户误以为完整长密码生效。
  - 不做复杂字符组成强制，但应拒绝常见空密码、纯空白和过短密码。
- 登录失败返回统一错误，例如 `{"detail": "邮箱或密码错误"}`，不要区分邮箱不存在或密码错误。
- 登录和注册接口增加基础限流：
  - V1 可先实现进程内限流依赖：按 IP + email 维度限制短时间失败次数。
  - README 中说明生产环境仍建议在 Nginx、负载均衡或云 WAF 层增加限流。
- Access token 短期有效，默认 60 分钟。
- Refresh token 默认 30 天有效，必须服务端可撤销：
  - refresh token 可以是 JWT，但必须含 `jti`。
  - 数据库保存 refresh token 的 `jti_hash` 或 token hash，不保存明文 refresh token。
  - `/api/auth/refresh` 成功后轮换 refresh token：撤销旧 token，签发新 access token 和新 refresh token。
- 生产环境必须使用 HTTPS；Docker 本身可提供 HTTP，README 说明需要由反向代理或云服务终止 TLS。
- CORS 不得使用 `*`，必须从 `CORS_ORIGINS` 环境变量读取。
- 不记录密码、JWT、refresh token、OSS AccessKey、presigned URL 完整值。
- OSS AccessKey 只存在云服务端环境变量中，桌面端绝不接触。
- OSS presigned URL 默认 1800 秒有效。
- `complete` 阶段必须校验：
  - 项目归属当前用户；
  - `upload_id` 属于该项目且未过期；
  - OSS object 存在；
  - OSS object size 与 `size_bytes` 一致；
  - `checksum_sha256` 格式为 64 位 hex。
- V1 无法在不下载文件的前提下验证 zip 的真实 SHA256，因为桌面端当前 PUT 到 OSS 时未发送 hash metadata。V1 先存储桌面端上报的 checksum，并通过 object exists + size 做轻量校验；后续可增加后台校验任务或在签名 PUT 时要求 `x-oss-meta-sha256`。

# Files to Create or Modify

只允许 Claude Code 创建或修改 `F:\zhangshu\cloud-server\` 下的文件。除非执行过程中发现桌面端契约与本文不一致，否则不要修改 `backend/`、`frontend/`、`docs/` 其他文件。

## 新建项目根文件

- `cloud-server/README.md`
- `cloud-server/.env.example`
- `cloud-server/.gitignore`
- `cloud-server/requirements.txt`
- `cloud-server/Dockerfile`
- `cloud-server/docker-compose.yml`
- `cloud-server/alembic.ini`

## 新建应用文件

- `cloud-server/app/main.py`
- `cloud-server/app/core/config.py`
- `cloud-server/app/core/security.py`
- `cloud-server/app/core/errors.py`
- `cloud-server/app/db/base.py`
- `cloud-server/app/db/session.py`
- `cloud-server/app/api/deps.py`
- `cloud-server/app/api/auth.py`
- `cloud-server/app/api/projects.py`
- `cloud-server/app/api/backups.py`
- `cloud-server/app/models/user.py`
- `cloud-server/app/models/refresh_token.py`
- `cloud-server/app/models/cloud_project.py`
- `cloud-server/app/models/cloud_backup.py`
- `cloud-server/app/schemas/auth.py`
- `cloud-server/app/schemas/project.py`
- `cloud-server/app/schemas/backup.py`
- `cloud-server/app/repositories/user_repo.py`
- `cloud-server/app/repositories/refresh_token_repo.py`
- `cloud-server/app/repositories/cloud_project_repo.py`
- `cloud-server/app/repositories/cloud_backup_repo.py`
- `cloud-server/app/services/auth_service.py`
- `cloud-server/app/services/token_service.py`
- `cloud-server/app/services/project_service.py`
- `cloud-server/app/services/backup_service.py`
- `cloud-server/app/infrastructure/oss_storage.py`

## 新建迁移与测试文件

- `cloud-server/alembic/env.py`
- `cloud-server/alembic/script.py.mako`
- `cloud-server/alembic/versions/<timestamp>_create_initial_cloud_tables.py`
- `cloud-server/tests/conftest.py`
- `cloud-server/tests/test_auth_api.py`
- `cloud-server/tests/test_project_api.py`
- `cloud-server/tests/test_backup_api.py`
- `cloud-server/tests/test_security.py`

# Implementation Steps for Claude Code

## Phase 0: 执行前确认

1. 确认 `F:\zhangshu\cloud-server\` 不存在或为空。
2. 如目录已存在且有文件，停止并向用户报告，不要覆盖用户已有实现。
3. 再次读取 `backend/app/infrastructure/cloud_api_client.py`，确认桌面端远程契约仍与本计划一致。
4. 不修改 `F:\zhangshu\backend\` 和 `F:\zhangshu\frontend\`。

## Phase 1: 创建项目骨架

1. 创建 `cloud-server/` 目录。
2. 创建 Python 包目录和空 `__init__.py`。
3. 创建 `requirements.txt`，建议依赖：

```text
fastapi
uvicorn[standard]
SQLAlchemy>=2.0
alembic
pydantic-settings
python-dotenv
PyJWT
passlib[bcrypt]
email-validator
oss2
psycopg[binary]
pytest
httpx
```

4. 创建 `.gitignore`，至少忽略：

```text
.env
.venv/
__pycache__/
.pytest_cache/
*.pyc
.coverage
htmlcov/
```

5. 创建 `.env.example`，包含：

```env
DATABASE_URL=postgresql+psycopg://zhangshu:zhangshu@postgres:5432/zhangshu_cloud
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
BCRYPT_ROUNDS=12
OSS_ACCESS_KEY_ID=your-access-key-id
OSS_ACCESS_KEY_SECRET=your-access-key-secret
OSS_BUCKET_NAME=zhangshu-backups
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_PRESIGNED_URL_EXPIRE_SECONDS=1800
MAX_BACKUP_SIZE_BYTES=524288000
CORS_ORIGINS=http://localhost:5180,http://127.0.0.1:5180,http://localhost:5173,http://127.0.0.1:5173
```

## Phase 2: 配置、数据库和迁移

1. 在 `app/core/config.py` 中用 `pydantic-settings` 定义 `Settings`：
   - `database_url`
   - `jwt_secret_key`
   - `jwt_algorithm`
   - `jwt_access_token_expire_minutes`
   - `jwt_refresh_token_expire_days`
   - `bcrypt_rounds`
   - `oss_access_key_id`
   - `oss_access_key_secret`
   - `oss_bucket_name`
   - `oss_endpoint`
   - `oss_presigned_url_expire_seconds`
   - `max_backup_size_bytes`
   - `cors_origins`
2. 在 `app/db/base.py` 定义 `Base = DeclarativeBase`。
3. 在 `app/db/session.py` 创建 engine、SessionLocal、`get_db()`。
4. 创建模型：
   - `User`
     - `id: UUID string PK`
     - `email: String unique index`
     - `password_hash: String`
     - `display_name: String`
     - `is_active: Boolean default True`
     - `created_at`
     - `updated_at`
   - `RefreshToken`
     - `id: UUID string PK`
     - `user_id: FK users.id`
     - `jti_hash: String unique index`
     - `expires_at`
     - `revoked_at nullable`
     - `created_at`
     - `replaced_by_id nullable`
   - `CloudProject`
     - `id: UUID string PK`
     - `owner_id: FK users.id index`
     - `title: String`
     - `created_at`
     - `updated_at`
     - `deleted_at nullable`
   - `CloudBackup`
     - `id: UUID string PK`
     - `project_id: FK cloud_projects.id index`
     - `object_key: String unique`
     - `filename: String`
     - `size_bytes: Integer`
     - `checksum_sha256: String nullable`
     - `status: String`，允许 `pending/uploading/success/failed`
     - `upload_id: String unique index`
     - `upload_expires_at`
     - `error_message nullable`
     - `created_at`
     - `uploaded_at nullable`
     - `deleted_at nullable`
5. 配置 Alembic：
   - `alembic/env.py` 引入 `app.db.base.Base` 和所有模型 metadata。
   - 创建初始迁移，生成上述 4 张表和必要索引。

## Phase 3: Schema 与统一错误

1. `schemas/auth.py`：
   - `LoginRequest(email: EmailStr, password: str)`
   - `RegisterRequest(email: EmailStr, password: str, display_name: str = "")`
   - `RefreshRequest(refresh_token: str)`
   - `TokenResponse(access_token: str, refresh_token: str, user_id: str | None = None)`
   - `MeResponse(id: str, email: str, display_name: str)`
2. `schemas/project.py`：
   - `CreateProjectRequest(title: str)`
   - `ProjectResponse(id: str, title: str, owner_id: str, created_at: datetime)`
   - `ProjectListResponse(items: list[ProjectResponse], total: int)`
3. `schemas/backup.py`：
   - `InitBackupRequest(filename: str, size_bytes: int)`
   - `InitBackupResponse(upload_url: str, upload_id: str)`
   - `CompleteBackupRequest(upload_id: str, checksum_sha256: str)`
   - `CompleteBackupResponse(id: str, object_key: str)`
   - `BackupResponse(id, filename, size_bytes, checksum_sha256, status, created_at, uploaded_at)`
   - `BackupListResponse(items: list[BackupResponse], total: int)`
   - `DownloadUrlResponse(download_url: str)`
4. 所有错误使用 FastAPI `HTTPException(detail="...")`，返回 JSON：`{"detail": "错误信息"}`。
5. 不新增与桌面端契约不兼容的 wrapper 字段。

## Phase 4: 认证与 Token

1. `core/security.py`：
   - `normalize_email(email: str) -> str`
   - `validate_password_strength(password: str) -> None`
   - `hash_password(password: str) -> str`
   - `verify_password(password: str, password_hash: str) -> bool`
   - `sha256_text(value: str) -> str`
2. 密码规则：
   - trim 后不得为空；
   - 长度不得低于 10 或 12；
   - UTF-8 byte length 不得超过 bcrypt 安全上限，建议限制为 72 bytes；
   - 注册失败返回明确但不泄露内部信息的中文错误。
3. `services/token_service.py`：
   - `create_access_token(user_id: str) -> str`
   - `create_refresh_token(user_id: str) -> tuple[token, jti, expires_at]`
   - `decode_token(token: str, expected_type: "access" | "refresh")`
   - payload 包含 `sub`、`type`、`exp`、`iat`、`jti`。
4. `services/auth_service.py`：
   - 注册：
     - email normalize；
     - 校验唯一；
     - bcrypt 哈希；
     - 创建 user；
     - 签发 access token + refresh token；
     - 保存 refresh token `jti_hash`；
     - 返回 `{"access_token": str, "refresh_token": str, "user_id": str}`。
   - 登录：
     - email normalize；
     - 如果用户不存在或密码错误，返回同一个 401 detail；
     - 成功后签发 token，同注册响应。
   - refresh：
     - 解码 refresh token；
     - 校验数据库中 jti 未撤销、未过期；
     - 撤销旧 refresh token；
     - 创建新 refresh token；
     - 返回 `{"access_token": str, "refresh_token": str}`。
   - me：
     - 通过 Bearer access token 取得用户；
     - 返回 `{"id": str, "email": str, "display_name": str}`。
5. `api/deps.py`：
   - `get_current_user()` 从 `Authorization: Bearer <token>` 解析 access token。
   - token 无效、过期、用户不存在、用户禁用，统一返回 401。
6. 基础限流：
   - 在 `api/auth.py` 的 login/register 上增加简单依赖或服务函数，按 IP + email 记录失败次数。
   - V1 可使用进程内字典，README 明确单进程有效；生产多实例需要 Redis 或网关限流。

## Phase 5: 项目接口

1. `POST /api/projects`
   - 认证：Bearer。
   - 请求：`{"title": str}`。
   - 校验 title trim 后非空，限制长度，例如 1-200。
   - 创建 `CloudProject(owner_id=current_user.id, title=title)`。
   - 响应严格为：

```json
{"id": "uuid", "title": "书名", "owner_id": "user_uuid", "created_at": "ISO_DATETIME"}
```

2. `GET /api/projects`
   - 认证：Bearer。
   - 只返回当前用户未删除项目。
   - 响应严格为：

```json
{"items": [], "total": 0}
```

3. 权限原则：
   - 所有 `{project_id}` 操作必须先按 `owner_id=current_user.id` 查询。
   - 如果项目不存在或不属于当前用户，统一返回 404，避免泄露其他用户项目存在性。

## Phase 6: OSS Storage Infrastructure

1. `infrastructure/oss_storage.py` 封装所有 OSS 操作，业务层不得直接调用 `oss2.Bucket`。
2. 初始化：
   - 使用 `OSS_ACCESS_KEY_ID`
   - 使用 `OSS_ACCESS_KEY_SECRET`
   - 使用 `OSS_BUCKET_NAME`
   - 使用 `OSS_ENDPOINT`
3. 方法：
   - `build_object_key(user_id, project_id, backup_id, filename) -> str`
   - `generate_put_url(object_key, expires_seconds, content_type="application/zip") -> str`
   - `generate_get_url(object_key, expires_seconds) -> str`
   - `head_object(object_key) -> dict`
   - `delete_object(object_key) -> None`
4. object key 格式：

```text
backups/{user_id}/{project_id}/{backup_id}/{safe_filename}
```

5. filename 处理：
   - 去除路径分隔符；
   - 限制长度；
   - 仅作为展示和 object key 最后一段；
   - 不信任客户端传入路径。
6. OSS 错误不要把 AccessKey、完整签名 URL、内部异常栈直接返回给用户。

## Phase 7: 备份接口

1. `POST /api/projects/{project_id}/backups/init`
   - 认证：Bearer。
   - 校验项目归属当前用户。
   - 请求：`{"filename": str, "size_bytes": int}`。
   - 校验：
     - filename 非空；
     - size_bytes > 0；
     - size_bytes <= `MAX_BACKUP_SIZE_BYTES`。
   - 创建 `CloudBackup`：
     - `status="uploading"`
     - `upload_id=<uuid>`
     - `object_key=backups/{user_id}/{project_id}/{backup_id}/{safe_filename}`
     - `upload_expires_at=now + presigned_url_expire`
   - 生成 OSS PUT presigned URL。
   - 响应严格为：

```json
{"upload_url": "https://...", "upload_id": "uuid"}
```

2. `POST /api/projects/{project_id}/backups/complete`
   - 认证：Bearer。
   - 请求：`{"upload_id": str, "checksum_sha256": str}`。
   - 校验：
     - 项目归属当前用户；
     - upload_id 存在且属于该项目；
     - 状态为 `uploading`；
     - 未超过 `upload_expires_at`；
     - checksum 为 64 位 hex；
     - OSS object 存在；
     - OSS object size 等于 `size_bytes`。
   - 更新：
     - `status="success"`
     - `checksum_sha256=<client checksum>`
     - `uploaded_at=now`
   - 响应严格为：

```json
{"id": "backup_uuid", "object_key": "backups/.../file.zip"}
```

3. `GET /api/projects/{project_id}/backups`
   - 认证：Bearer。
   - 只返回当前用户、该项目、未删除的备份。
   - 默认按 `created_at desc`。
   - 响应严格为：

```json
{
  "items": [
    {
      "id": "uuid",
      "filename": "backup.zip",
      "size_bytes": 123,
      "checksum_sha256": "64hex",
      "status": "success",
      "created_at": "ISO_DATETIME",
      "uploaded_at": "ISO_DATETIME"
    }
  ],
  "total": 1
}
```

4. `GET /api/projects/{project_id}/backups/{backup_id}/download-url`
   - 认证：Bearer。
   - 校验项目归属和备份归属。
   - 只允许 `status="success"` 的备份下载。
   - 生成 OSS GET presigned URL。
   - 响应严格为：

```json
{"download_url": "https://..."}
```

5. `DELETE /api/projects/{project_id}/backups/{backup_id}`
   - 认证：Bearer。
   - 校验项目归属和备份归属。
   - 删除 OSS object。
   - 数据库建议软删除：设置 `deleted_at=now`，或至少不再出现在 list 中。
   - 响应 204，无响应体。
6. 对失败上传的处理：
   - 如果 `complete` 检测到 object 不存在、大小不一致或 upload 过期，将记录 `status="failed"` 和 `error_message`。
   - README 中说明可后续加定时清理 pending/uploading 超时记录和 OSS 残留对象。

## Phase 8: FastAPI Main 与 CORS

1. `app/main.py`：
   - 创建 FastAPI app。
   - 注册 CORS middleware，origins 来自 `settings.cors_origins`。
   - include routers：
     - `auth.router`
     - `projects.router`
     - `backups.router`
   - 提供 `GET /health`，返回 `{"status": "ok"}`，仅用于部署健康检查，不影响桌面端契约。
2. 不要在 `main.py` 中写业务逻辑。
3. 所有路由函数只做请求解析、依赖注入和 HTTPException 转换，业务判断放到 service。

## Phase 9: Docker 与部署

1. `Dockerfile`：
   - Python slim 镜像。
   - 安装 `requirements.txt`。
   - 默认启动 `uvicorn app.main:app --host 0.0.0.0 --port 9000`。
2. `docker-compose.yml`：
   - `postgres` 服务：
     - image: postgres 16 或稳定版本。
     - volume 持久化。
     - healthcheck。
   - `cloud-api` 服务：
     - build `.`。
     - depends_on postgres healthcheck。
     - env_file `.env`。
     - ports `9000:9000`。
   - 开发可在 command 中先执行 `alembic upgrade head` 再启动；生产建议 README 说明迁移独立执行。
3. 不要把真实 `.env`、OSS AccessKey、JWT_SECRET_KEY 写入仓库。

## Phase 10: README

`cloud-server/README.md` 必须包含：

1. 项目用途：章枢云 API 服务端，独立于桌面端。
2. 本地开发：
   - 创建虚拟环境；
   - 安装依赖；
   - 复制 `.env.example` 为 `.env`；
   - 配置数据库和 OSS；
   - `alembic upgrade head`；
   - `uvicorn app.main:app --reload --port 9000`。
3. Docker 启动：
   - `docker compose up --build`
   - 健康检查 URL：`http://127.0.0.1:9000/health`
4. 桌面端连接：
   - 设置 `ZHANGSHU_CLOUD_API_BASE_URL=http://127.0.0.1:9000`。
5. 阿里云 OSS 配置：
   - 创建 Bucket；
   - 建议开启服务端加密；
   - 创建最小权限 RAM 用户或角色，只允许目标 Bucket 的必要 Put/Get/Delete/List/Head 权限；
   - 设置 Bucket CORS：
     - AllowedOrigin：桌面端实际 origin，开发可含 `http://localhost:5180`、`http://127.0.0.1:5180`；
     - AllowedMethod：`PUT`、`GET`、`HEAD`；
     - AllowedHeader：至少允许 `Content-Type`；
     - ExposeHeader：建议 `ETag`；
   - 设置生命周期规则：
     - 可按产品策略保留最近 N 天或 N 个版本；
     - V1 不自动删除用户数据，除非用户点击删除。
6. 安全注意：
   - 生产必须替换 `JWT_SECRET_KEY`；
   - 生产必须 HTTPS；
   - 不提交 `.env`；
   - 不把 OSS AccessKey 放到桌面端；
   - 建议启用云厂商告警和访问日志。

## Phase 11: 测试

1. `tests/conftest.py`：
   - 使用 SQLite in-memory 或临时 SQLite。
   - 覆盖 `get_db()`。
   - mock `OSSStorage`，不要真实访问阿里云。
2. `test_auth_api.py`：
   - 注册成功，返回 `access_token`、`refresh_token`、`user_id`。
   - 重复 email 注册失败。
   - 密码过短失败。
   - 登录成功。
   - 登录错误时不区分用户不存在和密码错误。
   - refresh 成功并轮换 refresh token。
   - 旧 refresh token 再次使用失败。
   - `GET /api/auth/me` 无 token 返回 401，有效 token 返回用户信息。
3. `test_project_api.py`：
   - 未登录创建项目返回 401。
   - 登录后创建项目返回契约字段。
   - 项目列表只返回当前用户项目。
   - 用户 A 不能访问用户 B 项目的备份接口。
4. `test_backup_api.py`：
   - init 返回 `upload_url` 和 `upload_id`。
   - init 拒绝空 filename、0 size、超大 size。
   - complete 成功后返回 `id` 和 `object_key`。
   - complete 拒绝错误 upload_id、过期 upload、size mismatch。
   - list 返回正确字段和 total。
   - download-url 仅允许 success 备份。
   - delete 返回 204，list 不再显示该备份。
5. `test_security.py`：
   - password_hash 不等于明文密码。
   - refresh token 数据库不保存明文 token。
   - 受保护接口无 Bearer token 返回 401。
   - CORS 不使用 `*`。

## Phase 12: 桌面端兼容性烟测

Claude Code 完成 `cloud-server` 后，进行最小联调：

1. 启动 cloud-server：

```powershell
cd F:\zhangshu\cloud-server
docker compose up --build
```

2. 运行迁移：

```powershell
cd F:\zhangshu\cloud-server
docker compose exec cloud-api alembic upgrade head
```

3. 设置桌面端本地后端环境变量：

```powershell
$env:ZHANGSHU_CLOUD_API_BASE_URL="http://127.0.0.1:9000"
```

4. 启动桌面端后端和前端，使用现有启动方式。
5. 在章枢 UI 中注册新账号、登录、为一本书启用云端保存、执行一次云端备份。
6. 如果没有真实 OSS 凭据，不做真实上传，只运行服务端测试和 mock OSS 测试；README 中说明真实 OSS 联调需要有效 Bucket 和 CORS。

# Constraints

- 这是独立项目，不能依赖 `F:\zhangshu\backend\` 中任何代码。
- 不修改桌面端 API 契约，请求和响应字段必须与用户给出的表格一致。
- 桌面端不得持有 OSS AccessKey。
- OSS AccessKey、JWT_SECRET_KEY、数据库密码不得写入仓库。
- 所有 API 错误统一 JSON：`{"detail": "错误信息"}`。
- 不允许在 Router/API 层堆积业务逻辑。
- 不允许在 Repository 层写权限判断和业务判断。
- 不允许为了快速完成而绕过用户归属校验。
- 不允许将其他用户项目或备份的存在性泄露给当前用户。
- 不允许在日志中记录密码、JWT、refresh token、OSS 密钥、完整签名 URL。
- 不允许返回 Python traceback 给客户端。
- `PUT {upload_url}` 是 OSS 端点，不是 FastAPI 路由。
- V1 只做备份文件存储，不实现云端编辑、实时同步、冲突合并或完整项目协作。
- 生产 HTTPS 和外层限流必须在 README 中明确说明；Docker 开发环境可以是 HTTP。

# Verification Commands

在 `F:\zhangshu\cloud-server\` 执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```powershell
python -c "from app.main import app; print(app.title)"
```

```powershell
alembic upgrade head
```

```powershell
pytest -q
```

```powershell
docker compose config
```

```powershell
docker compose up --build
```

新开 PowerShell 后执行健康检查：

```powershell
Invoke-RestMethod http://127.0.0.1:9000/health
```

注册/登录契约烟测：

```powershell
$base="http://127.0.0.1:9000"
$reg = Invoke-RestMethod "$base/api/auth/register" -Method Post -ContentType "application/json" -Body '{"email":"test@example.com","password":"test-password-123","display_name":"测试作者"}'
$reg.access_token
$headers = @{ Authorization = "Bearer $($reg.access_token)" }
Invoke-RestMethod "$base/api/auth/me" -Headers $headers
Invoke-RestMethod "$base/api/projects" -Method Post -Headers $headers -ContentType "application/json" -Body '{"title":"测试作品"}'
```

如果配置了真实 OSS，再执行备份 init / PUT / complete 联调；否则只执行 mock OSS 测试，不强行连接阿里云。

# Acceptance Criteria

- `cloud-server` 是独立 FastAPI 项目，不 import 桌面端 `backend/app/*`。
- Docker Compose 可以启动 PostgreSQL 和 cloud API。
- Alembic 初始迁移可以创建 `users`、`refresh_tokens`、`cloud_projects`、`cloud_backups`。
- 12 个端点全部实现，并与桌面端 `CloudApiClient` 请求/响应契约兼容。
- 注册：
  - email 唯一；
  - 密码 bcrypt 哈希；
  - 返回 `access_token`、`refresh_token`、`user_id`。
- 登录：
  - 错误信息不泄露账号是否存在；
  - 成功返回 token。
- refresh：
  - 支持 refresh token 轮换；
  - 旧 refresh token 不能重复使用。
- Bearer 鉴权：
  - 无 token、过期 token、非法 token 返回 401；
  - 当前用户不能访问其他用户项目和备份。
- 备份上传：
  - init 返回 OSS presigned PUT URL 和 upload_id；
  - complete 校验 upload_id、归属、过期时间、OSS object 存在、size 匹配；
  - success 记录可 list、可生成 download-url。
- 删除备份返回 204，并且 list 不再显示。
- 测试覆盖认证、项目、备份、基础安全约束。
- README 说明阿里云 OSS Bucket、CORS、生命周期、Docker、桌面端 `ZHANGSHU_CLOUD_API_BASE_URL` 配置。
- 未提交 `.env`、真实密钥、本地数据库、日志或临时文件。

# Risks and Watchpoints

- bcrypt 只处理前 72 bytes 密码，必须主动校验过长密码，否则长密码用户可能产生安全误解。
- presigned PUT URL 的签名字段必须与桌面端实际 PUT 行为兼容；桌面端当前使用 `Content-Type: application/zip`，OSS 签名时应考虑该 header。
- 仅凭桌面端上报的 `checksum_sha256` 无法证明 OSS 中实际文件内容 hash 一致；V1 至少校验 object 存在和 size，后续可增加后台校验。
- 进程内限流在多实例部署下不可靠；生产应补充网关、Nginx、Redis 或云 WAF 限流。
- Docker Compose 中自动执行 migration 适合开发，生产环境建议独立迁移步骤，避免多实例同时迁移。
- OSS Bucket CORS 若未配置 PUT/GET/HEAD，桌面端上传下载会失败。
- 生产 HTTPS 未配置时，JWT 和 presigned URL 会暴露在明文链路中，不能上线。
- Access token 过期后，桌面端当前是否自动 refresh 需要复核；如果桌面端未自动 refresh，服务端仍按契约实现 refresh，但可在 Claude 执行报告中提示后续桌面端改进。
- 删除备份时如果 OSS 删除成功但 DB 更新失败，或 DB 成功但 OSS 删除失败，需要明确错误处理；V1 建议先删 OSS，再软删除 DB，失败时返回 500 并保留记录。
- 不要把 `cloud-server/.env`、PostgreSQL volume、测试生成数据库提交。

# Review Checklist

- [ ] `cloud-server` 是否完全独立，不依赖桌面端后端代码？
- [ ] 12 个端点路径、方法、请求体、响应体是否完全兼容 `CloudApiClient`？
- [ ] 所有受保护端点是否都使用 Bearer JWT？
- [ ] 用户密码是否只保存 bcrypt hash，且没有明文日志？
- [ ] refresh token 是否服务端可撤销、可轮换，数据库不保存明文 token？
- [ ] 用户 A 是否无法访问用户 B 的项目和备份？
- [ ] OSS AccessKey 是否只在服务端 `.env` 中使用，没有进入桌面端和响应体？
- [ ] presigned URL 是否短时有效，默认约 30 分钟？
- [ ] init / complete 是否校验 filename、size、upload_id、OSS object、归属关系？
- [ ] API 错误是否统一为 `{"detail": "错误信息"}`？
- [ ] Router 是否保持薄层，业务逻辑是否放在 Service？
- [ ] Repository 是否只负责数据访问，不写复杂业务判断？
- [ ] Alembic 迁移是否可从空库成功创建所有表？
- [ ] Dockerfile 和 docker-compose 是否能一键启动？
- [ ] README 是否写清 OSS Bucket、CORS、生命周期、HTTPS 和桌面端 base URL 配置？
- [ ] 测试是否覆盖注册、登录、refresh、项目隔离、备份上传完成、下载 URL、删除？
- [ ] git diff 是否没有 `.env`、密钥、本地数据库、日志、临时文件？
