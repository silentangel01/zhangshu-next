#!/bin/bash
set -e

# ============================================================
# 章枢云 API — 应用部署脚本 (v2)
# ============================================================
# 用法: bash deploy/deploy.sh
#
# 功能:
#   1. 生成 .env 配置（自动生成密钥和密码）
#   2. 配置 Docker 镜像加速
#   3. 构建并启动容器
#   4. 配置 Nginx 反向代理
#   5. 申请 SSL 证书（可选，DNS 未生效时跳过）
#   6. 验证服务健康状态
# ============================================================

export DEBIAN_FRONTEND=noninteractive

# ---------- 配置 ----------
APP_DIR="/opt/zhangshu-cloud"
DOMAIN="${ZHANGSHU_DOMAIN:-api.emailbs.xin}"
EMAIL="${ZHANGSHU_EMAIL:-admin@example.com}"

# ---------- 颜色 ----------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

# ---------- 检查环境 ----------
if ! command -v docker &>/dev/null; then
    err "Docker 未安装，请先运行 deploy/setup.sh"
    exit 1
fi

echo ""
echo "========================================="
echo "  章枢云 API 部署"
echo "  应用目录: ${APP_DIR}"
echo "  目标域名: ${DOMAIN}"
echo "  管理员邮箱: ${EMAIL}"
echo "========================================="
echo ""

# ---------- 1. 生成 .env 文件 ----------
if [[ -f "${APP_DIR}/.env" ]]; then
    warn ".env 文件已存在，跳过生成"
else
    log "生成 .env 配置文件..."

    JWT_SECRET=$(openssl rand -hex 32)
    DB_PASSWORD=$(openssl rand -base64 24 | tr -d '=+/' | head -c 20)

    cat > "${APP_DIR}/.env" << EOF
# ============================================================
# 章枢云 API 环境配置
# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')
# ============================================================

# --- 数据库 ---
DATABASE_URL=postgresql+psycopg://zhangshu:${DB_PASSWORD}@postgres:5432/zhangshu_cloud
POSTGRES_USER=zhangshu
POSTGRES_PASSWORD=${DB_PASSWORD}
POSTGRES_DB=zhangshu_cloud

# --- JWT ---
JWT_SECRET_KEY=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# --- 密码哈希 ---
BCRYPT_ROUNDS=12

# --- 阿里云 OSS ---
OSS_ACCESS_KEY_ID=your-access-key-id
OSS_ACCESS_KEY_SECRET=your-access-key-secret
OSS_BUCKET_NAME=zhangshu-backups
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_PRESIGNED_URL_EXPIRE_SECONDS=1800

# --- 备份限制 ---
MAX_BACKUP_SIZE_BYTES=524288000

# --- CORS ---
CORS_ORIGINS=http://localhost:5180,http://127.0.0.1:5180

# --- 生产安全 ---
ENVIRONMENT=production
FORCE_HTTPS=true
LOG_LEVEL=INFO
ACCESS_LOG_JSON=true
RATE_LIMIT_LOGIN_PER_5M=10
RATE_LIMIT_BACKUP_INIT_PER_HOUR=30
DEFAULT_STORAGE_QUOTA_BYTES=1073741824
DEFAULT_BACKUP_COUNT_QUOTA=100

# --- 域名 ---
DOMAIN=${DOMAIN}
EOF

    chmod 600 "${APP_DIR}/.env"
    log ".env 已生成"
    warn "稍后请编辑 .env 填入阿里云 OSS AccessKey:"
    echo "     nano ${APP_DIR}/.env"
fi

# ---------- 2. 预拉取基础镜像（阿里云容器镜像） ----------
log "预拉取基础镜像..."
ALIYUN_REGISTRY="registry.cn-hangzhou.aliyuncs.com/library"

for image in "python:3.12-slim" "postgres:16-alpine"; do
    if docker image inspect "${image}" &>/dev/null; then
        warn "镜像 ${image} 已存在，跳过"
    else
        docker pull "${ALIYUN_REGISTRY}/${image}" && \
        docker tag "${ALIYUN_REGISTRY}/${image}" "${image}"
    fi
done
log "基础镜像准备完成"

# ---------- 3. 构建并启动 Docker 容器 ----------
cd "${APP_DIR}"

log "构建 Docker 镜像（首次构建可能需要 2-5 分钟）..."
docker compose build 2>&1 | tail -5

log "启动容器..."
docker compose up -d

# ---------- 4. 等待服务就绪 ----------
log "等待服务启动..."
RETRIES=30
HEALTHY=false
for i in $(seq 1 $RETRIES); do
    if curl -sf http://127.0.0.1:9000/health > /dev/null 2>&1; then
        HEALTHY=true
        break
    fi
    if [[ $i -eq $RETRIES ]]; then
        err "服务启动超时"
        echo ""
        echo "查看日志排查问题:"
        docker compose logs --tail=20
        exit 1
    fi
    echo -n "."
    sleep 3
done

if $HEALTHY; then
    log "服务已就绪!"
fi

# ---------- 5. 配置 Nginx 反向代理 ----------
log "配置 Nginx 反向代理..."

# 先写 HTTP-only 配置
cat > "/etc/nginx/sites-available/zhangshu-cloud" << NGINX_CONF
server {
    listen 80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://127.0.0.1:9000;
        access_log off;
    }
}
NGINX_CONF

mkdir -p /var/www/certbot

ln -sf /etc/nginx/sites-available/zhangshu-cloud /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx
log "Nginx HTTP 配置已生效"

# ---------- 6. 申请 SSL 证书（可选）----------
DNS_READY=false
if ping -c 1 -W 3 "${DOMAIN}" &>/dev/null; then
    RESOLVED_IP=$(ping -c 1 -W 3 "${DOMAIN}" | head -1 | grep -oP '\d+\.\d+\.\d+\.\d+' || echo "")
    SERVER_IP=$(curl -s http://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
    if [[ "${RESOLVED_IP}" == "${SERVER_IP}" ]]; then
        DNS_READY=true
    fi
fi

if $DNS_READY; then
    log "DNS 已生效，申请 SSL 证书..."
    if [[ -d "/etc/letsencrypt/live/${DOMAIN}" ]]; then
        warn "SSL 证书已存在，跳过"
    else
        certbot certonly --webroot \
            --webroot-path=/var/www/certbot \
            --email "${EMAIL}" \
            --agree-tos \
            --no-eff-email \
            --non-interactive \
            -d "${DOMAIN}" || {
            warn "SSL 证书申请失败，继续使用 HTTP"
            warn "稍后可手动运行: certbot certonly --webroot -w /var/www/certbot -d ${DOMAIN}"
        }
    fi

    # 如果证书存在，部署 HTTPS 配置
    if [[ -d "/etc/letsencrypt/live/${DOMAIN}" ]]; then
        cat > "/etc/nginx/sites-available/zhangshu-cloud" << HTTPS_CONF
server {
    listen 80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name ${DOMAIN};

    ssl_certificate     /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://127.0.0.1:9000;
        access_log off;
    }
}
HTTPS_CONF

        nginx -t
        systemctl reload nginx

        # 证书自动续期
        systemctl enable certbot.timer 2>/dev/null || true
        systemctl start certbot.timer 2>/dev/null || true

        log "SSL 证书 + HTTPS 已生效"
    fi
else
    warn "DNS 未生效 (${DOMAIN} 未解析到本机 IP)，跳过 SSL"
    warn "DNS 生效后运行: bash deploy/enable-ssl.sh"
fi

# ---------- 7. 最终验证 ----------
echo ""
echo "========================================="
echo -e "  ${GREEN}部署完成!${NC}"
echo "========================================="
echo ""

# 本地健康检查 (use /ready for full check)
HEALTH=$(curl -sf http://127.0.0.1:9000/ready 2>/dev/null || echo "FAILED")
if echo "${HEALTH}" | grep -q '"ok"'; then
    log "本地健康检查通过: ${HEALTH}"
else
    warn "本地健康检查未通过"
    docker compose ps
fi

# 远程健康检查
if $DNS_READY; then
    REMOTE=$(curl -sf "http://${DOMAIN}/health" 2>/dev/null || echo "FAILED")
    if echo "${REMOTE}" | grep -q '"ok"'; then
        log "远程健康检查通过: http://${DOMAIN}/health"
    else
        warn "远程健康检查未通过，DNS 可能还在传播中"
    fi
fi

echo ""
echo "  访问地址:  http://${DOMAIN}/docs"
if $DNS_READY && [[ -d "/etc/letsencrypt/live/${DOMAIN}" ]]; then
    echo "  HTTPS:     https://${DOMAIN}/docs"
fi
echo ""
echo "常用命令:"
echo "  查看日志:   cd ${APP_DIR} && docker compose logs -f cloud-api"
echo "  重启服务:   cd ${APP_DIR} && docker compose restart"
echo "  查看状态:   cd ${APP_DIR} && docker compose ps"
echo "  备份数据库: bash deploy/backup-db.sh"
echo ""
echo -e "${YELLOW}⚠  重要：请编辑 .env 填入 OSS AccessKey:${NC}"
echo "  nano ${APP_DIR}/.env"
echo "  docker compose restart"
echo ""
