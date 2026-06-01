# 章枢云服务操作指南

本文档面向运维和开发人员，说明云服务的部署架构、API 接口、常用运维命令和故障排查方法。

> Swagger API 文档：https://api.emailbs.xin/docs

---

## 1. 服务架构

```
客户端 (桌面端 / sidecar)
    │
    ▼
Nginx (443/SSL)
    │  反代到 127.0.0.1:9000
    ▼
Docker: cloud-api (FastAPI + Uvicorn, 2 workers)
    │
    ├── PostgreSQL 16 (端口 5432, 仅本机)
    └── 阿里云 OSS (备份/附件存储)
```

### 服务器信息

| 项目 | 值 |
|------|------|
| IP | 121.40.247.143 |
| 域名 | api.emailbs.xin |
| 部署目录 | /opt/zhangshu-cloud/ |
| Docker Compose | 两个服务：postgres + cloud-api |
| cloud-api 内部端口 | 9000（仅 127.0.0.1） |
| PostgreSQL 内部端口 | 5432（仅 127.0.0.1） |

### 目录结构

```
/opt/zhangshu-cloud/
├── .env                    # 环境变量（敏感，不可提交 Git）
├── .env.example            # 环境变量模板
├── docker-compose.yml      # 容器编排
├── Dockerfile              # cloud-api 镜像构建
├── alembic.ini             # 数据库迁移配置
├── alembic/
│   ├── env.py
│   └── versions/           # 迁移脚本
├── app/                    # FastAPI 应用源码
│   ├── api/                # 路由层
│   ├── services/           # 业务逻辑层
│   ├── repositories/       # 数据访问层
│   ├── models/             # ORM 模型
│   ├── schemas/            # Pydantic schema
│   ├── core/               # 配置、安全、日志
│   ├── db/                 # 数据库引擎
│   └── infrastructure/     # OSS 存储适配器
└── tests/                  # 测试文件
```

---

## 2. 常用运维命令

所有命令通过 SSH 登录后在服务器上执行。

### 2.1 SSH 登录

```bash
ssh root@121.40.247.143
# 密码：@Zhangshussh
```

### 2.2 查看容器状态

```bash
docker ps
# 或更详细
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### 2.3 查看日志

```bash
# 查看 cloud-api 最近 50 行日志
docker logs zhangshu-cloud-cloud-api-1 --tail 50

# 实时跟踪日志
docker logs -f zhangshu-cloud-cloud-api-1

# 查看 PostgreSQL 日志
docker logs zhangshu-cloud-postgres-1 --tail 30
```

### 2.4 重启服务

```bash
# 仅重启 cloud-api（不影响数据库）
cd /opt/zhangshu-cloud && docker compose restart cloud-api

# 重建并重启（代码更新后）
cd /opt/zhangshu-cloud && docker compose up -d --build cloud-api

# 强制重建（不使用缓存）
cd /opt/zhangshu-cloud && docker compose up -d --build --force-recreate cloud-api

# 重启所有服务（包括数据库，谨慎）
cd /opt/zhangshu-cloud && docker compose restart
```

### 2.5 从本地上传文件到服务器

使用 `scp` 命令从本地 Windows 上传文件：

```powershell
# 上传单个文件
scp F:\zhangshu\cloud-server\app\main.py root@121.40.247.143:/opt/zhangshu-cloud/app/main.py

# 上传整个目录
scp -r F:\zhangshu\cloud-server\app\api root@121.40.247.143:/opt/zhangshu-cloud/app/
```

或使用 `sftp`：

```powershell
sftp root@121.40.247.143
# 进入 sftp 后：
put F:\zhangshu\cloud-server\app\main.py /opt/zhangshu-cloud/app/main.py
```

### 2.6 从服务器下载文件

```powershell
scp root@121.40.247.143:/opt/zhangshu-cloud/.env ./server-env-backup
```

### 2.7 进入容器内部

```bash
# 进入 cloud-api 容器
docker exec -it zhangshu-cloud-cloud-api-1 /bin/bash

# 进入 PostgreSQL 容器
docker exec -it zhangshu-cloud-postgres-1 /bin/bash
```

### 2.8 健康检查

```bash
# 简单存活检查
curl http://127.0.0.1:9000/health

# 就绪检查（含数据库和 OSS 配置状态）
curl http://127.0.0.1:9000/ready
```

---

## 3. 数据库操作

### 3.1 连接 PostgreSQL

```bash
# 通过容器执行 SQL
docker exec zhangshu-cloud-postgres-1 psql -U zhangshu -d zhangshu_cloud -c "SELECT count(*) FROM users;"

# 交互式 SQL 终端
docker exec -it zhangshu-cloud-postgres-1 psql -U zhangshu -d zhangshu_cloud
```

### 3.2 常用查询

```sql
-- 查看用户列表
SELECT id, email, display_name, is_admin, created_at FROM users;

-- 查看公告
SELECT id, title, status, severity, published_at FROM announcements;

-- 查看反馈工单
SELECT id, category, status, priority, title, created_at FROM feedback_tickets ORDER BY created_at DESC;

-- 查看备份统计
SELECT u.email, count(b.id) as backup_count, sum(b.size_bytes) as total_size
FROM users u LEFT JOIN cloud_backups b ON u.id = b.owner_id
GROUP BY u.email;

-- 查看当前迁移版本
SELECT * FROM alembic_version;
```

### 3.3 数据库迁移

迁移在容器启动时自动执行（`alembic upgrade head`）。如需手动执行：

```bash
docker exec zhangshu-cloud-cloud-api-1 alembic upgrade head
docker exec zhangshu-cloud-cloud-api-1 alembic current    # 查看当前版本
docker exec zhangshu-cloud-cloud-api-1 alembic history    # 查看迁移历史
```

### 3.4 数据库备份

```bash
# 导出数据库
docker exec zhangshu-cloud-postgres-1 pg_dump -U zhangshu zhangshu_cloud > backup_$(date +%Y%m%d).sql

# 恢复数据库
cat backup.sql | docker exec -i zhangshu-cloud-postgres-1 psql -U zhangshu -d zhangshu_cloud
```

---

## 4. API 接口总览

所有 API 前缀为 `https://api.emailbs.xin`（外网）或 `http://127.0.0.1:9000`（服务器内部）。

需要认证的接口在 Header 中携带：`Authorization: Bearer <ACCESS_TOKEN>`

### 4.1 认证模块 `/api/auth`

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/auth/register` | 否 | 注册新用户 |
| POST | `/api/auth/login` | 否 | 登录获取 JWT token |
| POST | `/api/auth/refresh` | 否 | 刷新 access token |
| GET | `/api/auth/me` | 是 | 获取当前用户信息 |

**注册 / 登录请求体：**

```json
{
  "email": "user@example.com",
  "password": "your-password",
  "display_name": "用户名"     // 仅注册时需要
}
```

**返回：**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user_id": "uuid-string"
}
```

- access_token 有效期：60 分钟（`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`）
- refresh_token 有效期：30 天（`JWT_REFRESH_TOKEN_EXPIRE_DAYS`）
- 登录限流：每 5 分钟 10 次（`RATE_LIMIT_LOGIN_PER_5M`）

### 4.2 项目管理 `/api/projects`

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/projects` | 是 | 创建云项目 |
| GET | `/api/projects` | 是 | 列出当前用户的项目 |

**创建项目请求体：**

```json
{ "title": "我的小说" }
```

### 4.3 云备份 `/api/projects/{project_id}/backups`

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/projects/{project_id}/backups/init` | 是 | 初始化备份上传，返回 OSS presigned URL |
| POST | `/api/projects/{project_id}/backups/complete` | 是 | 确认备份上传完成，校验 SHA256 |
| GET | `/api/projects/{project_id}/backups` | 是 | 列出项目的所有备份 |
| GET | `/api/projects/{project_id}/backups/{backup_id}/download-url` | 是 | 获取备份下载 URL |
| DELETE | `/api/projects/{project_id}/backups/{backup_id}` | 是 | 删除备份 |

**init 请求体：**

```json
{
  "filename": "backup_20260527.zip",
  "size_bytes": 1048576
}
```

**complete 请求体：**

```json
{
  "upload_id": "uuid-from-init",
  "checksum_sha256": "sha256hex..."
}
```

**限制：**
- 单文件最大 500 MB（`MAX_BACKUP_SIZE_BYTES`）
- 每小时最多 30 次 init（`RATE_LIMIT_BACKUP_INIT_PER_HOUR`）
- 每用户默认 1 GB 存储配额（`DEFAULT_STORAGE_QUOTA_BYTES`）
- 每用户默认 100 个备份（`DEFAULT_BACKUP_COUNT_QUOTA`）

### 4.4 账号管理 `/api/account`

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/account/profile` | 是 | 获取个人资料 |
| PATCH | `/api/account/profile` | 是 | 更新昵称 |
| POST | `/api/account/password/change` | 是 | 修改密码 |
| GET | `/api/account/sessions` | 是 | 列出所有登录会话 |
| DELETE | `/api/account/sessions/{session_id}` | 是 | 注销指定会话 |
| POST | `/api/account/sessions/revoke-all` | 是 | 注销所有其他会话 |
| GET | `/api/account/usage` | 是 | 查看存储用量 |
| GET | `/api/account/export` | 是 | 导出账号数据（JSON） |
| POST | `/api/account/delete-request` | 是 | 申请删除账号（第一阶段） |
| DELETE | `/api/account` | 是 | 确认删除账号（第二阶段） |

**修改密码请求体：**

```json
{
  "old_password": "旧密码",
  "new_password": "新密码"
}
```

### 4.5 公告（公开读取）`/api/announcements`

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/announcements` | 否 | 获取当前有效公告列表 |

**查询参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `platform` | string | 按平台过滤：`windows` / `macos` / `linux` |
| `app_version` | string | 客户端版本号 |

**返回示例：**

```json
{
  "items": [
    {
      "id": "uuid",
      "title": "测试公告",
      "body": "测试下公告通知",
      "severity": "info",
      "published_at": "2026-05-27T13:25:29Z",
      "starts_at": null,
      "ends_at": null
    }
  ],
  "total": 1
}
```

### 4.6 公告管理（管理员）`/api/admin/announcements`

所有接口需要管理员权限（Bearer token + ADMIN_EMAILS 白名单或 is_admin=true）。

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/admin/announcements` | 创建公告（草稿状态） |
| GET | `/api/admin/announcements` | 列出所有公告（含草稿） |
| GET | `/api/admin/announcements/{id}` | 查看单条公告详情 |
| PATCH | `/api/admin/announcements/{id}` | 更新公告内容 |
| POST | `/api/admin/announcements/{id}/publish` | 发布公告 |
| POST | `/api/admin/announcements/{id}/archive` | 归档公告 |
| DELETE | `/api/admin/announcements/{id}` | 删除公告 |

**创建公告请求体：**

```json
{
  "title": "公告标题（最多120字）",
  "body": "公告正文（纯文本，不支持 HTML）",
  "severity": "info",
  "platform": null,
  "starts_at": null,
  "ends_at": null
}
```

**severity 级别：**

| 值 | 含义 | 前端展示 |
|---|---|---|
| `info` | 一般通知 | 蓝色横幅 |
| `success` | 好消息 | 绿色横幅 |
| `warning` | 警告 | 黄色横幅 |
| `critical` | 紧急 | 红色横幅 |

**发布公告完整流程：**

```bash
# 1. 登录获取 token
TOKEN=$(curl -s -X POST http://127.0.0.1:9000/api/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email": "2553341751@qq.com", "password": "@Zlc20040613"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 2. 创建公告（使用文件避免中文编码问题）
echo '{"title":"公告标题","body":"公告正文","severity":"info"}' > /tmp/ann.json
ANN_ID=$(curl -s -X POST http://127.0.0.1:9000/api/admin/announcements \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d @/tmp/ann.json | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

# 3. 发布
curl -X POST http://127.0.0.1:9000/api/admin/announcements/$ANN_ID/publish \
  -H "Authorization: Bearer $TOKEN"
```

> **注意**：通过 SSH 执行 curl 时，中文 JSON 建议使用文件（`-d @file`）或 base64 编码传递，避免编码问题。

### 4.7 用户反馈（公开）`/api/feedback`

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/feedback` | 可选 | 提交反馈（支持匿名和已登录用户） |
| POST | `/api/feedback/{id}/complete` | 否 | 确认附件上传完成 |

**提交反馈请求体：**

```json
{
  "category": "bug",
  "title": "问题标题",
  "description": "详细描述（至少10个字符）",
  "contact_email": "user@example.com",
  "attachments": [
    {
      "filename": "screenshot.png",
      "content_type": "image/png",
      "size_bytes": 102400,
      "checksum_sha256": "sha256hex..."
    }
  ]
}
```

**category 分类：**

| 值 | 含义 |
|---|---|
| `bug` | 程序错误 |
| `suggestion` | 功能建议 |
| `data_loss` | 数据丢失 |
| `cloud` | 云服务问题 |
| `ui` | 界面问题 |
| `other` | 其他 |

**附件限制：**
- 最多 5 个附件（`FEEDBACK_MAX_ATTACHMENTS`）
- 单文件最大 50 MB（`FEEDBACK_MAX_ATTACHMENT_SIZE_BYTES`）
- 总大小最大 150 MB（`FEEDBACK_MAX_TOTAL_SIZE_BYTES`）
- 允许类型：PNG、JPEG、WebP、GIF、MP4、WebM、MOV

### 4.8 反馈管理（管理员）`/api/admin/feedback`

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/admin/feedback` | 列出反馈（支持 status/category 筛选） |
| GET | `/api/admin/feedback/{id}` | 查看反馈详情 |
| PATCH | `/api/admin/feedback/{id}` | 更新反馈状态/优先级/备注 |
| GET | `/api/admin/feedback/{id}/attachments/{aid}/download-url` | 获取附件下载 URL |
| DELETE | `/api/admin/feedback/{id}` | 删除反馈 |

**筛选参数：**

| 参数 | 可选值 |
|------|------|
| `status` | `open` / `triaged` / `in_progress` / `closed` / `spam` |
| `category` | `bug` / `suggestion` / `data_loss` / `cloud` / `ui` / `other` |
| `limit` | 1-200 |
| `offset` | 偏移量 |

**更新反馈请求体：**

```json
{
  "status": "triaged",
  "priority": "high",
  "admin_note": "已复现，排入下个迭代修复。"
}
```

### 4.9 系统探针

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/health` | 否 | 存活探针，返回 `{"status": "ok"}` |
| GET | `/ready` | 否 | 就绪探针，检查 DB 和 OSS 配置 |

---

## 5. 完整部署流程

### 5.1 首次部署

```bash
# 1. SSH 登录服务器
ssh root@121.40.247.143

# 2. 克隆或上传代码到 /opt/zhangshu-cloud/
cd /opt
git clone <repo-url> zhangshu-cloud
# 或从本地上传：scp -r ./cloud-server/* root@121.40.247.143:/opt/zhangshu-cloud/

# 3. 配置环境变量
cp .env.example .env
vim .env  # 修改以下必要项：
#   DATABASE_URL=postgresql+psycopg://zhangshu:zhangshu@postgres:5432/zhangshu_cloud
#   JWT_SECRET_KEY=<随机32字符以上>
#   OSS_ACCESS_KEY_ID=<阿里云 AK>
#   OSS_ACCESS_KEY_SECRET=<阿里云 SK>
#   ADMIN_EMAILS=2553341751@qq.com

# 4. 启动服务
docker compose up -d --build

# 5. 验证
curl http://127.0.0.1:9000/health
curl http://127.0.0.1:9000/ready
```

### 5.2 代码更新部署

```bash
# 1. 上传更新的文件
# 从本地 Windows：
scp -r F:\zhangshu\cloud-server\app root@121.40.247.143:/opt/zhangshu-cloud/
scp F:\zhangshu\cloud-server\alembic\versions\*.py root@121.40.247.143:/opt/zhangshu-cloud/alembic/versions/

# 2. 重建并重启
cd /opt/zhangshu-cloud && docker compose up -d --build cloud-api

# 3. 检查日志
docker logs zhangshu-cloud-cloud-api-1 --tail 20
```

### 5.3 批量同步所有文件（Python 脚本）

适用于大量文件变更时，一次性同步本地代码到服务器：

```python
import paramiko, os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('121.40.247.143', username='root', password='@Zhangshussh')

sftp = ssh.open_sftp()
local_base = r'F:\zhangshu\cloud-server\app'
remote_base = '/opt/zhangshu-cloud/app'

for root, dirs, files in os.walk(local_base):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if f.endswith('.py'):
            local_path = os.path.join(root, f)
            rel_path = os.path.relpath(local_path, local_base)
            remote_path = remote_base + '/' + rel_path.replace(os.sep, '/')
            sftp.put(local_path, remote_path)
            print(f'  ok {rel_path}')

sftp.close()

# 重建容器
stdin, stdout, stderr = ssh.exec_command(
    'cd /opt/zhangshu-cloud && docker compose up -d --build cloud-api'
)
print(stderr.read().decode())
ssh.close()
```

---

## 6. 环境变量参考

### 核心配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./cloud_server.db` | 数据库连接字符串，生产用 PostgreSQL |
| `ENVIRONMENT` | `development` | `production` 时启用严格校验 |
| `JWT_SECRET_KEY` | `change-me-in-production` | JWT 签名密钥，生产必须更换 |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 60 | access token 有效期（分钟） |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | 30 | refresh token 有效期（天） |
| `BCRYPT_ROUNDS` | 12 | 密码哈希轮数 |

### OSS 存储

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OSS_ACCESS_KEY_ID` | （空） | 阿里云 AccessKey ID |
| `OSS_ACCESS_KEY_SECRET` | （空） | 阿里云 AccessKey Secret |
| `OSS_BUCKET_NAME` | `zhangshu-backups` | OSS Bucket 名称 |
| `OSS_ENDPOINT` | `oss-cn-hangzhou.aliyuncs.com` | OSS 端点 |
| `OSS_PUBLIC_ENDPOINT` | （空=同 OSS_ENDPOINT） | 公网端点（用于 presigned URL） |
| `OSS_INTERNAL_ENDPOINT` | （空=同 OSS_ENDPOINT） | 内网端点（用于服务端操作） |
| `OSS_PRESIGNED_URL_EXPIRE_SECONDS` | 1800 | 签名 URL 有效期（秒） |

### 限流与配额

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `RATE_LIMIT_LOGIN_PER_5M` | 10 | 登录限流（每5分钟） |
| `RATE_LIMIT_BACKUP_INIT_PER_HOUR` | 30 | 备份初始化限流（每小时） |
| `DEFAULT_STORAGE_QUOTA_BYTES` | 1073741824 | 用户存储配额（1 GB） |
| `DEFAULT_BACKUP_COUNT_QUOTA` | 100 | 用户备份数量配额 |
| `MAX_BACKUP_SIZE_BYTES` | 524288000 | 单备份最大（500 MB） |

### 管理员

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ADMIN_EMAILS` | （空） | 管理员邮箱白名单，逗号分隔 |

### 反馈

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `FEEDBACK_MAX_ATTACHMENTS` | 5 | 单条反馈最大附件数 |
| `FEEDBACK_MAX_ATTACHMENT_SIZE_BYTES` | 52428800 | 单附件最大（50 MB） |
| `FEEDBACK_MAX_TOTAL_SIZE_BYTES` | 157286400 | 附件总大小最大（150 MB） |
| `RATE_LIMIT_FEEDBACK_CREATE_PER_HOUR` | 5 | 反馈提交限流（每小时） |
| `RATE_LIMIT_FEEDBACK_UPLOAD_PER_HOUR` | 20 | 附件上传限流（每小时） |

### 其他

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CORS_ORIGINS` | `http://localhost:5180,...` | 允许的 CORS 来源 |
| `FORCE_HTTPS` | true | 生产模式强制 HTTPS |
| `LOG_LEVEL` | INFO | 日志级别 |
| `ACCESS_LOG_JSON` | true | JSON 格式访问日志 |

---

## 7. Nginx 配置

Nginx 安装在宿主机（非 Docker），配置文件位于 `/etc/nginx/sites-enabled/`。

```nginx
# HTTP → HTTPS 重定向
server {
    listen 80;
    server_name api.emailbs.xin;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# HTTPS 反向代理
server {
    listen 443 ssl http2;
    server_name api.emailbs.xin;

    ssl_certificate     /etc/letsencrypt/live/api.emailbs.xin/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.emailbs.xin/privkey.pem;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**常用 Nginx 命令：**

```bash
# 检查配置语法
nginx -t

# 重载配置
systemctl reload nginx

# 查看 Nginx 日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# 续期 SSL 证书
certbot renew --dry-run
certbot renew
```

---

## 8. 故障排查

### 容器反复重启

```bash
# 查看日志找原因
docker logs zhangshu-cloud-cloud-api-1 --tail 50

# 常见原因：
# 1. 数据库连接失败 → 检查 .env 中 DATABASE_URL
# 2. 缺少依赖文件 → 重新同步所有文件
# 3. 迁移失败 → 检查 alembic/versions/ 目录是否完整
```

### 数据库连接失败

```bash
# 检查 PostgreSQL 是否运行
docker ps | grep postgres

# 重置密码（如果认证失败）
docker exec zhangshu-cloud-postgres-1 psql -U zhangshu -d zhangshu_cloud \
  -c "ALTER USER zhangshu WITH PASSWORD 'zhangshu';"

# 重启 cloud-api
cd /opt/zhangshu-cloud && docker compose restart cloud-api
```

### 中文乱码

通过 SSH 执行 curl 传递中文 JSON 时可能乱码。解决方法：

```bash
# 方法1：使用文件传递
echo '{"title":"测试"}' > /tmp/data.json
curl -X POST ... -d @/tmp/data.json

# 方法2：使用 base64 编码
echo 'eyJ0aXRsZSI6IuWlsuaPqCJ9' | base64 -d > /tmp/data.json
curl -X POST ... -d @/tmp/data.json
```

### 磁盘空间不足

```bash
# 查看磁盘使用
df -h

# 清理 Docker 镜像缓存
docker system prune -f

# 查看 Docker 空间占用
docker system df
```

### SSL 证书过期

```bash
# 检查证书有效期
openssl x509 -enddate -noout -in /etc/letsencrypt/live/api.emailbs.xin/fullchain.pem

# 续期
certbot renew
systemctl reload nginx
```
