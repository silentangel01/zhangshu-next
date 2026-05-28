---
date: 2026-05-28
task: Admin 系统全面升级（高优先级 + 中优先级，共 10 步）
codex_plan: 基于会话中生成的计划（plan file: toasty-churning-piglet.md）
---

## Task Summary

按高优先级（Steps 1-5）→ 中优先级（Steps 6-10）的顺序完成了 cloud-server 后端和 cloud-admin 前端的全面升级，涵盖测试修复、Toast 通知、分页、Token 续期、lifespan 迁移、审计日志入库、用户管理操作、全局搜索和部署配置。

## Files Changed

### 新建（14 个文件）
- `cloud-server/tests/test_admin_auth.py` — 8 个 admin auth 端点测试
- `cloud-server/tests/test_admin_dashboard.py` — 5 个 dashboard 端点测试
- `cloud-server/tests/test_admin_users.py` — 6 个用户管理端点测试
- `cloud-server/tests/test_admin_monitoring.py` — 4 个监控端点测试（mock 阿里云 API）
- `cloud-server/app/models/audit_log.py` — AuditLog ORM 模型
- `cloud-server/alembic/versions/006_audit_log.py` — 数据库迁移
- `cloud-server/app/api/admin_audit.py` — GET /api/admin/audit 端点
- `cloud-server/app/api/admin_search.py` — GET /api/admin/search 全局搜索端点
- `cloud-admin/src/shared/composables/useToast.ts` — 模块级 reactive Toast 单例
- `cloud-admin/src/shared/ui/ToastContainer.vue` — Toast 容器组件
- `cloud-admin/src/entities/admin-audit/types.ts` — 审计日志类型定义
- `cloud-admin/src/entities/admin-audit/api.ts` — 审计日志 API
- `cloud-server/deploy/nginx/cloud-admin.conf` — Nginx 部署配置
- `docs/CLOUD_ADMIN_DEPLOY.md` — 部署文档

### 修改（~20 个文件）
- `cloud-server/app/models/__init__.py` — 导出 FeedbackReply + AuditLog
- `cloud-server/tests/conftest.py` — 添加 feedback_reply、user_activity_event、audit_log 模型导入
- `cloud-server/tests/test_admin_feedback.py` — create_access_token → create_admin_access_token
- `cloud-server/tests/test_admin_announcements.py` — 同上 token 修复
- `cloud-server/app/main.py` — on_event("startup") → lifespan；注册 audit/search routers
- `cloud-server/app/core/audit.py` — 添加 db 参数，支持 DB 持久化
- `cloud-server/app/api/admin_auth.py` — audit_event 传 db=db
- `cloud-server/app/api/admin_feedback.py` — audit_event 传 db=db
- `cloud-server/app/api/admin_announcements.py` — audit_event 传 db=db
- `cloud-server/app/api/admin_users.py` — 新增 toggle-active 和 force-logout 端点
- `cloud-server/app/api/auth.py` — audit_event 传 db=db
- `cloud-server/app/api/account.py` — audit_event 传 db=db
- `cloud-server/app/api/backups.py` — audit_event 传 db=db
- `cloud-server/app/api/feedback.py` — audit_event 传 db=db
- `cloud-server/app/services/account_service.py` — audit_event 传 db=self._db
- `cloud-server/app/services/admin_user_service.py` — 新增 toggle_active、force_logout 方法
- `cloud-admin/src/components/AdminLayout.vue` — ToastContainer + Token 续期 + 全局搜索 UI
- `cloud-admin/src/components/DataTable.vue` — 分页 props + 控件
- `cloud-admin/src/entities/admin-announcement/api.ts` — 添加分页参数
- `cloud-admin/src/entities/admin-user/api.ts` — 添加 toggleUserActive、forceLogoutUser
- `cloud-admin/src/pages/DashboardPage.vue` — Toast 错误提示
- `cloud-admin/src/pages/FeedbackListPage.vue` — Toast + 分页
- `cloud-admin/src/pages/FeedbackDetailPage.vue` — Toast 错误提示
- `cloud-admin/src/pages/UsersPage.vue` — Toast + 分页
- `cloud-admin/src/pages/AnnouncementsPage.vue` — Toast + 分页
- `cloud-admin/src/pages/MonitoringPage.vue` — Toast + 审计日志面板
- `cloud-admin/src/pages/UserDetailPage.vue` — 管理操作按钮（禁用/启用、强制下线）

## Implementation Notes

1. **Token 类型不匹配修复**：admin 端点使用 `decode_token(token, "admin_access")` 验证，但旧测试用 `create_access_token()` 生成 type="access" 的 token。修复为 `create_admin_access_token()`。
2. **TestClient Cookie 处理**：TestClient 不自动发送 `secure=True` 的 cookies，需手动从 login response 提取并传入后续请求。
3. **Audit DB 持久化**：audit_event() 的 db 写入使用 try/except + rollback，确保审计失败不影响主业务。
4. **None 值安全处理**：feedback.py 匿名反馈传 `user_id=None`，DB 写入时通过 `or ""` 转换为空字符串。
5. **AdminMonitoringService 类级缓存**：测试中使用 `autouse` fixture 在每次测试前后清理 `_cache`。

## Deviations from Codex Plan

无偏差。所有 10 步均按计划完成。

## Verification Commands Run
- `cd cloud-server && .venv/Scripts/python.exe -m pytest tests/ -v` → 163 passed
- `cd cloud-admin && npm run type-check` → 零错误
- `cd cloud-admin && npm run build` → 生产构建成功（141KB JS + 22KB CSS）
- `cd cloud-server && .venv/Scripts/python.exe -c "from app.main import app; print('ok')"` → ok

## Verification Results

全部通过。163 个测试通过，前端类型检查和生产构建均无错误。

## Known Issues

1. `test_admin_auth.py` 中的 `test_refresh_success` 和 `test_me_success` 有 DeprecationWarning（TestClient per-request cookies），这是 Starlette 的 deprecation 提示，不影响功能。
2. Alembic `path_separator` deprecation warning — 来自 alembic.ini 配置，不影响迁移。
3. 审计日志迁移（006）尚未在开发数据库上执行 `alembic upgrade head`，需在部署时运行。

## Suggested Next Review Points for Codex

1. 审计日志的 `_ALLOWED_EXTRA_KEYS` 白名单是否需要扩展（当前包含 tokens_revoked、target_user_id、feedback_id、announcement_id）
2. 全局搜索的 ILIKE 查询在大量数据下的性能，是否需要全文索引
3. Nginx 配置中的 SSL 证书路径需在实际部署时替换
4. 管理员用户操作中 `toggle_active` 是否需要防止禁用最后一个管理员
