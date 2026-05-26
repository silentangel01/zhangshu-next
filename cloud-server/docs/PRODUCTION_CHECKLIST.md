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
- [ ] Alembic 迁移已执行（`alembic upgrade head`）
- [ ] 已执行过至少一次数据库备份
- [ ] 已执行过至少一次恢复演练

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

## 运行检查

```bash
bash deploy/preflight.sh
```
