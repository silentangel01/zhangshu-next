<!-- archived: 2026-05-26; reason: cloud account privacy and abuse protection task completed -->

# Task Summary

本次任务是规划“章枢云账户与隐私 + 成本和滥用防护”。

目标不是新增写作业务功能，而是围绕云账户上线后的两个生产级问题补齐能力：

1. 云账户与隐私：
   - 用户能查看、导出、删除自己的云端账号数据。
   - 用户能理解哪些数据会上云，云备份不会变成黑盒。
   - 用户能退出所有设备、撤销会话、修改密码。
   - 服务端尽量最小化保存个人信息，日志和审计继续脱敏。

2. 成本和滥用防护：
   - 防止恶意注册、刷备份初始化、刷 OSS 上传、占满存储。
   - 将当前基础配额升级为用户可见的使用量、限制和错误提示。
   - 将 in-process 限流逐步替换为可在多 worker / Docker 生产环境生效的数据库限流。

Codex 未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

- 已阅读并归档上一轮生产级基线交接文件：
  - `docs/ai-handoff/archive/2026-05-26-cloud-production-hardening-completed/CODEX_PLAN.md`
  - `docs/ai-handoff/archive/2026-05-26-cloud-production-hardening-completed/CLAUDE_EXECUTION_REPORT.md`
- 上一轮 Claude 执行报告显示：
  - 已新增结构化日志、请求 ID、安全响应头、审计事件。
  - 已新增 `/ready`、生产配置校验、数据库备份/恢复脚本、preflight。
  - 已新增备份配额、数量配额、频率限制和 stale upload cleanup。
  - 云服务端测试通过：`86 passed`。
- 当前云账户模型 `cloud-server/app/models/user.py` 只有：
  - `id`
  - `email`
  - `password_hash`
  - `display_name`
  - `is_active`
  - `created_at`
  - `updated_at`
- 当前 refresh token 模型 `cloud-server/app/models/refresh_token.py` 缺少：
  - `user_agent`
  - `client_ip`
  - `last_used_at`
  - `revoked_reason`
  这会限制“设备/会话管理”和“退出所有设备”的用户可见能力。
- 当前认证接口 `cloud-server/app/api/auth.py` 使用 in-process rate limit：
  - 多 worker、容器重启或多实例部署时限流状态不共享。
  - 对生产滥用防护不够。
- 当前备份服务 `cloud-server/app/services/backup_service.py` 已有：
  - 总存储配额。
  - 备份数量配额。
  - 每小时 backup init 频率限制。
  - stale uploading 清理。
  但用户侧还看不到自己的使用量和限制，也没有账号级成本透明度。
- 当前云服务端没有账号删除、数据导出、修改密码、会话列表、撤销全部 token 等能力。
- 当前桌面端云 UI 有登录、注册、云备份和网络诊断，但没有隐私说明、云端数据导出/删除入口、配额/使用量展示。

# Architecture Decision

## 1. 云账户隐私以“用户自助可控”为原则

第一版不做复杂管理后台，优先提供用户自助接口：

- 查看账号资料。
- 修改显示名称。
- 修改密码。
- 查看当前云使用量。
- 导出账号元数据。
- 删除云端账号和云备份数据。
- 退出全部设备。

## 2. 删除账号采用“两阶段安全删除”

不要提供一键误删。建议：

1. 用户先发起删除请求，需输入密码确认。
2. 服务端返回影响范围：项目数、备份数、占用空间。
3. 用户再次提交明确确认文本，例如 `DELETE MY CLOUD DATA`。
4. 服务端执行：
   - 撤销 refresh tokens。
   - 删除 OSS 备份对象。
   - 软删除项目和备份记录。
   - 匿名化用户 email / display_name。
   - 设置 `deleted_at`、`anonymized_at`。

如果 OSS 删除失败，不应直接假装成功。应记录 `pending_deletion` 状态并返回“部分完成，需要稍后重试或管理员处理”。

## 3. 成本和滥用防护以“数据库可共享限流”为 V1

当前 in-process 限流不适合多 worker。V1 不引入 Redis，先增加数据库表实现跨 worker 的轻量限流：

- `rate_limit_events`
- `usage_events` 或直接聚合现有 `cloud_backups`

未来流量变大后再替换为 Redis / 网关 / WAF。

## 4. 用户可见配额

用户不应该只在超限时才知道限制。新增云使用量接口：

- 已用存储。
- 存储上限。
- 成功备份数量。
- 备份数量上限。
- 最近一小时备份初始化次数。
- 每小时上限。
- 最大单文件大小。

桌面端云备份面板展示这些数据，避免用户反复试错。

# Files to Create or Modify

## cloud-server 模型与迁移

- 修改：`cloud-server/app/models/user.py`
  - 增加 `deleted_at`
  - 增加 `deletion_requested_at`
  - 增加 `anonymized_at`
  - 增加 `privacy_version_accepted`
  - 可选增加 `password_changed_at`
- 修改：`cloud-server/app/models/refresh_token.py`
  - 增加 `user_agent`
  - 增加 `client_ip`
  - 增加 `last_used_at`
  - 增加 `revoked_reason`
- 新增：`cloud-server/app/models/rate_limit_event.py`
  - 数据库级限流事件。
- 可选新增：`cloud-server/app/models/account_deletion_request.py`
  - 如果两阶段删除需要短期保存确认 token。
- 新增迁移：`cloud-server/alembic/versions/<timestamp>_account_privacy_and_abuse.py`

## cloud-server Repository / Service

- 修改：`cloud-server/app/repositories/user_repo.py`
- 修改：`cloud-server/app/repositories/refresh_token_repo.py`
- 新增：`cloud-server/app/repositories/rate_limit_repo.py`
- 新增：`cloud-server/app/services/account_service.py`
  - 账号资料、修改密码、导出、删除、会话管理。
- 新增：`cloud-server/app/services/usage_service.py`
  - 计算用户存储、备份数量、频率限制使用情况。
- 新增：`cloud-server/app/services/rate_limit_service.py`
  - 数据库级限流。
- 修改：`cloud-server/app/services/auth_service.py`
  - 注册/登录/refresh 时记录 token 的 user_agent/client_ip。
  - 修改密码后撤销旧 refresh tokens。
  - 禁止 deleted/anonymized user 登录。
- 修改：`cloud-server/app/services/backup_service.py`
  - 复用 `UsageService`。
  - 将频率限制从 service 私有查询迁移到 `RateLimitService` 或保留备份专用限制但统一错误结构。

## cloud-server API / Schema

- 新增：`cloud-server/app/schemas/account.py`
- 新增：`cloud-server/app/schemas/usage.py`
- 新增：`cloud-server/app/api/account.py`
  - `GET /api/account/profile`
  - `PATCH /api/account/profile`
  - `POST /api/account/password/change`
  - `GET /api/account/sessions`
  - `DELETE /api/account/sessions/{session_id}`
  - `POST /api/account/sessions/revoke-all`
  - `GET /api/account/usage`
  - `GET /api/account/export`
  - `POST /api/account/delete-request`
  - `DELETE /api/account`
- 修改：`cloud-server/app/main.py`
  - include account router。
- 修改：`cloud-server/app/api/auth.py`
  - 替换 in-process rate limit 或先并行接入 DB rate limit。

## 桌面端后端

- 修改：`backend/app/infrastructure/cloud_api_client.py`
  - 增加远程账号/隐私/使用量相关方法。
- 修改：`backend/app/api/cloud.py`
  - 增加本地转发 API：
    - 获取云账号资料。
    - 修改密码。
    - 获取使用量。
    - 导出账号数据。
    - 请求删除账号 / 确认删除账号。
    - 退出全部设备。
- 修改：`backend/app/schemas/cloud.py`
  - 增加对应 schema。
- 修改：`backend/app/services/cloud_auth_service.py`
  - 删除账号后清理本地 token 和云账户状态。

## 桌面端前端

- 修改：`frontend/src/entities/cloud/types.ts`
  - 增加 account profile、usage、session、export/delete 类型。
- 修改：`frontend/src/entities/cloud/api.ts`
  - 增加账号隐私和使用量 API 封装。
- 新增：`frontend/src/features/cloud/CloudAccountPrivacyPanel.vue`
  - 账号资料、修改密码、退出全部设备、导出、删除账号。
- 新增：`frontend/src/features/cloud/CloudUsagePanel.vue`
  - 使用量、配额、备份数量、频率限制显示。
- 修改：`frontend/src/features/app-config/AppSettingsDialog.vue`
  - 在章枢云账户区域加入“账户与隐私”“使用量与限制”入口。
- 修改：`frontend/src/features/cloud/CloudBackupPanel.vue`
  - 显示云备份使用量摘要。
  - 超限错误时显示更可理解的提示。

## 文档与测试

- 新增：`cloud-server/docs/PRIVACY_AND_ACCOUNT.md`
  - 说明云端保存什么、不保存什么、如何导出/删除。
- 修改：`cloud-server/docs/INCIDENT_RUNBOOK.md`
  - 增加滥用、配额耗尽、账号删除失败的处理。
- 新增测试：
  - `cloud-server/tests/test_account_api.py`
  - `cloud-server/tests/test_account_deletion.py`
  - `cloud-server/tests/test_usage_api.py`
  - `cloud-server/tests/test_db_rate_limit.py`
  - `backend/tests/test_cloud_account_proxy_api.py`

# Implementation Steps for Claude Code

## Phase 1: 数据模型和迁移

1. 修改 `User`：
   - `deleted_at: datetime | None`
   - `deletion_requested_at: datetime | None`
   - `anonymized_at: datetime | None`
   - `privacy_version_accepted: str | None`
   - `password_changed_at: datetime | None`
2. 修改 `RefreshToken`：
   - `user_agent: str | None`
   - `client_ip: str | None`
   - `last_used_at: datetime | None`
   - `revoked_reason: str | None`
3. 新增 `RateLimitEvent`：

```text
id
scope: auth_login | auth_register | backup_init | account_delete
key: ip/email/user_id 组合 hash 或安全字符串
user_id nullable
client_ip nullable
created_at
expires_at
```

4. 如需要两阶段删除请求，新增 `AccountDeletionRequest`：

```text
id
user_id
confirm_token_hash
summary_json
expires_at
used_at nullable
created_at
```

5. 创建 Alembic 迁移，确保 PostgreSQL 和 SQLite 测试均可运行。

## Phase 2: 数据库级限流

1. 新建 `RateLimitService`：
   - `check_and_record(scope, key, limit, window_seconds, user_id=None, client_ip=None)`
   - 清理过期事件。
2. 替换 `api/auth.py` 中 `_rate_limit_store` in-process 实现。
3. 限流 key 规则：
   - 登录：`client_ip + normalized_email`
   - 注册：`client_ip + email_domain` 或 `client_ip`
   - 备份 init：`user_id`
   - 删除账号：`user_id`
4. key 中不要保存完整邮箱明文；如需要可保存 hash。
5. 限流错误统一返回 429，并写审计事件。

## Phase 3: 账号资料与密码管理

1. 新建 `AccountService`。
2. 实现：
   - `get_profile(user_id)`
   - `update_profile(user_id, display_name)`
   - `change_password(user_id, old_password, new_password)`
   - `list_sessions(user_id)`
   - `revoke_session(user_id, session_id)`
   - `revoke_all_sessions(user_id, keep_current=False)`
3. 修改 `AuthService._issue_tokens()`：
   - 接收 `request` 或显式传入 user_agent/client_ip。
   - 保存到 refresh token。
4. 修改 `refresh()`：
   - 刷新成功时更新新 token 的 user_agent/client_ip。
   - 旧 token `revoked_reason="rotated"`。
5. 修改密码后：
   - 更新 password_hash。
   - 设置 `password_changed_at`。
   - 撤销全部 refresh tokens，要求重新登录。

## Phase 4: 隐私导出

1. `GET /api/account/export` 返回 JSON，不直接打包所有备份 zip。
2. 导出内容：
   - 账号 ID、email、display_name、created_at。
   - 云端项目列表。
   - 备份元数据：filename、size、checksum、created_at、uploaded_at、status。
   - 当前配额与使用量。
3. 不包含：
   - password_hash。
   - refresh token。
   - OSS AccessKey。
   - presigned URL 完整签名。
4. 如用户需要备份正文 zip，仍通过已有备份下载流程逐个下载。

## Phase 5: 两阶段删除账号和云数据

1. `POST /api/account/delete-request`
   - 需要 Bearer token。
   - 请求体包含当前密码。
   - 校验密码。
   - 统计影响范围：
     - 项目数。
     - 成功备份数。
     - 总 size。
   - 创建删除请求，返回：

```json
{
  "request_id": "uuid",
  "expires_at": "...",
  "project_count": 2,
  "backup_count": 10,
  "total_size_bytes": 12345,
  "confirmation_text": "DELETE MY CLOUD DATA"
}
```

2. `DELETE /api/account`
   - 请求体包含：

```json
{
  "request_id": "uuid",
  "confirmation_text": "DELETE MY CLOUD DATA"
}
```

   - 校验 request 未过期、未使用、属于当前用户。
   - 删除该用户所有 OSS backup objects。
   - 软删除 cloud_projects / cloud_backups。
   - 撤销 refresh tokens。
   - 匿名化 user：
     - `email = "deleted+<user_id>@deleted.local"`
     - `display_name = "已删除用户"`
     - `password_hash` 替换为随机不可登录值。
     - `is_active = False`
     - `deleted_at = now`
     - `anonymized_at = now`
3. 如果部分 OSS 删除失败：
   - 不要继续声称完全删除。
   - 将失败备份保留并标记 `pending_deletion` 或记录 error。
   - 返回 207 风格的语义不适合 FastAPI 常规 JSON，可用 500/409 并返回失败数量。
   - 审计 `account_delete_partial_failed`。

## Phase 6: 使用量和成本透明

1. 新建 `UsageService`：
   - `get_usage(user_id)`
2. 返回：

```json
{
  "storage_used_bytes": 123,
  "storage_quota_bytes": 1073741824,
  "backup_count": 5,
  "backup_count_quota": 100,
  "backup_init_used_last_hour": 2,
  "backup_init_limit_per_hour": 30,
  "max_backup_size_bytes": 524288000
}
```

3. `BackupService` 继续使用同一套 service 或 helper，避免 UI 与后端限制不一致。
4. 超限错误增加机器可读 code：
   - `storage_quota_exceeded`
   - `backup_count_quota_exceeded`
   - `backup_rate_limited`
   - `max_file_size_exceeded`

## Phase 7: 桌面端转发和 UI

1. `CloudApiClient` 增加：
   - `get_account_profile`
   - `update_account_profile`
   - `change_password`
   - `list_sessions`
   - `revoke_all_sessions`
   - `get_usage`
   - `export_account_data`
   - `request_account_deletion`
   - `confirm_account_deletion`
2. 本地 `backend/app/api/cloud.py` 增加对应 `/api/cloud/account/...` 转发接口。
3. `CloudAccountPrivacyPanel.vue`：
   - 显示邮箱、显示名。
   - 修改显示名。
   - 修改密码。
   - 退出全部设备。
   - 导出云端账号数据。
   - 删除云端账号按钮放在危险区域，二次确认。
4. `CloudUsagePanel.vue`：
   - 展示存储已用/上限。
   - 展示备份数量/上限。
   - 展示每小时上传限制。
   - 在云备份面板里给出轻量摘要。
5. 删除账号成功后：
   - 清空本地 cloud token。
   - UI 进入未登录状态。
   - 不删除本地作品数据。

## Phase 8: 隐私说明文档

1. 新建 `cloud-server/docs/PRIVACY_AND_ACCOUNT.md`。
2. 内容包括：
   - 章枢本地优先：本地作品不因退出云账户而删除。
   - 云端保存哪些数据：账号邮箱、显示名、云项目、备份 zip、备份元数据、审计日志。
   - 云端不保存哪些数据：本地未启用云备份的作品、用户本机 AI Key、OSS AccessKey。
   - 如何导出云数据。
   - 如何删除云账号和备份。
   - 备份删除和日志保留的边界。
3. 前端设置里用简短文案链接到隐私说明，不要塞长文。

## Phase 9: 测试

1. `test_account_api.py`
   - 获取 profile。
   - 修改 display_name。
   - 修改密码后旧 refresh token 失效。
   - revoke all sessions 后 refresh 失败。
2. `test_account_deletion.py`
   - 删除请求需要密码。
   - 确认文本错误不能删除。
   - 删除成功后用户不可登录。
   - 删除成功后 tokens revoked。
   - OSS delete 被调用。
   - 部分 OSS 删除失败返回错误且不匿名化为完全成功状态。
3. `test_usage_api.py`
   - usage 返回存储、数量、频率限制。
   - 多项目聚合正确。
4. `test_db_rate_limit.py`
   - 登录限流跨 service 实例生效。
   - 注册限流不保存完整邮箱明文。
   - 备份 init 限流返回 429。
5. `backend/tests/test_cloud_account_proxy_api.py`
   - 本地转发 API 正常调用 CloudApiClient。
   - 删除账号成功后清理本地 token。
6. 前端至少运行 type-check；如已有测试基础，再补组件渲染测试。

# Constraints

- 不要实现计费系统、支付、会员等级或管理后台。
- 不要强制用户登录；云功能仍然是可选增强。
- 删除云账号不得删除用户本地作品数据。
- 导出数据不得包含 password_hash、refresh token、OSS AccessKey、完整 presigned URL。
- 日志和审计继续只记录脱敏信息。
- 不要把完整邮箱作为 rate limit key 明文存储；使用 hash 或 domain。
- 不要破坏现有 12 个云 API 契约。
- 新增接口必须独立在 `/api/account/...` 或本地 `/api/cloud/account/...` 下。
- 账号删除必须有二次确认，不能一键误删。
- 如果 OSS 删除失败，不要声称用户数据已完全删除。

# Verification Commands

## 云服务端

```powershell
cd F:\zhangshu\cloud-server
pytest -q
pytest tests/test_account_api.py -q
pytest tests/test_account_deletion.py -q
pytest tests/test_usage_api.py -q
pytest tests/test_db_rate_limit.py -q
python -c "from app.main import app; print(app.title)"
```

## 桌面端后端

```powershell
cd F:\zhangshu\backend
pytest tests/test_cloud_api.py -q
pytest tests/test_cloud_account_proxy_api.py -q
python -c "from app.main import app; print('ok')"
```

## 前端

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run build
```

## 手动验收

1. 注册云账号并登录。
2. 查看云使用量。
3. 上传一次云备份，确认使用量增加。
4. 导出账号数据，确认不包含密码 hash、token、OSS 签名 URL。
5. 修改密码，确认旧 refresh token 失效。
6. 退出全部设备，确认当前或其他会话不能继续 refresh。
7. 发起删除账号请求，确认二次确认文案清晰。
8. 删除云账号后，确认本地作品仍存在，云账户状态变为未登录。

# Acceptance Criteria

- 用户可以查看和修改云账户显示名。
- 用户可以修改密码，修改后旧 refresh token 失效。
- 用户可以退出全部设备。
- 用户可以查看云备份使用量和配额。
- 用户可以导出云账户元数据，且导出内容不含敏感凭证。
- 用户可以通过两阶段确认删除云账号和云端备份数据。
- 删除账号不会删除本地作品数据。
- 数据库级限流替代或覆盖 in-process auth rate limit。
- 注册、登录、备份 init 都有可跨 worker 生效的滥用防护。
- 备份配额和频率限制对用户可见，错误提示可理解。
- 所有新增测试通过。
- Claude 执行报告列出任何未能真实验证的 OSS 删除/多设备场景。

# Risks and Watchpoints

- 账号删除涉及 OSS 对象删除，必须避免“数据库删了但 OSS 留着”的静默失败。
- 导出账号数据如果包含 presigned URL，可能泄露临时访问能力；V1 不应包含。
- 修改密码后是否保留当前会话需要产品取舍；本计划建议撤销全部 refresh token，要求重新登录。
- 数据库限流表如果不清理会增长，需要清理过期事件。
- 使用 email hash 做限流 key 时要避免可逆或泄露完整邮箱。
- 账号匿名化后 email unique 约束要继续满足。
- 两阶段删除请求如果持久化 confirm token，必须保存 hash，不保存明文 token。
- 前端危险操作必须有清晰二次确认，避免误删。

# Review Checklist

- [ ] 是否已归档上一轮生产级基线计划和执行报告？
- [ ] 是否没有修改无关小说业务模块？
- [ ] 是否新增账号资料、密码修改、会话管理、导出、删除能力？
- [ ] 删除账号是否两阶段确认？
- [ ] 删除账号是否不会影响本地作品数据？
- [ ] OSS 删除失败是否不会被误报为完全成功？
- [ ] 导出数据是否不包含 password_hash、token、OSS AccessKey、完整 presigned URL？
- [ ] refresh token 是否记录基本会话信息且可撤销？
- [ ] 修改密码后旧 token 是否失效？
- [ ] 是否用数据库级限流替代或覆盖 in-process 限流？
- [ ] 限流 key 是否避免明文完整邮箱？
- [ ] 用户是否能看到自己的使用量和配额？
- [ ] 配额、频率限制、删除流程是否有测试？
- [ ] 前端危险操作文案是否足够明确？
- [ ] Claude 执行报告是否包含验证命令结果和未验证风险？
