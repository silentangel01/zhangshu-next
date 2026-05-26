# 章枢云 API — Ubuntu 22.04 部署指南

> 适用于阿里云轻量应用服务器 2v2G Ubuntu 22.04

## 架构概览

```
用户桌面客户端
    │
    │ HTTPS (443)
    ▼
Nginx (反向代理 + SSL)
    │
    │ HTTP (9000, 仅本机)
    ▼
FastAPI (cloud-api, 2 workers)
    │
    ├── PostgreSQL 16 (5432, 仅本机)
    │
    └── 阿里云 OSS (备份文件直传)
```

## 前置条件

- 一台阿里云轻量应用服务器 (Ubuntu 22.04, 2v2G)
- 一个已备案的域名 (国内服务器需要) 或 IP 直接访问
- 阿里云 OSS Bucket + RAM 用户 AccessKey
- 本地已安装 SSH 客户端 (Windows 自带)

## 部署步骤

### 第一步：服务器安全组配置

登录阿里云控制台 → 轻量应用服务器 → 防火墙 → 添加规则：

| 端口 | 协议 | 用途 |
|------|------|------|
| 22   | TCP  | SSH  |
| 80   | TCP  | HTTP |
| 443  | TCP  | HTTPS |

### 第二步：SSH 密钥登录

```bash
# 本地生成密钥 (如果没有)
ssh-keygen -t ed25519 -C "zhangshu-deploy"

# 复制公钥到服务器
ssh-copy-id root@YOUR_SERVER_IP
```

### 第三步：初始化服务器

```bash
# SSH 登录服务器
ssh root@YOUR_SERVER_IP

# 设置域名和邮箱环境变量
export ZHANGSHU_DOMAIN="api.yourdomain.com"
export ZHANGSHU_EMAIL="your-email@example.com"

# 运行初始化脚本
bash deploy/setup.sh
```

脚本会自动完成：
- 创建 `deploy` 用户
- 加固 SSH (禁止 root/密码登录)
- 配置防火墙 (UFW)
- 安装 Docker + Docker Compose
- 安装 Nginx + Certbot
- 配置 2G swap (优化 2G 内存)
- 启用自动安全更新

### 第四步：上传代码

**方式 A: 使用 rsync (推荐)**

```bash
# 在本地运行
bash deploy/upload.sh YOUR_SERVER_IP
```

**方式 B: 手动 scp**

```bash
# 在本地运行
scp -r cloud-server/ deploy@YOUR_SERVER_IP:/opt/zhangshu-cloud/
```

**方式 C: Git 拉取 (如果代码在 Git 仓库)**

```bash
# SSH 登录服务器后
cd /opt/zhangshu-cloud
git clone https://your-repo.com/cloud-server.git .
```

### 第五步：配置域名 DNS

在域名服务商处添加 DNS 记录：

| 类型 | 主机记录 | 记录值 |
|------|----------|--------|
| A    | api      | YOUR_SERVER_IP |

等待 DNS 生效 (通常 1-10 分钟)。

### 第六步：运行部署脚本

```bash
# SSH 登录服务器 (使用 deploy 用户)
ssh deploy@YOUR_SERVER_IP

# 设置环境变量
export ZHANGSHU_DOMAIN="api.yourdomain.com"
export ZHANGSHU_EMAIL="your-email@example.com"

# 运行部署脚本
cd /opt/zhangshu-cloud
bash deploy/deploy.sh
```

脚本会自动：
1. 生成 `.env` 配置文件 (JWT 密钥和数据库密码自动生成)
2. 配置 Nginx 反向代理
3. 申请 Let's Encrypt SSL 证书
4. 构建 Docker 镜像
5. 启动容器并验证

### 第七步：配置阿里云 OSS

编辑 `.env` 文件，填入 OSS 配置：

```bash
nano /opt/zhangshu-cloud/.env
```

```env
OSS_ACCESS_KEY_ID=LTAI5t...
OSS_ACCESS_KEY_SECRET=abc123...
OSS_BUCKET_NAME=zhangshu-backups
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
# 公网端点 — 用于生成客户端预签名 URL（必须是桌面端可达的公网地址）
OSS_PUBLIC_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
# 内网端点 — 用于服务端 head/delete 操作（可使用 VPC 内网地址节省流量）
OSS_INTERNAL_ENDPOINT=oss-cn-hangzhou-internal.aliyuncs.com
```

重启服务使配置生效：

```bash
cd /opt/zhangshu-cloud
docker compose restart cloud-api
```

### 第八步：验证部署

```bash
# 健康检查
curl https://api.yourdomain.com/health
# 应返回: {"status":"ok"}

# 查看 API 文档
# 浏览器访问: https://api.yourdomain.com/docs
```

**OSS 端点验证**：确保 `OSS_PUBLIC_ENDPOINT` 是公网可达地址（不含 `-internal`）。如果预签名 URL 使用了内网端点，桌面客户端将无法访问，上传/下载会失败。

## 日常运维

### 查看日志

```bash
cd /opt/zhangshu-cloud
docker compose logs -f cloud-api
```

### 更新部署

```bash
cd /opt/zhangshu-cloud
bash deploy/update.sh
```

自动完成：备份数据库 → 重建镜像 → 滚动更新 → 运行迁移 → 健康检查

### 备份数据库

```bash
bash deploy/backup-db.sh
```

设置定时备份 (每天凌晨 3 点)：

```bash
crontab -e
# 添加:
0 3 * * * /opt/zhangshu-cloud/deploy/backup-db.sh >> /var/log/zhangshu-backup.log 2>&1
```

### 重启服务

```bash
cd /opt/zhangshu-cloud
docker compose restart
```

### 查看资源使用

```bash
docker stats --no-stream
```

### 部署前检查

```bash
bash deploy/preflight.sh
```

自动检查 `.env` 配置、数据库连接、OSS 端点、磁盘空间等。

### 数据库恢复

```bash
# 查看可用备份
ls -lh backups/db_*.dump

# 恢复 (需要显式确认)
RESTORE_CONFIRM=yes bash deploy/restore-db.sh backups/db_XXXXXXXX_XXXXXX.dump
```

恢复前会自动备份当前数据库，详见 `docs/DISASTER_RECOVERY.md`。

## 故障排查

### 服务无法启动

```bash
# 查看容器状态
docker compose ps

# 查看详细日志
docker compose logs cloud-api

# 检查端口占用
sudo netstat -tlnp | grep -E '80|443|9000'
```

### SSL 证书问题

```bash
# 手动续期证书
sudo certbot renew --dry-run
sudo certbot renew
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 状态
docker compose logs postgres

# 进入数据库
docker compose exec postgres psql -U zhangshu -d zhangshu_cloud
```

### 内存不足

```bash
# 查看内存使用
free -h

# 查看 swap 使用
swapon --show

# 重启服务释放内存
cd /opt/zhangshu-cloud
docker compose restart
```

## 安全建议

1. **定期更新系统**：已配置自动安全更新，但建议每月手动检查
2. **备份异地存储**：将数据库备份下载到本地或上传到其他云存储
3. **监控日志**：定期检查 `/var/log/auth.log` 和容器日志
4. **限制访问**：如果不需要公网访问 API 文档，可在 Nginx 中限制 `/docs` 路径

## 性能优化 (2v2G 服务器)

- ✅ 已配置 2G swap (swappiness=10)
- ✅ Docker 资源限制 (PostgreSQL 256M, API 512M)
- ✅ Uvicorn 2 workers (适合 2 vCPU)
- ✅ 静态文件缓存 (Nginx)
- ✅ Gzip 压缩 (Nginx 默认启用)

## 扩展建议

如果用户量增长，考虑：
1. 升级到 4G 内存
2. 使用阿里云 RDS PostgreSQL (托管数据库)
3. 添加 Redis 缓存 (替换进程内限流)
4. 使用 CDN 加速静态资源
5. 配置负载均衡 (多台 API 实例)

## 运维文档

- [`docs/PRODUCTION_CHECKLIST.md`](../docs/PRODUCTION_CHECKLIST.md) — 生产部署检查清单
- [`docs/INCIDENT_RUNBOOK.md`](../docs/INCIDENT_RUNBOOK.md) — 事故处置手册
- [`docs/DISASTER_RECOVERY.md`](../docs/DISASTER_RECOVERY.md) — 灾备与恢复方案
