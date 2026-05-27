---
date: 2026-05-26
archived_at: 2026-05-26
archive_reason: cloud account privacy and abuse protection task completed
task: 章枢云账户与隐私 + 成本和滥用防护
codex_plan: docs/ai-handoff/CODEX_PLAN.md (current version)
---

## Task Summary

实现"章枢云账户与隐私 + 成本和滥用防护"功能，包括：用户自助账号管理（查看、修改、导出、删除）、两阶段安全删除账号、数据库级限流替代内存限流、用户可见的使用量和配额展示、桌面端代理转发和前端 UI。

## Files Changed

### cloud-server 模型与迁移
- 修改：`cloud-server/app/models/user.py` — 增加 deleted_at, deletion_requested_at, anonymized_at, privacy_version_accepted, password_changed_at
- 修改：`cloud-server/app/models/refresh_token.py` — 增加 user_agent, client_ip, last_used_at, revoked_reason
- 新增：`cloud-server/app/models/rate_limit_event.py` — 数据库级限流事件表
- 新增：`cloud-server/app/models/account_deletion_request.py` — 两阶段删除请求表
- 新增：`cloud-server/alembic/versions/002_account_privacy.py` — Alembic 迁移

### cloud-server Repository / Service
- 修改：`cloud-server/app/repositories/refresh_token_repo.py` — revoke() 增加 reason 参数
- 新增：`cloud-server/app/repositories/rate_limit_repo.py` — 限流事件数据访问
- 新增：`cloud-server/app/services/account_service.py` — 账号资料、密码、会话、导出、删除
- 新增：`cloud-server/app/services/usage_service.py` — 使用量和配额计算
- 新增：`cloud-server/app/services/rate_limit_service.py` — 数据库级限流服务
- 修改：`cloud-server/app/services/auth_service.py` — 记录 user_agent/client_ip、阻止已删除用户登录

### cloud-server API / Schema
- 新增：`cloud-server/app/schemas/account.py` — 账号管理 Pydantic schemas
- 新增：`cloud-server/app/schemas/usage.py` — 使用量 Pydantic schema
- 新增：`cloud-server/app/api/account.py` — /api/account/* 路由
- 修改：`cloud-server/app/main.py` — include account_router
- 修改：`cloud-server/app/api/auth.py` — 替换 in-process rate limit 为 DB rate limit

### 桌面端后端
- 修改：`backend/app/infrastructure/cloud_api_client.py` — 增加 9 个账号/隐私/使用量方法
- 修改：`backend/app/api/cloud.py` — 增加 8 个本地转发 API
- 修改：`backend/app/schemas/cloud.py` — 增加对应 schema
- 修改：`backend/app/services/cloud_auth_service.py` — 增加 8 个代理方法

### 桌面端前端
- 修改：`frontend/src/entities/cloud/types.ts` — 增加 account profile、usage、session、export/delete 类型
- 修改：`frontend/src/entities/cloud/api.ts` — 增加账号隐私和使用量 API 封装
- 新增：`frontend/src/features/cloud/CloudAccountPrivacyPanel.vue` — 账号管理组件
- 新增：`frontend/src/features/cloud/CloudUsagePanel.vue` — 使用量展示组件
- 修改：`frontend/src/features/app-config/AppSettingsDialog.vue` — 增加账户与隐私、使用量入口

### 文档
- 新增：`cloud-server/docs/PRIVACY_AND_ACCOUNT.md` — 隐私和账户说明
- 修改：`cloud-server/docs/INCIDENT_RUNBOOK.md` — 增加滥用、配额耗尽、账号删除失败处置

### 测试
- 新增：`cloud-server/tests/test_account_api.py` — 9 个账号 API 测试
- 新增：`cloud-server/tests/test_account_deletion.py` — 7 个删除测试
- 新增：`cloud-server/tests/test_usage_api.py` — 3 个使用量测试
- 新增：`cloud-server/tests/test_db_rate_limit.py` — 4 个限流测试
- 新增：`backend/tests/test_cloud_account_proxy_api.py` — 11 个代理 API 测试

## Implementation Notes

### 两阶段删除
- POST /delete-request 需要密码验证，返回 request_id 和影响范围
- DELETE /account 需要 request_id + 确认文本 "DELETE MY CLOUD DATA"
- confirm_token 哈希存储在 account_deletion_requests 表
- 删除后用户匿名化：email 变为 "deleted+{user_id}@deleted.local"

### 数据库级限流
- rate_limit_events 表：scope, key (SHA-256 hash), expires_at
- 限流 key 不包含完整邮箱明文，使用 hash
- 登录限流 key: hash(client_ip + normalized_email)
- 注册限流 key: hash(client_ip + email_domain)
- 备份限流仍由 BackupService 内部实现（基于 cloud_backups 记录计数）

### 会话跟踪
- RefreshToken 增加 user_agent, client_ip, last_used_at
- 修改密码后撤销全部 refresh tokens
- 撤销全部会话后本地自动退出

### 桌面端代理
- CloudAuthService 增加 8 个代理方法，调用 CloudApiClient 对应方法
- 破坏性操作（密码修改、撤销全部会话、删除账号）后自动调用 logout()
- 错误通过 CloudAuthError 传递，包含 error_kind 和 suggestion

### 前端
- CloudAccountPrivacyPanel: 显示邮箱/显示名、修改密码、退出全部设备、导出、删除账号
- CloudUsagePanel: 存储/备份数量/频率限制的使用量进度条
- AppSettingsDialog: 仅在登录状态下显示使用量和账户隐私面板
- 删除账号后 emit logged-out 事件，刷新云账户状态

## Deviations from Codex Plan

无偏差。

## Verification Commands Run

- `cloud-server: pytest -q` → ✅ 109 passed (86 existing + 23 new)
- `cloud-server: pytest tests/test_account_api.py` → ✅ 9 passed
- `cloud-server: pytest tests/test_account_deletion.py` → ✅ 7 passed
- `cloud-server: pytest tests/test_usage_api.py` → ✅ 3 passed
- `cloud-server: pytest tests/test_db_rate_limit.py` → ✅ 4 passed
- `backend: pytest tests/test_cloud_account_proxy_api.py` → ✅ 11 passed
- `backend: pytest tests/test_cloud_api.py` → ✅ 14 passed
- `backend: pytest tests/test_cloud_backup_service.py` → ✅ 8 passed
- `backend: python -c "from app.main import app; print('ok')"` → ✅ ok
- `frontend: npm run type-check` → ✅ passed
- `frontend: npm run build` → ✅ passed

## Verification Results

全部通过。

## Known Issues

1. **备份限流测试简化**：备份 init 限流测试未实际触发 429（需要创建 30+ 备份记录），仅验证了端点可访问。备份服务使用自己的限流逻辑（基于 cloud_backups 表），未迁移到 RateLimitService。

2. **OSS 删除场景未真实验证**：账号删除中的 OSS 对象删除在测试中使用 mock，生产环境的 OSS 部分删除失败场景需要真实环境验证。

3. **多设备场景未真实验证**：修改密码后旧 token 失效、退出全部设备等场景在测试中验证了 token 撤销逻辑，但真实的多设备并发场景需要集成测试。

## Suggested Next Review Points for Codex

1. 备份限流是否应该统一迁移到 RateLimitService，保持限流逻辑一致性？
2. 账号删除时 OSS 部分失败的处理策略是否需要更细粒度的重试机制？
3. 使用量 API 返回的配额目前是全局默认值，是否需要支持用户级别的配额配置？
4. 前端删除账号的二次确认文案是否需要进一步用户测试？
5. rate_limit_events 表的清理策略：当前依赖 expires_at，是否需要定期 purge job？
