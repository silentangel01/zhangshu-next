#!/bin/bash
set -e

# ============================================================
# 章枢云 — SSL 证书申请脚本
# DNS 生效后运行此脚本启用 HTTPS
# ============================================================

DOMAIN="${ZHANGSHU_DOMAIN:-api.emailbs.xin}"
EMAIL="${ZHANGSHU_EMAIL:-admin@example.com}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

echo "申请 SSL 证书: ${DOMAIN}"

# 检查 DNS
RESOLVED_IP=$(ping -c 1 -W 3 "${DOMAIN}" 2>/dev/null | head -1 | grep -oP '\d+\.\d+\.\d+\.\d+' || echo "")
SERVER_IP=$(curl -s http://ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')

if [[ "${RESOLVED_IP}" != "${SERVER_IP}" ]]; then
    err "DNS 未生效: ${DOMAIN} 解析到 ${RESOLVED_IP:-无}，本机 IP: ${SERVER_IP}"
    err "请先在域名控制台添加 A 记录"
    exit 1
fi

log "DNS 已生效: ${DOMAIN} -> ${SERVER_IP}"

# 申请证书
mkdir -p /var/www/certbot

if [[ -d "/etc/letsencrypt/live/${DOMAIN}" ]]; then
    warn "证书已存在，跳过"
else
    certbot certonly --webroot \
        --webroot-path=/var/www/certbot \
        --email "${EMAIL}" \
        --agree-tos \
        --no-eff-email \
        --non-interactive \
        -d "${DOMAIN}"
    log "证书申请成功"
fi

# 部署 HTTPS 配置
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

systemctl enable certbot.timer 2>/dev/null || true
systemctl start certbot.timer 2>/dev/null || true

log "HTTPS 已启用: https://${DOMAIN}"
