# 章枢云 (Zhangshu Cloud) API Server

章枢桌面写作软件的云端备份 API 服务端。提供用户注册/登录、作品管理、阿里云 OSS 备份上传与下载能力。

## 架构概览

```
桌面客户端 (Zhangshu Desktop)
    │
    │  HTTPS (JWT)
    ▼
章枢云 API (本项目)
    │
    ├── PostgreSQL  ── 用户、作品、备份记录
    │
    └── 阿里云 OSS  ── 备份文件存储 (预签名 URL)
```

桌面客户端**不持有** OSS AccessKey。服务端生成预签名 URL，客户端直接上传/下载至 OSS。

## 技术栈

| 层       | 技术                                          |
|----------|-----------------------------------------------|
| 框架     | FastAPI + Uvicorn                             |
| ORM      | SQLAlchemy 2.0                                |
| 数据库   | PostgreSQL 16 (生产) / SQLite (本地开发/测试)  |
| 迁移     | Alembic                                       |
| 认证     | PyJWT + bcrypt (passlib)                      |
| 对象存储 | oss2 (阿里云)                                 |
| 容器化   | Docker + docker-compose                       |

## 目录结构

```
cloud-server/
├── app/
│   ├── api/           # FastAPI 路由层 (auth, projects, backups)
│   ├── core/          # 配置 (config.py) 与安全工具 (security.py)
│   ├── db/            # 数据库引擎与会话 (base.py, session.py)
│   ├── infrastructure/# OSS 存储适配器 (oss_storage.py)
│   ├── models/        # SQLAlchemy ORM 模型
│   ├── repositories/  # 数据访问层
│   ├── schemas/       # Pydantic 请求/响应 schema
│   └── services/      # 业务逻辑层
├── alembic/           # 数据库迁移
├── tests/             # pytest 测试
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
└── requirements.txt
```

## 本地开发

### 1. 创建虚拟环境

```powershell
cd F:\zhangshu\cloud-server
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. 配置环境变量

复制示例文件并按需修改：

```powershell
copy .env.example .env
```

关键配置项：

| 变量                  | 说明                           | 示例值                              |
|-----------------------|--------------------------------|-------------------------------------|
| `DATABASE_URL`        | 数据库连接串                   | `postgresql+psycopg://...` 或 `sqlite:///./dev.db` |
| `JWT_SECRET_KEY`      | JWT 签名密钥 (≥32 字符)       | 随机生成                            |
| `CORS_ORIGINS`        | 允许的跨域来源 (逗号分隔)      | `http://localhost:5180`             |
| `OSS_ACCESS_KEY_ID`   | 阿里云 AccessKey ID            | —                                   |
| `OSS_ACCESS_KEY_SECRET` | 阿里云 AccessKey Secret      | —                                   |
| `OSS_BUCKET_NAME`     | OSS Bucket 名称                | `zhangshu-backups`                  |
| `OSS_ENDPOINT`        | OSS 节点 (默认回退)              | `oss-cn-hangzhou.aliyuncs.com`      |
| `OSS_PUBLIC_ENDPOINT`  | 公网端点 (预签名 URL 使用，客户端可达) | `oss-cn-hangzhou.aliyuncs.com`      |
| `OSS_INTERNAL_ENDPOINT`| 内网端点 (服务端 head/delete 操作)  | `oss-cn-hangzhou-internal.aliyuncs.com` |

> **端点说明**：`OSS_PUBLIC_ENDPOINT` 用于生成客户端可访问的预签名 URL，必须是公网可达地址。`OSS_INTERNAL_ENDPOINT` 用于服务端 OSS 操作（如检查对象、删除对象），可使用 VPC 内网端点以节省流量费用。如不配置，两者均回退到 `OSS_ENDPOINT`。

> **提示**：本地开发可将 `DATABASE_URL` 设为 SQLite 路径，无需安装 PostgreSQL。

### 3. 运行数据库迁移

```powershell
alembic upgrade head
```

### 4. 启动开发服务器

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 9000
```

API 文档：http://127.0.0.1:9000/docs

### 5. 运行测试

```powershell
pytest -q
```

测试使用 SQLite 内存数据库 + MagicMock OSS，无需外部依赖。

## Docker 部署

### 构建与启动

```bash
# 配置 .env 后
docker compose up -d
```

此命令会：
1. 启动 PostgreSQL 16 (带健康检查)
2. 自动运行 `alembic upgrade head`
3. 启动 cloud-api 服务 (端口 9000)

### 仅构建镜像

```bash
docker compose build
```

### 查看日志

```bash
docker compose logs -f cloud-api
```

## 阿里云 OSS 配置指南

### 1. 创建 Bucket

- 登录阿里云 OSS 控制台
- 创建 Bucket，选择**私有读写**
- 开启**跨域设置 (CORS)**：
  - 来源：你的桌面客户端域名 (或 `*` 用于开发)
  - 允许 Methods：`GET`, `PUT`, `HEAD`
  - 允许 Headers：`Content-Type`, `*`
  - 暴露 Headers：`ETag`, `Content-Length`

### 2. 创建 RAM 用户

- 创建专用 RAM 子账号
- 授权策略：仅允许对该 Bucket 的 `oss:PutObject`、`oss:GetObject`、`oss:HeadObject`、`oss:DeleteObject`
- 生成 AccessKey ID 和 Secret

### 3. 配置环境变量

将 AccessKey 填入 `.env`：

```
OSS_ACCESS_KEY_ID=LTAI...
OSS_ACCESS_KEY_SECRET=abc...
OSS_BUCKET_NAME=zhangshu-backups
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
```

> **注意**：OSS 未配置时，备份相关接口会返回 503 Service Unavailable。认证和作品管理接口不受影响。

## API 端点

### 认证

| 方法   | 路径               | 说明       | 鉴权 |
|--------|---------------------|------------|------|
| POST   | `/api/auth/register`| 注册       | —    |
| POST   | `/api/auth/login`   | 登录       | —    |
| POST   | `/api/auth/refresh` | 刷新令牌   | —    |
| GET    | `/api/auth/me`      | 获取当前用户 | ✅   |

### 作品

| 方法   | 路径              | 说明       | 鉴权 |
|--------|-------------------|------------|------|
| POST   | `/api/projects`   | 创建作品   | ✅   |
| GET    | `/api/projects`   | 获取作品列表 | ✅   |

### 备份

| 方法   | 路径                                           | 说明         | 鉴权 |
|--------|------------------------------------------------|--------------|------|
| POST   | `/api/projects/{id}/backups/init`             | 初始化上传   | ✅   |
| POST   | `/api/projects/{id}/backups/complete`         | 完成上传     | ✅   |
| GET    | `/api/projects/{id}/backups`                  | 备份列表     | ✅   |
| GET    | `/api/projects/{id}/backups/{bid}/download-url`| 获取下载链接 | ✅   |
| DELETE | `/api/projects/{id}/backups/{bid}`            | 删除备份     | ✅   |

### 健康检查

| 方法   | 路径       | 说明     |
|--------|------------|----------|
| GET    | `/health`  | 服务状态 |

## 安全设计

- **密码**：bcrypt 哈希 (12 轮)，72 字节上限校验
- **令牌**：Access Token (60 分钟) + Refresh Token (30 天，一次性使用，轮换制)
- **Refresh Token 存储**：仅存 JTI 的 SHA-256 哈希，不存明文
- **限流**：登录/注册接口每 IP+邮箱 5 分钟内最多 10 次
- **CORS**：不允许 `*` 通配符 (生产环境)
- **错误信息**：登录失败统一返回"邮箱或密码错误"，不泄露用户是否存在
- **OSS**：桌面客户端不持有 AccessKey，仅使用预签名 URL (有效期 30 分钟)
- **日志**：不记录密码、令牌、密钥

## License

Private — 章枢项目内部使用。
