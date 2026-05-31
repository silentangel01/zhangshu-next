# 生产部署检查清单

部署到生产环境前，逐项确认以下内容。

## 基础设施

- [ ] 服务器已安装 Docker 和 Docker Compose
- [ ] 已配置防火墙（仅开放 22/80/443）
- [ ] SSH 已加固（禁用密码登录、使用密钥认证）
- [ ] 磁盘剩余空间 > 2 GB
- [ ] 已配置时区同步（NTP/chrony）

## HTTPS 和证书

- [ ] 域名 DNS 已解析到服务器 IP
- [ ] SSL 证书已签发（Let's Encrypt 或其他 CA）
- [ ] 证书自动续期已配置（certbot timer 或 cron）
- [ ] `https://${DOMAIN}/health` 可正常访问
- [ ] HTTP 自动跳转 HTTPS

## 环境配置 (.env)

- [ ] `DATABASE_URL` 指向 PostgreSQL（非 SQLite）
- [ ] `JWT_SECRET_KEY` 已设置为随机密钥（≥32 字符）
- [ ] `JWT_SECRET_KEY` 不是默认值 `change-me-in-production`
- [ ] `CORS_ORIGINS` 指定了具体域名（非通配符 `*`）
- [ ] `BCRYPT_ROUNDS` ≥ 12
- [ ] `ENVIRONMENT` 设置为 `production`
- [ ] `ADMIN_REQUIRE_ORIGIN_CHECK` 设置为 `true`（启用 CSRF 防护）
- [ ] `ADMIN_ALLOW_BEARER_FALLBACK` 设置为 `false`（禁止 Bearer token 回退）

## 阿里云 OSS

- [ ] `OSS_ACCESS_KEY_ID` 已填写
- [ ] `OSS_ACCESS_KEY_SECRET` 已填写
- [ ] `OSS_BUCKET_NAME` 已创建
- [ ] `OSS_ENDPOINT` 已设置
- [ ] `OSS_PUBLIC_ENDPOINT` 使用公网地址（不含 `-internal`）
- [ ] `OSS_INTERNAL_ENDPOINT` 使用内网地址（服务端操作加速）
- [ ] 手动测试过 presigned URL 上传和下载

## 数据库

- [ ] PostgreSQL 容器运行正常
- [ ] `pg_isready` 检查通过
- [ ] `DATABASE_URL` 指向 PostgreSQL（非 SQLite）
- [ ] Alembic 迁移已执行（`alembic upgrade head`）
- [ ] 已执行过至少一次数据库备份
- [ ] 已执行过至少一次恢复演练

## Redis

- [ ] `REDIS_ENABLED` 设置为 `true`
- [ ] Redis 容器运行正常（`redis-cli ping` → PONG）
- [ ] `RATE_LIMIT_BACKEND` 设置为 `redis`
- [ ] `CACHE_BACKEND` 设置为 `redis`
- [ ] `AUDIT_ASYNC_ENABLED` 设置为 `true`（审计异步入队）
- [ ] audit-worker 容器运行正常
- [ ] `/ready` 端点中 Redis 状态为 `ok`

## 连接池和 Worker

- [ ] `API_WORKERS` 已根据 CPU 核心数设置（2v → 2, 4v → 4）
- [ ] `DATABASE_POOL_SIZE` 和 `DATABASE_MAX_OVERFLOW` 已设置
- [ ] 连接池公式安全：`workers × (pool + overflow) ≤ max_connections × 0.8`
- [ ] `DATABASE_CONNECT_TIMEOUT_SECONDS` 已设置（默认 5s）
- [ ] `DATABASE_STATEMENT_TIMEOUT_MS` 已设置（默认 5000ms）
- [ ] `DATABASE_POOL_RECYCLE_SECONDS` 已设置（默认 1800s）

## Nginx 限流

- [ ] `/etc/nginx/conf.d/rate-limits.conf` 已安装
- [ ] 站点配置包含 `limit_req` 规则
- [ ] `/api/auth/login` 使用 `api_auth` 限流区（5r/min）
- [ ] `/api/admin/` 使用 `api_admin` 限流区（60r/min）
- [ ] `/api/feedback` 使用 `api_feedback` 限流区（20r/min）
- [ ] `client_max_body_size` ≤ 10M（备份走 OSS presigned URL）
- [ ] `proxy_connect_timeout` ≤ 5s
- [ ] 429 响应正确返回（Nginx 限流生效）

## 云备份配额

- [ ] `DEFAULT_STORAGE_QUOTA_BYTES` 已确认（默认 1 GB/用户）
- [ ] `DEFAULT_BACKUP_COUNT_QUOTA` 已确认（默认 100 个/用户）
- [ ] `RATE_LIMIT_BACKUP_INIT_PER_HOUR` 已确认（默认 30 次/小时）
- [ ] `MAX_BACKUP_SIZE_BYTES` 已确认（默认 500 MB）

## 测试

- [ ] `pytest tests/ -q` 全部通过
- [ ] `docker compose config` 无错误
- [ ] `/health` 和 `/ready` 端点响应正常

## 运维

- [ ] 已配置 crontab 定时备份（`deploy/backup-db.sh`）
- [ ] 已确认日志轮转配置（Docker log rotation）
- [ ] 已记录回滚流程和紧急联系方式
- [ ] 已阅读 `INCIDENT_RUNBOOK.md`
- [ ] 已阅读 `DISASTER_RECOVERY.md`
- [ ] 已阅读 `SECURITY_PRIVACY_BASELINE.md`

## 管理员安全

- [ ] 至少有一个 `admin_role=owner` 的管理员账号
- [ ] 不需要最高权限的管理员已分配适当角色（support/ops/readonly）
- [ ] `ADMIN_EMAILS` 环境变量仅包含必须的管理员邮箱
- [ ] 管理员密码符合强度要求（≥8 字符，含大小写、数字、特殊字符）
- [ ] 管理员已了解角色权限矩阵（见 `SECURITY_PRIVACY_BASELINE.md`）

## 安全审计

- [ ] 审计日志表（`audit_logs`）已创建（Alembic 迁移已执行）
- [ ] 确认审计日志中 IP 地址已脱敏（非原始 IP）
- [ ] 确认审计日志 `extra_json` 中不含密码、Token 等敏感字段
- [ ] CSRF 中间件已生效（管理员写请求需要自定义头）
- [ ] Refresh Token 重放检测已验证

## 运行检查

```bash
bash deploy/preflight.sh
```
