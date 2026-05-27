<!-- archived: 2026-05-26; reason: cloud production hardening completed, superseded by account privacy and abuse protection planning -->

# Task Summary

本次任务是规划“章枢云生产级改进基线”。目标不是继续扩展小说业务功能，而是把已经可用的云账号、云备份、网络诊断和部署脚本提升到更接近生产可上线的状态。

优先级顺序：

1. 安全基线：密钥、HTTPS、日志脱敏、限流、容器权限。
2. 可观测性：结构化日志、请求 ID、健康检查、错误分类、运维排查。
3. 灾备与恢复：PostgreSQL 备份验证、恢复演练文档、OSS 生命周期/版本控制建议。
4. 可靠性与成本控制：备份配额、上传频率限制、失败清理、大文件风险提示。
5. API 兼容与发布：云 API 版本化准备、部署前检查、发布回滚。

Codex 未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

- 已归档上一轮云网络韧性任务的活跃交接文件：
  - `docs/ai-handoff/archive/2026-05-26-cloud-network-resilience-completed/CODEX_PLAN.md`
  - `docs/ai-handoff/archive/2026-05-26-cloud-network-resilience-completed/CLAUDE_EXECUTION_REPORT.md`
- 云网络韧性执行报告显示：
  - 后端新增 `backend/app/infrastructure/cloud_network_diagnostics.py`、`backend/app/services/cloud_network_service.py`。
  - `CloudApiClient` 已从单一路径升级为 `auto -> secure_direct -> system_proxy -> compat_no_sni` 策略链。
  - 已加入远程 HTTP 风险判断，本地 `localhost/127.0.0.1/::1` HTTP 联调不受影响。
  - 云服务端已加入 `oss_public_endpoint / oss_internal_endpoint`。
  - 后端、云服务端、前端验证均通过。
- 当前 `cloud-server/` 已存在独立云服务端项目，包含：
  - FastAPI + SQLAlchemy + Alembic + PostgreSQL + Docker Compose。
  - `cloud-server/deploy/` 部署脚本、SSH 加固脚本、数据库备份脚本。
  - `cloud-server/deploy/README.md` 已说明 Nginx、SSL、OSS endpoint、日常运维。
- 当前发现的生产级风险点：
  - `cloud-server/.env`、`cloud-server/cloud_server.db`、`cloud-server/python-3.12.9-amd64.exe`、`cloud-server/_oss_diag.py` 是本地/临时/敏感或大文件风险，需要 Claude 检查是否被 `.gitignore` 忽略，不能提交。
  - `Dockerfile` 默认以 root 用户运行，生产容器权限可继续收紧。
  - `docker-compose.yml` 有基础 healthcheck，但云 API 本身缺少 readiness/detail health。
  - `backup-db.sh` 生成本地备份，但缺少恢复演练脚本、备份加密/异地保存说明。
  - 目前缺少统一结构化日志、请求 ID、审计事件字段规范。
  - 云端备份缺少用户配额、频率限制、失败上传清理策略。
  - 部署脚本和 README 已覆盖不少流程，但还缺少“上线前检查清单”和“回滚流程”。

# Architecture Decision

## 1. 本轮只做生产基线，不做大业务扩张

本轮不实现完整云同步、协作、会员计费、管理后台或实时任务系统。只补齐上线前最需要的生产安全、可观测性、备份恢复、配额限制和发布检查。

## 2. 云服务端优先

生产级风险主要集中在 `cloud-server/` 和部署链路。本轮以云服务端为主，桌面端只做必要的错误提示和兼容检查，不改写已有云备份主流程。

## 3. 安全和可观测性必须分层

- FastAPI middleware：请求 ID、结构化日志、安全响应头。
- Service 层：审计事件、业务错误分类。
- Deploy 层：Nginx 安全头、HTTPS、限流、备份、回滚。
- Docs 层：上线前检查、密钥轮换、恢复演练。

## 4. 先轻量实现，预留后续扩展

不引入庞大监控平台。V1 先用结构化 JSON 日志、健康检查、部署脚本和文档约束。后续再接 Prometheus、Sentry、Grafana、对象存储备份归档等。

# Files to Create or Modify

## cloud-server 应用

- 修改：`cloud-server/app/main.py`
  - 增加请求 ID middleware、安全头 middleware、结构化访问日志。
  - 增加 `/ready` 或增强 `/health`。
- 新增：`cloud-server/app/core/logging.py`
  - 统一日志格式、敏感字段脱敏、request_id 注入。
- 新增：`cloud-server/app/core/security_headers.py`
  - 安全响应头封装。
- 新增：`cloud-server/app/core/audit.py`
  - 登录、注册、备份 init/complete/delete 等审计事件记录辅助函数。
- 修改：`cloud-server/app/core/config.py`
  - 增加生产安全配置：环境名、是否强制 HTTPS、限流参数、配额参数、日志级别。
- 修改：`cloud-server/app/api/auth.py`
  - 审计登录/注册/refresh 事件。
  - 检查限流和错误日志是否脱敏。
- 修改：`cloud-server/app/api/backups.py`
  - 审计备份 init/complete/delete。
- 修改：`cloud-server/app/services/backup_service.py`
  - 增加用户配额、频率限制、失败上传清理入口。
- 修改：`cloud-server/app/models/user.py`
  - 如需要，增加 `storage_quota_bytes`、`backup_count_quota` 默认值字段。
- 修改：`cloud-server/app/models/cloud_backup.py`
  - 如需要，增加 `expires_at`、`deleted_reason` 或保留现有字段并通过 service 实现清理。
- 新增迁移：`cloud-server/alembic/versions/<timestamp>_production_hardening_fields.py`

## cloud-server 部署

- 修改：`cloud-server/Dockerfile`
  - 增加非 root 用户运行。
  - 避免把本地 `.env`、数据库、诊断脚本、安装包复制进镜像。
- 修改：`cloud-server/.dockerignore`
  - 明确忽略 `.env`、`.venv/`、`cloud_server.db`、`*.db`、`*.sqlite*`、`python-*.exe`、`_oss_diag.py`、`backups/`。
- 修改：`cloud-server/docker-compose.yml`
  - 增加 cloud-api healthcheck。
  - 可选增加日志大小限制。
- 修改：`cloud-server/deploy/deploy.sh`
  - 增加上线前检查：HTTPS、域名 DNS、`.env` 必填项、OSS public endpoint。
- 修改：`cloud-server/deploy/update.sh`
  - 增加回滚提示或保留上一个镜像 tag。
- 修改：`cloud-server/deploy/backup-db.sh`
  - 增加备份校验、可配置保留天数、可选加密说明。
- 新增：`cloud-server/deploy/restore-db.sh`
  - 明确从 `.dump` 恢复数据库的受控流程。
- 新增：`cloud-server/deploy/preflight.sh`
  - 上线前统一检查脚本。

## 文档

- 修改：`cloud-server/README.md`
  - 增加生产安全基线、日志脱敏、配额、灾备说明。
- 修改：`cloud-server/deploy/README.md`
  - 增加上线前 checklist、回滚流程、恢复演练。
- 新增：`cloud-server/docs/PRODUCTION_CHECKLIST.md`
  - 生产部署 checklist。
- 新增：`cloud-server/docs/INCIDENT_RUNBOOK.md`
  - 登录失败、备份失败、OSS 403、数据库满、磁盘满、证书过期等处置流程。
- 新增：`cloud-server/docs/DISASTER_RECOVERY.md`
  - PostgreSQL + OSS 灾备、恢复演练、RPO/RTO 建议。

## 测试

- 新增：`cloud-server/tests/test_production_config.py`
- 新增：`cloud-server/tests/test_security_headers.py`
- 新增：`cloud-server/tests/test_audit_logging.py`
- 新增：`cloud-server/tests/test_backup_quota.py`
- 新增：`cloud-server/tests/test_health_ready.py`

# Implementation Steps for Claude Code

## Phase 1: 清理提交风险和忽略规则

1. 检查 `cloud-server/.gitignore` 和 `cloud-server/.dockerignore`。
2. 确保以下文件不会进入 Git 或 Docker 镜像：
   - `cloud-server/.env`
   - `cloud-server/.venv/`
   - `cloud-server/cloud_server.db`
   - `cloud-server/*.sqlite*`
   - `cloud-server/python-*.exe`
   - `cloud-server/_oss_diag.py`
   - `cloud-server/backups/`
   - `cloud-server/.pytest_cache/`
3. 如果这些文件已经被 Git 跟踪，不要直接删除用户数据；在执行报告中标注并建议用户确认后移除跟踪。
4. 更新 `.dockerignore`，避免生产镜像复制本地敏感文件和大文件。

## Phase 2: 生产配置校验

1. 修改 `cloud-server/app/core/config.py`，增加：

```python
environment: str = "development"
force_https: bool = True
log_level: str = "INFO"
access_log_json: bool = True
rate_limit_login_per_5m: int = 10
rate_limit_backup_init_per_hour: int = 30
default_storage_quota_bytes: int = 1_073_741_824
default_backup_count_quota: int = 100
```

2. 增加配置校验函数：
   - `environment=production` 时 `JWT_SECRET_KEY` 不能是默认值。
   - `environment=production` 时 `CORS_ORIGINS` 不能为 `*`。
   - `environment=production` 时远程云服务必须经 HTTPS 反代暴露。
   - `OSS_PUBLIC_ENDPOINT` 不能包含 `-internal.aliyuncs.com`。
3. 在 app startup 或 preflight 中执行校验，生产配置不合格时明确失败。

## Phase 3: 结构化日志和请求 ID

1. 新建 `cloud-server/app/core/logging.py`。
2. 实现：
   - `configure_logging(settings)`
   - `redact_sensitive(value)`
   - `safe_log_extra(extra)`
3. 修改 `cloud-server/app/main.py`：
   - 每个请求生成或读取 `X-Request-ID`。
   - 响应头返回 `X-Request-ID`。
   - 记录结构化访问日志：method、path、status_code、duration_ms、request_id、client_ip。
   - 不记录 query 中的 token、presigned URL、Authorization。
4. 业务错误日志只记录错误类别，不记录用户密码、JWT、refresh token、OSS 签名 URL。

## Phase 4: 安全响应头和 HTTPS 反代文档

1. 新建 `cloud-server/app/core/security_headers.py`。
2. 在 FastAPI middleware 中加入：
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `Referrer-Policy: no-referrer`
   - `Cache-Control: no-store`，至少对认证相关响应生效。
3. Nginx 侧在 `deploy/README.md` 中补充：
   - HSTS 只在 HTTPS 确认稳定后启用。
   - TLS 证书续期检查命令。
   - 禁止生产 HTTP 明文访问 API。

## Phase 5: 审计事件

1. 新建 `cloud-server/app/core/audit.py`。
2. 实现轻量审计日志，不新增数据库表，先写结构化日志：
   - `user_registered`
   - `login_success`
   - `login_failed`
   - `token_refreshed`
   - `cloud_project_created`
   - `backup_init`
   - `backup_complete`
   - `backup_deleted`
   - `backup_failed`
3. 审计字段：
   - `event`
   - `user_id`，可为空
   - `project_id`，可为空
   - `backup_id`，可为空
   - `request_id`
   - `client_ip`
   - `result`
   - `reason_code`
4. 不记录密码、token、OSS 完整 URL。

## Phase 6: 配额、频率限制和失败清理

1. 在 `BackupService.init_upload()` 前增加配额检查：
   - 单用户总备份大小不得超过 `default_storage_quota_bytes`。
   - 单用户成功备份数量不得超过 `default_backup_count_quota`。
   - 每小时 backup init 次数不得超过 `rate_limit_backup_init_per_hour`。
2. 如暂不新增 Redis，V1 可用数据库查询实现：
   - 最近一小时 `CloudBackup.created_at` 计数。
   - 当前用户所有 success 备份 `size_bytes` 总和。
3. 超限返回明确错误：
   - `{"detail": "云备份空间已达上限，请删除旧备份后重试。"}`
4. 增加清理函数：
   - 将超时 `uploading` 记录标为 `failed`。
   - 不自动删除 OSS 对象，除非能确认 object_key 存在且属于该用户。
5. README 说明后续可升级为后台定时任务。

## Phase 7: 健康检查和 readiness

1. 保留 `/health` 作为轻量存活检查。
2. 新增 `/ready`：
   - 检查数据库连接。
   - 检查 Alembic 版本是否可读取。
   - 可选检查 OSS 配置是否存在，但不要真实上传文件。
3. Docker Compose healthcheck 改为调用 `/ready` 或保留 `/health` 并在 deploy preflight 中调用 `/ready`。
4. 部署脚本中加入：

```bash
curl -fsS http://127.0.0.1:9000/ready
curl -fsS https://${ZHANGSHU_DOMAIN}/health
```

## Phase 8: 灾备与恢复

1. 改进 `deploy/backup-db.sh`：
   - 保留 `.dump` 格式。
   - 输出 SHA256 校验文件。
   - 支持 `KEEP_DAYS` 环境变量。
   - 明确不要把备份目录提交。
2. 新增 `deploy/restore-db.sh`：
   - 要求用户显式输入 `RESTORE_CONFIRM=yes`。
   - 恢复前自动生成当前数据库备份。
   - 使用 `pg_restore --clean --if-exists`。
3. 新增 `cloud-server/docs/DISASTER_RECOVERY.md`：
   - RPO：建议 24 小时以内。
   - RTO：小规模部署建议 2 小时以内。
   - 每月至少做一次恢复演练。
   - OSS 建议开启版本控制和生命周期规则。
   - 高级灾备可启用 OSS 跨区域复制。

## Phase 9: 部署 preflight 和回滚

1. 新增 `deploy/preflight.sh` 检查：
   - `.env` 必填项是否存在。
   - `JWT_SECRET_KEY` 非默认。
   - `OSS_PUBLIC_ENDPOINT` 非 internal。
   - Docker Compose 配置可解析。
   - 数据库可连接。
   - HTTPS health 可访问。
   - 磁盘空间大于阈值，例如剩余 1GB。
2. 修改 `deploy/update.sh`：
   - 更新前记录当前镜像 ID。
   - 迁移前执行数据库备份。
   - 更新失败时输出回滚命令。
3. 文档中写清回滚步骤，不要求全自动回滚。

## Phase 10: 文档收束

1. `cloud-server/docs/PRODUCTION_CHECKLIST.md` 必须包含：
   - HTTPS 和证书续期。
   - `.env` 密钥检查。
   - OSS public/internal endpoint。
   - CORS origins。
   - 数据库备份和恢复演练。
   - 磁盘和日志空间。
   - 云备份配额。
   - 是否已运行测试。
2. `cloud-server/docs/INCIDENT_RUNBOOK.md` 必须包含：
   - 用户无法登录。
   - 云备份上传失败。
   - OSS 403。
   - 数据库连接失败。
   - 磁盘满。
   - 证书过期。
   - 网络诊断显示 SNI 过滤。
3. `cloud-server/README.md` 只保留高层入口，把长篇运维内容链接到 docs。

# Constraints

- 不要实现管理后台、计费系统、实时同步或多人协作。
- 不要破坏现有桌面端云 API 契约。
- 不要在日志中记录密码、JWT、refresh token、OSS AccessKey、完整 presigned URL。
- 不要把 `.env`、本地 SQLite、Python 安装包、诊断临时脚本、数据库备份加入 Git 或 Docker 镜像。
- 不要引入大型监控平台依赖；V1 用结构化日志、health/readiness 和文档化 runbook。
- 不要在生产中允许远程 HTTP 明文云 API。
- 不要让生产配置校验影响本地开发：`environment=development` 时允许 SQLite、localhost HTTP、默认轻量配置。
- 如果涉及数据库迁移，必须提供 Alembic 迁移和测试。

# Verification Commands

## 云服务端

```powershell
cd F:\zhangshu\cloud-server
pytest -q
python -c "from app.main import app; print(app.title)"
docker compose config
```

## 指定测试

```powershell
cd F:\zhangshu\cloud-server
pytest tests/test_production_config.py -q
pytest tests/test_security_headers.py -q
pytest tests/test_audit_logging.py -q
pytest tests/test_backup_quota.py -q
pytest tests/test_health_ready.py -q
```

## 部署脚本静态检查

```powershell
cd F:\zhangshu\cloud-server
bash -n deploy/preflight.sh
bash -n deploy/backup-db.sh
bash -n deploy/restore-db.sh
bash -n deploy/update.sh
```

如果 Windows 环境没有 bash，Claude Code 应在执行报告中说明，并至少人工检查脚本语法。

## 本地 Docker 烟测

```powershell
cd F:\zhangshu\cloud-server
docker compose up --build
```

另开终端：

```powershell
Invoke-RestMethod http://127.0.0.1:9000/health
Invoke-RestMethod http://127.0.0.1:9000/ready
```

## Git 风险检查

```powershell
cd F:\zhangshu
git status --short
git diff --stat
```

重点确认没有以下内容被提交：

- `cloud-server/.env`
- `cloud-server/cloud_server.db`
- `cloud-server/python-*.exe`
- `cloud-server/_oss_diag.py`
- `cloud-server/backups/`
- `data/`
- `logs/`

# Acceptance Criteria

- `cloud-server` 生产配置可校验，生产环境默认拒绝明显危险配置。
- 生产远程云 API 不允许 HTTP 明文；本地开发 HTTP 不受影响。
- API 响应带 `X-Request-ID`，日志中可按 request_id 串起一次请求。
- 登录、注册、备份相关关键动作有脱敏审计事件。
- 安全响应头已加入，认证相关响应不被缓存。
- 云备份有基础配额和频率限制。
- 超时上传记录可被标记失败或有清理入口。
- `/health` 和 `/ready` 可用，部署脚本可使用它们做健康检查。
- PostgreSQL 备份脚本有校验，恢复脚本有确认保护。
- 文档包含生产 checklist、事故 runbook、灾备恢复说明。
- Docker 镜像不复制 `.env`、数据库、本地安装包、临时诊断脚本。
- 所有新增测试通过，或执行报告说明无法运行的具体环境原因。

# Risks and Watchpoints

- 配额限制若实现过严，可能误伤正常用户；默认值应宽松，并在错误提示中说明处理方式。
- 审计日志必须脱敏，否则生产日志反而成为敏感信息泄露点。
- `restore-db.sh` 是高风险脚本，必须有显式确认和恢复前自动备份。
- Docker 非 root 用户可能影响文件权限，需确认 Alembic、日志和运行目录可写。
- `/ready` 不应做昂贵 OSS 操作，避免健康检查本身造成故障。
- 如果新增字段迁移，要兼容已有云服务端数据库。
- 日志大小限制要避免把关键错误吞掉；建议 Docker log rotation 而不是关闭日志。
- 本轮不要把任务扩张到完整管理后台，否则会拖慢生产基线落地。

# Review Checklist

- [ ] 是否只做生产基线，没有扩张到无关业务功能？
- [ ] 是否没有破坏现有云 API 契约？
- [ ] `.env`、本地数据库、Python 安装包、临时诊断脚本是否未被提交？
- [ ] Docker 镜像是否不会复制敏感/临时/大文件？
- [ ] 生产配置校验是否能拦截默认 JWT_SECRET_KEY、远程 HTTP、internal OSS public endpoint？
- [ ] 本地开发配置是否仍然可用？
- [ ] 请求 ID 是否贯穿响应和日志？
- [ ] 审计日志是否覆盖登录、注册、备份关键事件？
- [ ] 日志是否脱敏？
- [ ] 安全响应头是否生效？
- [ ] 备份配额和频率限制是否有测试？
- [ ] `/health` 与 `/ready` 是否职责清晰？
- [ ] 数据库备份与恢复脚本是否有保护措施？
- [ ] 文档是否包含上线前 checklist、事故 runbook、灾备恢复？
- [ ] 测试命令和构建命令是否通过？
- [ ] Claude 执行报告是否列出无法本地验证的生产环境检查项？
