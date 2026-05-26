# 灾备与恢复方案

## 概述

本文档描述章枢云 API 的灾备策略、恢复流程和演练要求。

## 恢复目标

| 指标 | 目标值 | 说明 |
|---|---|---|
| **RPO** (恢复点目标) | ≤ 24 小时 | 最多丢失 24 小时内的数据 |
| **RTO** (恢复时间目标) | ≤ 2 小时 | 从故障到恢复服务不超过 2 小时 |

## 备份策略

### PostgreSQL 数据库

| 项目 | 配置 |
|---|---|
| 备份工具 | `pg_dump`（自定义格式） |
| 备份频率 | 每日 03:00（crontab） |
| 保留策略 | 默认 30 天，可配置 `KEEP_DAYS` |
| 校验 | SHA256 校验文件 |
| 存储位置 | 服务器本地 `/opt/zhangshu-cloud/backups/` |

**建议**：
- 将备份同步到异地（OSS 归档存储、另一台服务器）
- 对备份文件加密后存储到 OSS
- 不要将备份提交到 Git

### 阿里云 OSS 用户数据

| 项目 | 建议 |
|---|---|
| 版本控制 | 开启 Bucket 版本控制 |
| 生命周期规则 | 30 天后转低频访问，90 天后转归档 |
| 跨区域复制 | 高可用场景可开启 |
| 防盗链 | 配置 Referer 白名单 |

OSS 数据由阿里云保障 99.9999999999%（12 个 9）的数据持久性。

## 恢复流程

### 场景 1：应用容器故障

```bash
cd /opt/zhangshu-cloud
docker compose restart cloud-api
curl -sf http://127.0.0.1:9000/ready
```

预计恢复时间：< 5 分钟

### 场景 2：数据库故障（可连接）

```bash
# 查看可用备份
ls -lh backups/db_*.dump

# 恢复最近的备份
RESTORE_CONFIRM=yes bash deploy/restore-db.sh backups/db_XXXXXXXX_XXXXXX.dump
```

预计恢复时间：15-30 分钟（取决于数据量）

### 场景 3：数据库故障（不可连接）

```bash
# 重建 PostgreSQL 容器
docker compose down postgres
docker volume rm zhangshu-cloud_postgres_data  # ⚠ 会丢失未备份的数据
docker compose up -d postgres

# 等待 PostgreSQL 就绪
docker compose exec postgres pg_isready -U zhangshu -d zhangshu_cloud

# 恢复备份
RESTORE_CONFIRM=yes bash deploy/restore-db.sh backups/db_XXXXXXXX_XXXXXX.dump

# 运行迁移
docker compose exec cloud-api alembic upgrade head
```

预计恢复时间：30-60 分钟

### 场景 4：整机故障

1. 在新服务器上执行 `deploy/setup.sh` 和 `deploy/deploy.sh`
2. 从异地备份恢复数据库
3. 配置 `.env`（OSS AccessKey、JWT Secret 等）
4. 更新 DNS 指向新服务器 IP
5. 签发 SSL 证书

预计恢复时间：1-2 小时

## 恢复演练

**频率**：每月至少一次

### 演练步骤

1. **准备测试环境**
   ```bash
   # 使用独立目录，不影响生产
   mkdir /tmp/drill && cd /tmp/drill
   cp -r /opt/zhangshu-cloud/{docker-compose.yml,.env,deploy} .
   ```

2. **恢复备份到测试数据库**
   ```bash
   # 复制最近的生产备份
   cp /opt/zhangshu-cloud/backups/db_LATEST.dump ./test_restore.dump

   # 在测试 PostgreSQL 中恢复
   docker compose exec postgres pg_restore \
       -U zhangshu -d zhangshu_cloud --clean --if-exists \
       < test_restore.dump
   ```

3. **验证数据完整性**
   ```bash
   docker compose exec postgres psql -U zhangshu -d zhangshu_cloud \
       -c "SELECT count(*) FROM users;"
   docker compose exec postgres psql -U zhangshu -d zhangshu_cloud \
       -c "SELECT count(*) FROM cloud_backups WHERE status = 'success';"
   ```

4. **验证 API 功能**
   ```bash
   curl -sf http://127.0.0.1:9000/ready
   curl -sf http://127.0.0.1:9000/health
   ```

5. **记录演练结果**
   - 恢复是否成功
   - 实际恢复时间
   - 数据是否完整
   - 发现的问题和改进项

## 备份加密（可选）

对敏感备份使用 GPG 加密后存储到 OSS：

```bash
# 加密
gpg --symmetric --cipher-algo AES256 backups/db_XXXXXXXX.dump

# 上传到 OSS
ossutil cp backups/db_XXXXXXXX.dump.gpg oss://zhangshu-backup-archive/

# 解密
gpg --decrypt backups/db_XXXXXXXX.dump.gpg > restored.dump
```

## 监控和告警（后续扩展）

V1 阶段使用结构化日志和手动检查。后续可接入：

- **Prometheus + Grafana**：API 延迟、错误率、数据库连接数
- **Sentry**：异常追踪和告警
- **阿里云 CloudMonitor**：ECS/OSS/RDS 监控
- **UptimeRobot**：外部 HTTPS 可用性监控
