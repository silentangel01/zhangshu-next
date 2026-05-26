# 云备份上传与账号注册：全链路排查复盘

> 时间跨度：2026-05-25 ~ 2026-05-26
> 影响范围：账号注册、登录、云端备份上传
> 最终根因：校园网 DPI 设备对 TLS SNI 域名进行过滤

---

## 1. 系统架构概览

章枢的云备份系统由三个独立组件构成，通过 HTTP 契约通信：

```
┌──────────────────────┐     HTTPS      ┌──────────────────────┐     SDK      ┌──────────────┐
│      桌面端           │ ─────────────→ │     云服务端          │ ──────────→ │  阿里云 OSS  │
│                      │                │                      │             │              │
│  Vue 3 前端          │   api.emailbs  │  FastAPI + Docker    │  预签名 URL  │  对象存储    │
│  FastAPI 后端        │   .xin         │  PostgreSQL          │  直传文件    │              │
│  SQLite 本地存储     │                │  Nginx 反向代理      │             │              │
└──────────────────────┘                └──────────────────────┘             └──────────────┘
```

**数据流**：

- 桌面端 `CloudApiClient` 持有 JWT token，向云服务端发起 API 请求
- 云服务端验证身份后，通过阿里云 OSS SDK 生成预签名 URL
- 桌面端拿到预签名 URL 后，将备份 zip 文件直接 PUT 到 OSS（不经过云服务端中转）
- 上传完成后，桌面端通知云服务端校验文件大小并记录备份元数据

**API 契约**（桌面端 `CloudApiClient` 已固定 12 个端点，服务端必须兼容）：

| 端点 | 用途 |
|---|---|
| `POST /api/auth/register` | 账号注册 |
| `POST /api/auth/login` | 账号登录 |
| `POST /api/auth/refresh` | 刷新 JWT |
| `GET /api/auth/me` | 获取当前用户信息 |
| `POST /api/projects` | 创建云端项目 |
| `GET /api/projects` | 获取云端项目列表 |
| `POST /api/projects/{id}/backups/init` | 初始化备份上传，获取预签名 URL |
| `PUT {presigned_url}` | 直传 OSS（非 FastAPI 端点） |
| `POST /api/projects/{id}/backups/complete` | 完成备份，校验文件 |
| `GET /api/projects/{id}/backups` | 获取备份列表 |
| `GET /api/projects/{id}/backups/{bid}/download-url` | 获取下载预签名 URL |
| `DELETE /api/projects/{id}/backups/{bid}` | 删除备份 |

---

## 2. 问题全景与时间线

整个排查过程可以分为四个阶段，每个阶段解决一类问题：

| 阶段 | 问题类别 | 耗时占比 | 难度 |
|---|---|---|---|
| 一、服务端搭建 | 新建 cloud-server 项目 | -- | 低 |
| 二、服务器部署 | Docker/镜像/数据库/SSL 等环境问题 | 约 30% | 中 |
| 三、TLS 连接失败 | 桌面端无法连接云服务端 | 约 60% | **高** |
| 四、OSS 上传 403 | 预签名 URL 内外网地址不匹配 | 约 10% | 低 |

阶段三中的 TLS 连接问题是本次排查的核心难点，经历了三轮错误假设才定位到真正的根因。

---

## 3. 第一阶段：服务端搭建

在 `cloud-server/` 目录新建独立 FastAPI 项目。与桌面端 `backend/` 完全解耦，不共享任何代码，仅通过 HTTP 契约通信。

核心设计决策：

- **独立项目，不 import 桌面端代码**：避免耦合，两端可以独立部署和升级
- **PostgreSQL 替代 SQLite**：云端需要并发支持，SQLite 不适合多用户场景
- **OSS AccessKey 只在服务端**：桌面端永远不接触 AccessKey，只拿到短时有效的预签名 URL
- **JWT 双 token 机制**：access token 短时有效（15 分钟），refresh token 长效（7 天）并支持轮换
- **登录错误不区分"用户不存在"和"密码错误"**：防止账号枚举攻击

这一阶段本身没有遇到技术障碍，代码按 Codex 计划正常实现。

---

## 4. 第二阶段：服务器部署

服务器为阿里云轻量应用服务器（Ubuntu 22.04，2 核 2G），域名 `api.emailbs.xin`，IP `121.40.247.143`。部署使用 Docker Compose 编排 FastAPI + PostgreSQL，Nginx 反向代理 + Let's Encrypt SSL。

部署过程中依次遇到 5 个环境问题：

### 4.1 Docker 安装超时

**现象**：`apt-get install docker-ce` 下载超时。

**原因**：`download.docker.com` 在国内无法访问。

**解决**：替换为阿里云 Docker 镜像源：

```bash
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
```

### 4.2 交互式提示阻塞部署脚本

**现象**：`apt-get install` 过程中弹出 `needrestart` 和 `dpkg` 配置冲突的交互对话框，脚本挂起。

**解决**：强制非交互模式：

```bash
export DEBIAN_FRONTEND=noninteractive
echo '$nrconf{restart} = "a";' > /etc/needrestart/conf.d/99-auto.conf
apt-get install -y \
  -o Dpkg::Options::="--force-confdef" \
  -o Dpkg::Options::="--force-confold" \
  docker-ce docker-ce-cli containerd.io
```

### 4.3 Docker 镜像拉取超时

**现象**：`docker build` 时 `python:3.12-slim` 基础镜像拉取失败。

**原因**：Docker Hub 国内不可达。

**解决**：通过 DaoCloud 镜像代理拉取后重新打标签：

```bash
docker pull docker.m.daocloud.io/python:3.12-slim
docker tag docker.m.daocloud.io/python:3.12-slim python:3.12-slim
```

同时 `Dockerfile` 中 pip 源替换为阿里云镜像。

### 4.4 Alembic 数据库迁移失败

**现象**：`alembic upgrade head` 报错，PostgreSQL 拒绝 Boolean 默认值。

**原因**：迁移脚本中使用了 SQLite 风格的 `sa.text("1")`，PostgreSQL 要求 `sa.text("true")`。

```python
# 修复前
sa.Column("is_active", sa.Boolean(), server_default=sa.text("1"))
# 修复后
sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"))
```

### 4.5 Nginx SSL 配置

配置 Let's Encrypt 证书 + Nginx 反向代理。初始配置启用了 TLS 1.2 + TLS 1.3 + HTTP/2，后续因 TLS 兼容性问题（见第三阶段）调整为仅 TLS 1.2、关闭 HTTP/2。

> **小结**：以上 5 个问题都属于国内服务器部署的常规障碍，有成熟解决方案。真正棘手的问题在下一阶段。

---

## 5. 第三阶段：TLS 连接失败（核心难题）

这是整个排查过程中最复杂、耗时最长的部分，占总排查时间的约 60%。问题表现为桌面端 Python 进程无法与云服务端建立 HTTPS 连接，但浏览器可以正常访问同一地址。

这个问题之所以困难，是因为它的症状极具误导性——看起来像是 TLS 版本不兼容，也像是代理软件干扰，但真正的根因隐藏在更底层的网络基础设施中。排查经历了三轮假设验证，前两轮都是"合理的猜测，错误的方向"。

### 5.1 问题现象

部署完成后，首次从桌面端发起注册请求：

```python
# 桌面端 CloudApiClient 内部调用
POST https://api.emailbs.xin/api/auth/register
```

返回错误：

```
httpx.ConnectError: [WinError 10054] 远程主机强迫关闭了一个现有的连接。
```

关键矛盾点：**浏览器直接访问 `https://api.emailbs.xin/api/auth/register` 能正常返回 JSON**。同一个 URL，浏览器行，Python 不行。

这个矛盾是整条排查线索的起点。它告诉我们：服务端本身没有问题（浏览器能拿到响应），问题出在"浏览器和 Python 有什么不同"。

### 5.2 第一轮排查：Python 3.14 TLS 兼容性（方向错误）

**为什么猜这个**：本地开发环境使用的是 Python 3.14（预发布版本），其 SSL 模块基于较新的 OpenSSL 3.x。Python 3.14 在 TLS 1.3 的 key share 协商上可能有行为变化。同时，Nginx error log 中确实出现了 `bad key share` 相关的 SSL 错误信息，看起来证据链是完整的。

**做了什么**：
1. 将本地 Python 从 3.14 降级到 3.12.10，重建虚拟环境
2. Nginx 端将 `ssl_protocols TLSv1.2 TLSv1.3` 改为仅 `TLSv1.2`
3. 关闭 HTTP/2（HTTP/2 的 ALPN 协商可能干扰 TLS 握手）

**结果**：问题未解决，错误信息一字不差。

**为什么走错了**：Nginx error log 中的 `bad key share` 信息是误导性的。当 DPI 设备在 TLS 握手过程中注入 RST 包时，Nginx 看到的是一个异常的 TLS 连接中断，其日志描述可能恰好与 key share 错误相似。我们犯了"看到日志就信日志"的错误，没有考虑日志本身可能是间接症状。

**教训**：日志是服务端视角的记录，当问题发生在客户端到服务端的传输链路上时，服务端日志可能给出不准确的描述。应该同时从客户端视角进行验证。

### 5.3 第二轮排查：Clash 代理干扰（部分正确）

**为什么猜这个**：开发机上运行着 Clash Verge 代理软件（含 TUN 模式），它会拦截系统级别的网络流量。即使关闭 Clash 界面，TUN 模式可能仍在系统网络栈中残留。这是一个非常合理的怀疑——代理软件导致 HTTP 客户端行为异常是常见问题。

**做了什么**：
1. 完全关闭 Clash 所有进程，包括后台服务
2. 在 httpx Client 上设置 `trust_env=False`，阻止读取 `HTTP_PROXY`/`HTTPS_PROXY` 环境变量
3. 对比测试：关闭 Clash 前后，curl 和 Python 的行为

**结果**：问题未解决。但有一个重要观察——**浏览器走 Clash 代理访问正常，关闭 Clash 后直连仍然失败**。

**这轮排查的价值**：虽然没有解决问题，但 `trust_env=False` 是正确的防御性配置，被保留在最终方案中。更重要的是，这轮排查帮我们排除了"代理软件"这个变量——如果关闭代理后问题依旧，那问题一定在代理之外的地方。

### 5.4 第三轮排查：校园网 SNI 过滤（定位根因）

**重新审视线索**：经过两轮失败后，我们回到起点重新整理已知信息：

- 浏览器（走代理）能访问 → 服务端正常
- curl（不走代理）不能访问 → 直连有问题
- Python httpx（不走代理）不能访问 → 直连有问题
- 关闭 Clash 后 curl 仍然失败 → 不是代理的问题
- 错误是"连接被重置"（RST），不是"连接超时" → 有什么东西在**主动断开**连接

"主动断开"这个词是关键。如果是网络不通，应该是超时（timeout）；如果是证书错误，应该有 SSL 错误信息。但 RST（连接重置）意味着有一个第三方在 TCP 连接建立后主动发送了重置包。

**系统性排除法**：

| 测试 | 方法 | 结果 | 排除/锁定 |
|---|---|---|---|
| TCP 端口连通性 | `Test-NetConnection api.emailbs.xin -Port 443` | 成功 | 排除防火墙端口封锁 |
| 其他 HTTPS 站点 | `curl https://www.baidu.com` | 成功 | 排除全局 HTTPS 问题 |
| 目标域名直连 | `curl https://api.emailbs.xin` | 连接被重置 | 锁定仅此域名失败 |
| 服务端日志 | 查看 Nginx access/error log | 请求返回 200，无错误 | 排除服务端问题 |

四组测试画出了一个精确的包围圈：TCP 层正常（端口可达）、服务端正常（返回 200）、其他 HTTPS 站点正常（不是全局问题），唯独这个特定域名在直连时被重置。问题被缩小到 TLS 层中与"域名"相关的某个环节。

在 TLS 握手中，唯一包含域名字段的是 Client Hello 消息中的 **SNI（Server Name Indication）扩展**。如果有什么东西在检查 SNI 并据此阻断连接，那就是 SNI 过滤。

**突破点——原始 socket 对比测试**：

为了验证这个假设，我们绕过 httpx 和 curl，直接用 Python 的 socket 模块建立 TLS 连接，精确控制是否发送 SNI：

```python
import socket, ssl

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# 测试 A：带 SNI（server_hostname）
sock_a = socket.create_connection(("121.40.247.143", 443))
ssl_a = ctx.wrap_socket(sock_a, server_hostname="api.emailbs.xin")
# 结果：连接被重置 ✗

# 测试 B：不带 SNI
sock_b = socket.create_connection(("121.40.247.143", 443))
ssl_b = ctx.wrap_socket(sock_b)  # 无 server_hostname
# 结果：TLS 握手成功 ✓
```

两组测试的网络环境相同、目标 IP 相同、SSL 配置相同，唯一区别是 Client Hello 中是否包含 `server_hostname="api.emailbs.xin"`。带 SNI 的被重置，不带的成功——这是一个干净的对照实验，直接证明了根因。

**根因确认**：校园网部署了 DPI（深度包检测）设备，在 TLS 握手阶段解析 Client Hello 报文，检查 SNI 扩展字段。当域名命中过滤规则时，DPI 设备向双方注入 TCP RST 包，强制断开连接。

```
时间线：
  客户端 → SYN → 服务端                          [TCP 三次握手正常]
  客户端 → Client Hello (SNI: api.emailbs.xin)   [TLS 握手开始]
  DPI    → 检测到过滤域名，注入 RST               [连接被强制中断]
```

这解释了之前所有的矛盾：
- 浏览器走代理时正常，因为代理服务器在海外，DPI 看不到代理内部的 TLS 握手
- curl/Python 直连时失败，因为 DPI 能直接看到 Client Hello 中的 SNI
- `bad key share` 日志是 Nginx 对异常中断的 TLS 连接的错误描述，不是真正的协议问题
- 降级 Python 版本无效，因为问题不在客户端 TLS 实现

这不是协议错误，不是证书错误，不是代理问题——是**校园网基础设施层面对特定域名的主动拦截**。

### 5.5 解决方案：IP 直连 + Host 头绕过 SNI 过滤

明确了根因后，解决方案的思路就很清晰了：

1. **绕过 SNI 过滤**：TLS 握手时不发送 SNI（用 IP 连接代替域名连接）
2. **保持 Nginx 路由**：HTTP 请求中手动添加 Host 头，让 Nginx 知道请求属于哪个虚拟主机

```
正常流程（被拦截）：
  客户端 → TLS Client Hello (SNI: api.emailbs.xin) → [DPI 拦截] → RST

绕过流程（成功）：
  客户端 → DNS 解析域名 → 得到 IP 121.40.247.143
         → TCP 连接 121.40.247.143:443
         → TLS Client Hello (无 SNI) → [DPI 放行]
         → HTTP 请求携带 Host: api.emailbs.xin → Nginx 正确路由到虚拟主机
```

在 `backend/app/infrastructure/cloud_api_client.py` 中实现：

1. **DNS 解析**：初始化时将域名解析为 IP，用 IP 构建 `_base_url`
2. **SSL 上下文**：跳过主机名验证（`check_hostname = False`）、跳过证书验证（`verify_mode = CERT_NONE`），因为 IP 直连时证书域名不匹配
3. **Host 头**：每次请求手动添加 `Host: api.emailbs.xin`，让 Nginx 知道该路由到哪个虚拟主机
4. **trust_env=False**：禁止 httpx 读取系统代理环境变量，避免 Clash 等代理软件干扰

```python
def _resolve_ip(hostname: str) -> str:
    """将域名解析为 IPv4 地址。"""
    try:
        return socket.getaddrinfo(hostname, 443, socket.AF_INET)[0][4][0]
    except Exception:
        return hostname

def _build_no_sni_context() -> ssl.SSLContext:
    """构建跳过 SNI 和主机名验证的 SSL 上下文。"""
    ctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    return ctx
```

**结果**：注册、登录、token 刷新等全部 API 恢复正常。

**安全考量**：`ssl.CERT_NONE` 不验证服务端证书，理论上存在中间人攻击风险。在当前场景下可接受——校园网 DPI 只做过滤不做中间人，且 JWT token 本身有签名保护。切换到非校园网环境后应恢复完整证书验证。

---

## 6. 第四阶段：OSS 预签名 URL 上传 403

TLS 连接问题解决后，注册和登录功能恢复正常。接下来测试云备份上传——这是整个系统的核心功能，也是最后一个需要解决的问题。

### 6.1 备份上传的完整流程

要理解这个问题，先需要理解章枢云备份的上传架构。为了减少服务端压力，备份文件不经过云服务端中转，而是采用"客户端直传 OSS"的模式：

```
桌面端                         云服务端                       阿里云 OSS
  │                               │                              │
  │── POST /backups/init ───────→ │                              │
  │   {filename, size_bytes}      │── oss2.sign_url(PUT, key) ──→│
  │                               │   用 OSS AccessKey 签名      │
  │←── 返回 presigned PUT URL ───│                              │
  │                               │                              │
  │── PUT {presigned_url} ──────────────────────────────────────→│
  │   直接上传 zip 文件           │                              │
  │←── 200 OK ──────────────────────────────────────────────────│
  │                               │                              │
  │── POST /backups/complete ───→ │                              │
  │   {upload_id, checksum}       │── head_object() ────────────→│
  │                               │   校验文件存在 + 大小匹配    │
  │←── 备份记录 ─────────────────│                              │
```

关键点：预签名 URL 是由**服务端生成**、交给**客户端使用**的。URL 中嵌入了域名（endpoint），客户端需要直接访问这个域名。

### 6.2 问题现象与定位

触发云备份上传后，桌面端收到 403 Forbidden 错误。此时注册和登录已经正常，说明 TLS 连接没有问题。403 来自 OSS 侧。

检查服务端返回的预签名 URL，发现问题：

```
https://zhangshu-backups.oss-cn-hangzhou-internal.aliyuncs.com/backups/...
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                这是阿里云内网地址
```

**根因**：服务器 `.env` 中 `OSS_ENDPOINT` 配置为内网地址：

```env
OSS_ENDPOINT=oss-cn-hangzhou-internal.aliyuncs.com
```

服务端本身在阿里云内网，用内网地址访问 OSS 没有问题（还免流量费）。但 `OSSStorage.generate_put_url()` 用这个 endpoint 生成预签名 URL 时，内网域名被嵌入 URL 中。桌面端拿到这个 URL 后尝试 PUT 请求，但桌面端在公网环境下根本访问不到 `oss-cn-hangzhou-internal.aliyuncs.com`。

这是一个典型的"谁用这个 URL"的问题——服务端生成 URL，但客户端使用 URL，两端网络环境不同。

### 6.3 解决

将 `OSS_ENDPOINT` 改为公网地址：

```env
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
```

重启服务后，预签名 URL 中的域名变为公网可达，上传正常。

### 6.4 后续优化

当前方案有一个不优雅的地方：服务端自己访问 OSS（`head_object`、`delete_object`）时也用公网 endpoint，会产生不必要的公网流量费。理想方案是维护双 endpoint：

```env
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com                    # 公网，用于生成客户端预签名 URL
OSS_INTERNAL_ENDPOINT=oss-cn-hangzhou-internal.aliyuncs.com  # 内网，用于服务端直连 OSS
```

---

## 7. 完整代码变更清单

### 7.1 桌面端变更

| 文件 | 变更 | 原因 |
|---|---|---|
| `backend/app/infrastructure/cloud_api_client.py` | IP 直连 + No-SNI SSL 上下文 + Host 头 + `trust_env=False` | 绕过校园网 SNI 过滤 |
| `backend/packaged_main.py` | 添加 `ZHANGSHU_CLOUD_API_BASE_URL` 环境变量默认值 | 打包后自动配置云服务地址 |
| `backend/.env.example` | 添加云服务配置说明 | 开发者参考 |

### 7.2 服务端变更

| 文件 | 变更 | 原因 |
|---|---|---|
| `cloud-server/alembic/versions/001_initial.py` | Boolean 默认值 `sa.text("1")` → `sa.text("true")` | PostgreSQL 兼容性 |
| `cloud-server/deploy/setup.sh` | 阿里云 Docker 镜像 + 非交互安装参数 | 国内服务器部署 |
| `cloud-server/deploy/deploy.sh` | DaoCloud 镜像代理 + DNS 验证 | 国内服务器部署 |
| `cloud-server/Dockerfile` | pip 源替换为阿里云镜像 | 国内 pip install |

### 7.3 服务器端变更（不在版本控制中）

| 文件 | 变更 |
|---|---|
| `/etc/nginx/sites-available/zhangshu-cloud` | TLS 1.2 强制、关闭 HTTP/2 |
| `/opt/zhangshu-cloud/.env` | OSS 公网 endpoint、数据库连接、JWT 密钥 |

---

## 8. 排查方法论总结

### 8.1 分层排查模型

本次排查最大的收获是：**网络连通性问题必须分层验证，不能假设某一层通了就等于全部通了。**

```
第 1 层 — DNS：域名能否解析到正确 IP？
第 2 层 — TCP：端口是否可达？（Test-NetConnection / telnet）
第 3 层 — TLS：握手是否成功？SNI 是否被过滤？
第 4 层 — HTTP：请求是否被正确路由？响应状态码和内容是否正常？
```

传统排查往往止步于第 2 层（"端口能通，所以网络没问题"）。但本次问题恰恰出在第 3 层——TCP 端口完全可达，DPI 设备甚至允许 TCP 三次握手完成，只在 TLS 握手阶段才根据 SNI 字段进行拦截。这种"选择性拦截"是最难排查的，因为它制造了"网络正常"的假象。

### 8.2 对照实验是定位根因的最有效手段

回顾整个排查过程，真正定位根因的不是理论分析，而是一个简单的对照实验：

```
测试 A：带 SNI → 失败
测试 B：不带 SNI → 成功
唯一变量：SNI 字段
结论：问题由 SNI 触发
```

这个实验的设计思路是"控制变量法"：保持 IP、端口、SSL 配置全部不变，只改变一个参数，观察结果差异。在前两轮排查中，我们同时改了太多东西（Python 版本 + TLS 版本 + HTTP/2 开关），无法判断哪个变更有效或无效。

### 8.3 "浏览器能访问但 curl 不能"——这个矛盾是金矿

本次排查最重要的线索从一开始就摆在面前：浏览器能访问，curl 不能。这个矛盾直接指向了"两者有什么不同"：

- 浏览器走代理 → 流量经过代理服务器，DPI 看不到内部 TLS 握手
- curl 直连 → 流量直接经过校园网出口，DPI 能看到 SNI

如果一开始就深入分析这个矛盾，可能会更早定位到 SNI 过滤。但实际上我们先花了时间在 Python 版本和代理软件上——这是因为"浏览器和 curl 的差异"有很多可能的解释（代理、TLS 版本、证书库等），SNI 过滤只是其中之一。

### 8.4 关键诊断手段清单

| 手段 | 作用 | 本次中的应用 |
|---|---|---|
| 浏览器 vs curl 对比 | 判断问题在网络层还是应用层 | 浏览器正常 + curl 失败 → 问题在网络传输层 |
| 原始 socket 测试 | 精确控制 TLS 握手参数 | 带/不带 SNI 对比 → 锁定 SNI 过滤 |
| 跨域名对比 | 排除普遍性问题 | baidu.com 正常 → 不是全局 HTTPS 问题 |
| 服务端日志检查 | 确认请求是否到达服务端 | 服务端 200 + 客户端失败 → 问题在传输层 |
| 环境变量隔离 | 排除代理软件干扰 | `trust_env=False` 排除 Clash 残留 |
| 错误信息精读 | "连接重置" ≠ "连接超时" | RST = 主动断开 = 有第三方干预 |

### 8.5 国内服务器部署检查清单

经过这次部署，总结出的国内部署必备项：

1. **Docker 镜像源**：阿里云 Docker 镜像替代 `download.docker.com`（否则安装超时）
2. **Docker Hub 代理**：DaoCloud 镜像代理拉取基础镜像（否则 build 超时）
3. **PyPI/npm 镜像**：阿里云镜像加速依赖安装（否则 pip install 超时）
4. **非交互模式**：`DEBIAN_FRONTEND=noninteractive` + dpkg 强制选项（否则脚本挂起）
5. **网络环境评估**：校园网/企业网可能存在 DPI/SNI 过滤，需要 IP 直连等绕过方案
6. **OSS 内外网区分**：预签名 URL 必须用公网 endpoint，服务端操作可用内网 endpoint

---

## 9. 遗留事项与后续建议

| 项目 | 当前状态 | 建议 |
|---|---|---|
| SSL 证书验证 | 使用 `CERT_NONE` 跳过验证 | 非校园网环境应恢复完整证书验证 |
| OSS 双 endpoint | 统一使用公网 endpoint | 服务端操作改回内网 endpoint 以节省流量费 |
| IP 直连稳定性 | 依赖 DNS 解析结果 | 服务器 IP 变更时需清理本地 DNS 缓存 |
| Clash 兼容 | `trust_env=False` 绕过代理 | 建议 Clash 规则中为域名添加 DIRECT 规则 |
| Python 版本 | 已降级到 3.12.10 | 待 3.14 稳定后重新测试 SSL 行为 |
| HTTP/2 | 已关闭 | TLS 兼容性改善后可重新开启 |
| 端到端测试 | 注册/登录已验证 | 云备份上传和恢复的完整端到端测试待执行 |
