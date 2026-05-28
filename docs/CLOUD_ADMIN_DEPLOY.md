# Cloud Admin 部署指南

本文档描述如何将 `cloud-admin` 管理后台部署到生产服务器。

## 前置条件

- 服务器已安装 Nginx（1.18+）
- `cloud-server` 后端 API 已在服务器上运行（默认监听 `127.0.0.1:8000`）
- 服务器有公网域名并已配置 DNS（如 `admin.example.com`）
- 已获取 SSL 证书（推荐使用 Let's Encrypt）

## 1. 构建前端

在开发机上执行：

```bash
cd cloud-admin
npm install
npm run build
```

构建产物输出到 `cloud-admin/dist/`。

## 2. 上传到服务器

```bash
# 方式 1: scp
scp -r dist/* user@server:/var/www/cloud-admin/

# 方式 2: rsync（增量同步，推荐）
rsync -avz --delete dist/ user@server:/var/www/cloud-admin/
```

## 3. 配置 Nginx

将 `deploy/nginx/cloud-admin.conf` 上传到服务器：

```bash
scp deploy/nginx/cloud-admin.conf user@server:/tmp/
ssh user@server 'sudo mv /tmp/cloud-admin.conf /etc/nginx/sites-available/cloud-admin'
ssh user@server 'sudo ln -sf /etc/nginx/sites-available/cloud-admin /etc/nginx/sites-enabled/'
```

**重要**：修改配置文件中的以下字段：

- `server_name` — 替换为你的域名
- `ssl_certificate` / `ssl_certificate_key` — 替换为证书路径
- `proxy_pass` — 如果后端不在 8000 端口，修改端口号

验证配置并重启 Nginx：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 4. SSL 证书（Let's Encrypt）

如果尚未获取证书：

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d admin.example.com
```

Certbot 会自动修改 Nginx 配置并配置自动续期。

## 5. 环境变量

`cloud-admin` 构建时的环境变量（可选）：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `VITE_API_BASE_URL` | （空，使用同源代理） | API 基础 URL，留空则通过 Nginx 代理 |

如需自定义 API 地址：

```bash
VITE_API_BASE_URL=https://api.example.com npm run build
```

## 6. 更新部署

```bash
# 开发机
cd cloud-admin && npm run build
rsync -avz --delete dist/ user@server:/var/www/cloud-admin/

# 无需重启 Nginx，静态文件直接覆盖即可
```

## 7. 验证清单

- [ ] 访问 `https://admin.example.com` 显示登录页
- [ ] 登录后侧边栏正常显示
- [ ] API 请求通过 Nginx 代理到后端
- [ ] Cookie 在 HTTPS 下正常设置（`Secure` 标志）
- [ ] 页面刷新不出现 404（SPA fallback 生效）

## 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 刷新页面 404 | Nginx 未配置 `try_files` | 检查 `location /` 块 |
| API 返回 502 | 后端未运行或端口不对 | 检查 `proxy_pass` 目标 |
| Cookie 不设置 | 非 HTTPS 环境下 `Secure` cookie 被拒绝 | 确保 SSL 配置正确 |
| 静态资源 404 | `dist/` 未正确上传 | 重新 rsync |
