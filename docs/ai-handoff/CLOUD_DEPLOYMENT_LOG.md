# 章枢云服务部署与调试记录

## 概述

本次任务将章枢云 API 服务器部署到阿里云轻量应用服务器（Ubuntu 22.04，2核2G），完成 Docker + PostgreSQL + FastAPI + Nginx + Let's Encrypt SSL 的全套部署，并解决桌面端连接云端 API 时遇到的多个网络和 TLS 问题。

---

## 服务器信息

- **服务器**：阿里云轻量应用服务器，Ubuntu 22.04，2核2G
- **域名**：api.emailbs.xin
- **IP**：121.40.247.143
- **SSL**：Let's Encrypt 证书
- **容器名**：
  - `zhangshu-cloud-cloud-api-1`（FastAPI 应用，端口 9000）
  - `zhangshu-cloud-postgres-1`（PostgreSQL 数据库，端口 5432）
- **Nginx 配置**：`/etc/nginx/sites-available/zhangshu-cloud`
- **应用目录**：`/opt/zhangshu-cloud/`
- **环境变量**：`/opt/zhangshu-cloud/.env`

---

## 部署过程与问题解决

### 1. Docker 安装超时

**问题**：`download.docker.com` 在国内无法访问。

**解决**：切换到阿里云镜像源：

```bash
curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
```

### 2. 交互式提示阻塞脚本

**问题**：`needrestart` 和 `dpkg` 配置冲突弹出交互式提示。

**解决**：

```bash
export DEBIAN_FRONTEND=noninteractive
echo '$nrconf{restart} = "a";' > /etc/needrestart/conf.d/99-auto.conf
apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" ...
```

### 3. Docker 镜像拉取超时

**问题**：Docker Hub 在国内无法访问。

**解决**：使用 DaoCloud 镜像：

```bash
docker pull docker.m.daocloud.io/python:3.12-slim
docker tag docker.m.daocloud.io/python:3.12-slim python:3.12-slim
```

### 4. Alembic 迁移失败

**问题**：PostgreSQL 的 Boolean 默认值不兼容 `sa.text("1")`。

**解决**：修改 `cloud-server/alembic/versions/001_initial.py`：

```python
# 修改前
sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
# 修改后
sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
```

### 5. Python 3.14 TLS 握手失败

**问题**：Python 3.14 的 SSL 模块与 Nginx TLS 1.3 配置不兼容，Nginx 日志显示 `bad key share` 错误。

**解决**：降级到 Python 3.12.10。

- 下载安装：https://www.python.org/downloads/release/python-31210/
- 重建虚拟环境：`py -3.12 -m venv .venv`
- Nginx 端也强制 TLS 1.2：`ssl_protocols TLSv1.2;`

### 6. Clash 代理干扰连接

**问题**：Clash Verge（含 TUN 模式）拦截了 curl 和 Python 的直连流量，即使关闭 Clash 进程后仍有残留影响。

**解决**：关闭 Clash 后问题仍然存在（见下一条 SNI 过滤）。

### 7. 校园网 SNI 过滤（核心问题）

**问题**：即使关闭代理、降级 Python，curl 和 httpx 仍然无法连接 `https://api.emailbs.xin`，TLS 握手阶段被重置（`[WinError 10054]`）。浏览器走代理时正常，`curl` 直连失败。

**排查过程**：
1. 确认 TCP 443 端口可达（`Test-NetConnection` 成功）
2. 确认其他 HTTPS 站点（如 baidu.com）正常
3. 服务器日志显示请求成功返回 200，但客户端收不到响应
4. 原始 socket 测试：带 SNI（`server_hostname`）握手被重置，**不带 SNI 握手成功**

**根本原因**：校园网部署了 DPI（深度包检测）设备，对 `api.emailbs.xin` 进行 SNI 过滤，检测 TLS Client Hello 中的域名标识并重置连接。

**解决**：修改 `backend/app/infrastructure/cloud_api_client.py`，用 IP 直连 + Host 头绕过 SNI 过滤：

```python
def _resolve_ip(hostname: str) -> str:
    """Resolve a hostname to its first IPv4 address."""
    try:
        return socket.getaddrinfo(hostname, 443, socket.AF_INET)[0][4][0]
    except Exception:
        return hostname

def _build_no_sni_context() -> ssl.SSLContext:
    """Build an SSL context that skips hostname verification for IP-based connections."""
    ctx = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.maximum_version = ssl.TLSVersion.TLSv1_2
    return ctx
```

`CloudApiClient.__init__` 中自动将域名解析为 IP：

```python
parsed = urlparse(original_url)
self._hostname = parsed.hostname or ""
if parsed.hostname and parsed.scheme == "https":
    ip = _resolve_ip(parsed.hostname)
    port = f":{parsed.port}" if parsed.port else ""
    self._base_url = f"{parsed.scheme}://{ip}{port}"
else:
    self._base_url = original_url
```

请求时添加 Host 头，确保 Nginx 路由到正确的虚拟主机：

```python
def _headers(self) -> dict[str, str]:
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if self._hostname:
        headers["Host"] = self._hostname
    if self._access_token:
        headers["Authorization"] = f"Bearer {self._access_token}"
    return headers
```

---

## OSS 预签名 URL 问题（待修复）

### 问题

云端备份上传返回 403（Forbidden）。

### 原因

服务器 `/opt/zhangshu-cloud/.env` 中的 `OSS_ENDPOINT` 配置为**内网地址**：

```
OSS_ENDPOINT=oss-cn-hangzhou-internal.aliyuncs.com
```

服务器用这个内网地址生成预签名 URL（presigned URL），但客户端（桌面电脑）无法访问阿里云内网，导致上传失败。

### 解决方案

将 `OSS_ENDPOINT` 改为**公网地址**：

```
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
```

在服务器终端执行：

```bash
sudo sed -i 's/OSS_ENDPOINT=oss-cn-hangzhou-internal.aliyuncs.com/OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com/' /opt/zhangshu-cloud/.env
cd /opt/zhangshu-cloud && docker compose restart cloud-api
```

### 注意事项

- 服务器本身访问 OSS 用内网地址可以免流量费、速度更快
- 但预签名 URL 是给客户端用的，必须用公网地址
- 如果服务器端也需要直传 OSS（如校验 checksum），可以考虑维护两个 endpoint：
  - `OSS_ENDPOINT`（公网，用于生成客户端预签名 URL）
  - `OSS_INTERNAL_ENDPOINT`（内网，用于服务器端操作）

---

## 修改过的文件清单

### 本地（F:\zhangshu\）

| 文件 | 改动 |
|---|---|
| `backend/app/infrastructure/cloud_api_client.py` | IP 直连 + No-SNI SSL + Host 头，绕过校园网 SNI 过滤 |
| `backend/packaged_main.py` | 添加 `ZHANGSHU_CLOUD_API_BASE_URL` 默认值 |
| `backend/.env` | 添加 `ZHANGSHU_CLOUD_API_BASE_URL=https://api.emailbs.xin` |
| `backend/.env.example` | 添加云服务配置说明 |
| `cloud-server/alembic/versions/001_initial.py` | 修复 Boolean 默认值 `sa.text("1")` → `sa.text("true")` |
| `cloud-server/deploy/setup.sh` | 阿里云 Docker 镜像、非交互式安装 |
| `cloud-server/deploy/deploy.sh` | DaoCloud 镜像拉取、DNS 验证 |
| `cloud-server/Dockerfile` | 阿里云 PyPI 镜像 |

### 服务器（api.emailbs.xin）

| 文件 | 改动 |
|---|---|
| `/etc/nginx/sites-available/zhangshu-cloud` | TLS 1.2 强制、去 HTTP/2 |
| `/opt/zhangshu-cloud/.env` | OSS 配置、数据库配置、JWT 密钥 |
| `/opt/zhangshu-cloud/.env`（待改） | `OSS_ENDPOINT` 改为公网地址 |

---

## 当前状态

- [x] 服务器部署完成
- [x] SSL 证书配置完成
- [x] 数据库迁移完成
- [x] 云端注册/登录功能正常
- [x] SNI 过滤绕过方案实现
- [ ] OSS 预签名 URL 公网地址修复（待执行）
- [ ] 云端备份端到端测试
- [ ] 云端恢复测试

---

## 后续建议

1. **OSS 双 endpoint 方案**：服务器端操作（如 head_object、delete_object）继续用内网地址省流量，只有预签名 URL 用公网地址
2. **Python 3.14 兼容性**：关注 Python 3.14 正式版发布后的 SSL 模块变化，可能需要重新测试
3. **DNS 缓存**：IP 直连依赖 DNS 解析结果，如果服务器 IP 变更需要清理本地 DNS 缓存
4. **Clash 规则**：建议在 Clash Verge 中为 `api.emailbs.xin` 添加 DIRECT 规则，避免代理干扰
5. **Nginx HTTP/2**：当前关闭了 HTTP/2，待 Python SSL 兼容性改善后可重新开启
