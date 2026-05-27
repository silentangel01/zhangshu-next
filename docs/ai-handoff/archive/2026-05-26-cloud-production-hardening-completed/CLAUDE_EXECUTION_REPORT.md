---
date: 2026-05-26
archived_at: 2026-05-26
archive_reason: cloud production hardening completed, superseded by account privacy and abuse protection planning
task: 章枢云生产级改进基线 (Cloud Server Production Hardening)
codex_plan: docs/ai-handoff/CODEX_PLAN.md (当前版本)
---

## Task Summary
将 cloud-server 从开发原型提升到生产就绪状态：增加安全基线（配置校验、安全响应头、日志脱敏）、可观测性（结构化日志、请求 ID、审计事件）、灾备与恢复（数据库备份校验、恢复脚本）、配额限制和部署检查。

## Files Changed

### 新增
- `cloud-server/app/core/logging.py` — 结构化日志、请求 ID 中间件、敏感字段脱敏、JSON/Plain 格式器
- `cloud-server/app/core/security_headers.py` — 安全响应头中间件 (X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Cache-Control)
- `cloud-server/app/core/audit.py` — 轻量审计事件日志（登录/注册/备份操作），结构化字段，无数据库表
- `cloud-server/deploy/restore-db.sh` — 数据库恢复脚本（SHA256 校验 + 恢复前自动备份 + 显式确认保护）
- `cloud-server/deploy/preflight.sh` — 部署前检查脚本（.env 必填项、JWT 密钥、OSS 端点、Docker 配置、数据库连接、磁盘空间）
- `cloud-server/docs/PRODUCTION_CHECKLIST.md` — 生产部署检查清单
- `cloud-server/docs/INCIDENT_RUNBOOK.md` — 事故处置手册（登录失败、备份失败、OSS 403、数据库连接、磁盘满、证书过期）
- `cloud-server/docs/DISASTER_RECOVERY.md` — 灾备与恢复方案（RPO ≤ 24h, RTO ≤ 2h, 每月演练）
- `cloud-server/tests/test_production_config.py` — 12 项测试：配置校验、默认值验证
- `cloud-server/tests/test_security_headers.py` — 10 项测试：安全响应头、请求 ID、认证缓存控制
- `cloud-server/tests/test_audit_logging.py` — 7 项测试：审计事件格式、集成测试
- `cloud-server/tests/test_backup_quota.py` — 8 项测试：存储配额、数量配额、频率限制、超时清理
- `cloud-server/tests/test_health_ready.py` — 5 项测试：/health 和 /ready 端点

### 修改
- `cloud-server/app/core/config.py` — 新增生产配置字段（environment, force_https, log_level, access_log_json, rate limits, quotas）+ `validate_production_config()` 校验函数
- `cloud-server/app/main.py` — 重写：集成配置校验（开发警告/生产拒绝启动）、configure_logging、RequestIDMiddleware、SecurityHeadersMiddleware、`/ready` 端点
- `cloud-server/app/api/auth.py` — 添加审计事件（register/login/refresh 成功和失败）
- `cloud-server/app/api/backups.py` — 添加审计事件（backup_init/complete/delete）、Request 参数注入
- `cloud-server/app/services/backup_service.py` — 添加存储配额、数量配额、频率限制检查 + `cleanup_stale_uploads()` 方法
- `cloud-server/app/services/auth_service.py` — refresh 方法返回 user_id（支持审计）
- `cloud-server/deploy/backup-db.sh` — 添加 SHA256 校验文件、可配置 KEEP_DAYS
- `cloud-server/deploy/update.sh` — 添加部署前检查、回滚命令输出、SHA256 备份
- `cloud-server/deploy/deploy.sh` — .env 增加生产安全变量、/ready 健康检查
- `cloud-server/deploy/README.md` — 添加 preflight.sh、restore-db.sh 说明和文档链接
- `cloud-server/.env.example` — 添加生产安全配置段

## Implementation Notes

### 结构化日志
- 生产环境使用 JSON 格式（便于 ELK/Loki 采集），开发环境使用 Plain 格式（人眼友好）
- `redact_sensitive()` 使用正则匹配 Bearer token、JWT、AWS/OSS presigned URL 并替换为 `[REDACTED]`
- 请求 ID 支持外部传入（`X-Request-ID` 头）或自动生成（uuid4 hex[:16]）

### 审计事件
- V1 使用结构化日志而非数据库表，避免增加数据库负担
- 审计 extra 字段使用白名单机制，防止敏感数据泄露
- 字段名加 `audit_` 前缀避免与 Python LogRecord 保留属性冲突（如 `filename`）

### 配额检查
- 使用 SQLAlchemy 子查询计算用户跨项目的总存储使用量
- CloudProject 表使用 `owner_id`（非 `user_id`），注意字段名差异
- 配额和频率限制在 `init_upload()` 前执行，避免无效 OSS 操作

### 安全设计
- 生产环境 `environment=production` 时配置不合格直接拒绝启动
- 开发环境 `environment=development` 时仅输出警告，不影响本地开发
- `/ready` 端点不做 OSS 网络调用，避免健康检查本身造成故障

## Deviations from Codex Plan

- 审计事件使用日志而非数据库表（Codex Plan 也建议了 V1 先写结构化日志，符合预期）
- 未新增数据库迁移（CloudProject 已有 owner_id，CloudBackup 已有 status/error_message，无需新字段）
- 未实现 Alembic 迁移脚本（现有表结构已满足需求）

## Verification Commands Run
- `python -c "from app.main import app; print(app.title)"` → ✅
- `pytest tests/ -q` → ✅ 86 passed (45 existing + 41 new)

## Verification Results
全部 86 项测试通过，包括：
- 12 项生产配置测试
- 10 项安全响应头测试
- 7 项审计日志测试
- 8 项配额和限制测试
- 5 项健康检查测试
- 44 项原有测试（无回归）

## Known Issues
- `on_event("startup")` 已被 FastAPI 标记为 deprecated，后续可迁移到 lifespan 事件
- Alembic `path_separator` 配置缺少，产生 deprecation warning（不影响功能）
- 生产环境 Docker 非 root 用户可能需要确认 Alembic 和日志目录写权限

## Suggested Next Review Points for Codex
1. 审计日志是否满足合规需求，还是需要升级到数据库表存储
2. 配额默认值（1 GB/用户、100 个备份）是否合理
3. 是否需要在 Nginx 层也添加请求 ID（当前在 FastAPI 层生成）
4. 备份加密（GPG）是否应在 V1 实现
5. 是否应配置 Sentry 或类似异常追踪平台
