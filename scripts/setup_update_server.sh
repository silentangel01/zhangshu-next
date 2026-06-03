#!/bin/bash
###############################################################################
# 章枢更新服务器 HTTPS 配置脚本
#
# 目标域名:
#   updates.zhangshu.xin    — 更新 manifest
#   downloads.zhangshu.xin  — 安装包下载
#   updates.emailbs.xin     — 备用更新 manifest
#
# 服务器: 121.40.247.143 (Ubuntu + Nginx)
#
# 使用方法:
#   ssh root@121.40.247.143
#   # 将本脚本内容粘贴到终端执行
#
# 安全边界:
#   - 只配置 updates.zhangshu.xin / downloads.zhangshu.xin / updates.emailbs.xin
#   - 不动 api.emailbs.xin 的现有业务配置
#   - 不删除已有 Nginx 配置文件
#   - nginx -t 失败时自动回滚并退出
#   - HTTP 完整路径测试失败时不申请 HTTPS
#   - updates.emailbs.xin DNS 未生效时只申请另外两个域名的证书
#   - 只创建 test.txt 和 latest.json 测试文件
###############################################################################
set -euo pipefail

PASS() { echo -e "\033[32m[PASS]\033[0m $*"; }
WARN() { echo -e "\033[33m[WARN]\033[0m $*"; }
FAIL() { echo -e "\033[31m[FAIL]\033[0m $*"; }

CONF_FILE="/etc/nginx/conf.d/zhangshu-static.conf"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"

echo ""
echo "=========================================="
echo "  章枢更新服务器 HTTPS 配置"
echo "=========================================="
echo ""

###############################################################################
# Step 1: 确认环境
###############################################################################
echo "── Step 1: 确认服务器环境 ──"
echo "  Hostname : $(hostname)"
echo "  User     : $(whoami)"

if ! command -v nginx &>/dev/null; then
  FAIL "Nginx 未安装"; exit 1
fi
NGINX_VER=$(nginx -v 2>&1)
echo "  Nginx    : $NGINX_VER"

if ! systemctl is-active --quiet nginx; then
  FAIL "Nginx 未运行"; exit 1
fi
PASS "Nginx 运行中"

echo "  端口监听:"
ss -ltnp | grep -E ':80|:443' | sed 's/^/    /' || echo "    (无 80/443 监听)"
echo ""

###############################################################################
# Step 2: 备份 Nginx
###############################################################################
echo "── Step 2: 备份 Nginx 配置 ──"
BACKUP_DIR="/root/nginx-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

nginx -T > "$BACKUP_DIR/nginx.full.conf" 2>&1
cp -a /etc/nginx/conf.d "$BACKUP_DIR/conf.d" 2>/dev/null || true
cp -a /etc/nginx/sites-enabled "$BACKUP_DIR/sites-enabled" 2>/dev/null || true
cp -a /etc/nginx/sites-available "$BACKUP_DIR/sites-available" 2>/dev/null || true

# 单独备份目标文件（如果已存在）
if [[ -f "$CONF_FILE" ]]; then
  cp "$CONF_FILE" "$BACKUP_DIR/zhangshu-static.conf.bak"
  PASS "已备份现有 zhangshu-static.conf"
fi

PASS "备份完成: $BACKUP_DIR"
echo ""

###############################################################################
# Step 3: DNS 检查
###############################################################################
echo "── Step 3: DNS 解析检查 ──"
SKIP_EMAILBS=0

DNS_ZS=$(getent hosts updates.zhangshu.xin 2>/dev/null | awk '{print $1}') || DNS_ZS=""
DNS_DL=$(getent hosts downloads.zhangshu.xin 2>/dev/null | awk '{print $1}') || DNS_DL=""
DNS_EB=$(getent hosts updates.emailbs.xin 2>/dev/null | awk '{print $1}') || DNS_EB=""

echo "  updates.zhangshu.xin   -> ${DNS_ZS:-未解析}"
echo "  downloads.zhangshu.xin -> ${DNS_DL:-未解析}"
echo "  updates.emailbs.xin    -> ${DNS_EB:-未解析}"

if [[ -z "$DNS_ZS" ]]; then FAIL "updates.zhangshu.xin DNS 未解析，无法继续"; exit 1; fi
if [[ -z "$DNS_DL" ]]; then FAIL "downloads.zhangshu.xin DNS 未解析，无法继续"; exit 1; fi

[[ "$DNS_ZS" != "121.40.247.143" ]] && WARN "updates.zhangshu.xin 未指向 121.40.247.143"
[[ "$DNS_DL" != "121.40.247.143" ]] && WARN "downloads.zhangshu.xin 未指向 121.40.247.143"

if [[ -z "$DNS_EB" || "$DNS_EB" != "121.40.247.143" ]]; then
  WARN "updates.emailbs.xin DNS 未生效或未指向本机，将跳过该域名证书"
  SKIP_EMAILBS=1
else
  PASS "三个域名 DNS 均已生效"
fi

UPDATE_SERVER_NAMES="updates.zhangshu.xin"
if [[ "$SKIP_EMAILBS" -eq 0 ]]; then
  UPDATE_SERVER_NAMES="$UPDATE_SERVER_NAMES updates.emailbs.xin"
fi
echo ""

###############################################################################
# Step 4: 创建测试静态文件
###############################################################################
echo "── Step 4: 创建测试文件 ──"
mkdir -p /var/www/zhangshu-updates/zhangshu/stable/windows-x64
mkdir -p /var/www/zhangshu-downloads/zhangshu/releases

printf 'hello update\n' > /var/www/zhangshu-downloads/zhangshu/releases/test.txt
TEST_SHA=$(sha256sum /var/www/zhangshu-downloads/zhangshu/releases/test.txt | awk '{print $1}')
TEST_SIZE=$(stat -c%s /var/www/zhangshu-downloads/zhangshu/releases/test.txt)

cat > /var/www/zhangshu-updates/zhangshu/stable/windows-x64/latest.json <<MANIFEST_EOF
{
  "schemaVersion": 1,
  "channel": "stable",
  "platform": "windows",
  "arch": "x64",
  "version": "0.0.1",
  "minSupportedVersion": "0.0.1",
  "publishedAt": "2026-06-02T00:00:00Z",
  "installer": {
    "url": "https://downloads.zhangshu.xin/zhangshu/releases/test.txt",
    "sha256": "${TEST_SHA}",
    "sizeBytes": ${TEST_SIZE}
  },
  "releaseNotes": ["测试更新入口"],
  "critical": false
}
MANIFEST_EOF

chown -R root:root /var/www/zhangshu-updates /var/www/zhangshu-downloads
find /var/www/zhangshu-updates /var/www/zhangshu-downloads -type d -exec chmod 755 {} \;
find /var/www/zhangshu-updates /var/www/zhangshu-downloads -type f -exec chmod 644 {} \;

PASS "测试文件已创建"
echo "  SHA256 : $TEST_SHA"
echo "  Size   : $TEST_SIZE bytes"
echo ""

###############################################################################
# Step 5: 写入 Nginx 配置
###############################################################################
echo "── Step 5: 写入 Nginx 配置 ──"

# 如果文件已存在，先单独备份
if [[ -f "$CONF_FILE" ]]; then
  cp "$CONF_FILE" "${CONF_FILE}.prev"
fi

cat > "$CONF_FILE" <<'NGINX_EOF'
# ── 章枢静态文件服务 ──
# 更新 manifest (主域名 + 备用域名)
server {
    listen 80;
    server_name __UPDATE_SERVER_NAMES__;

    root /var/www/zhangshu-updates;

    location = / {
        return 404;
    }

    location / {
        try_files $uri =404;
    }

    location = /zhangshu/stable/windows-x64/latest.json {
        default_type application/json;
        add_header Cache-Control "no-cache, no-store, must-revalidate" always;
        try_files $uri =404;
    }
}

# 安装包下载
server {
    listen 80;
    server_name downloads.zhangshu.xin;

    root /var/www/zhangshu-downloads;

    location = / {
        return 404;
    }

    location / {
        try_files $uri =404;
    }

    location ~* \.(exe|msi|zip|txt)$ {
        add_header Cache-Control "public, max-age=31536000, immutable" always;
        try_files $uri =404;
    }
}
NGINX_EOF

sed -i "s/__UPDATE_SERVER_NAMES__/${UPDATE_SERVER_NAMES}/" "$CONF_FILE"

PASS "配置已写入: $CONF_FILE"
echo ""

###############################################################################
# Step 6: 语法检查 + 重载（失败则回滚）
###############################################################################
echo "── Step 6: Nginx 语法检查 ──"

ROLLBACK() {
  FAIL "正在回滚..."
  if [[ -f "$BACKUP_DIR/zhangshu-static.conf.bak" ]]; then
    # 恢复到之前已有的配置
    cp "$BACKUP_DIR/zhangshu-static.conf.bak" "$CONF_FILE"
    PASS "已恢复到之前的 zhangshu-static.conf"
  else
    # 之前不存在该文件，删除新增的
    rm -f "$CONF_FILE"
    PASS "已删除新增的 zhangshu-static.conf"
  fi
  if nginx -t 2>&1 | sed 's/^/    /'; then
    systemctl reload nginx
    PASS "Nginx 已恢复并重载"
  else
    FAIL "回滚后 nginx -t 仍失败，请手动检查 $BACKUP_DIR"
  fi
}

if ! nginx -t 2>&1 | sed 's/^/    /'; then
  ROLLBACK
  FAIL "nginx -t 失败，已回滚退出"
  exit 1
fi

systemctl reload nginx
PASS "Nginx 已重载"
echo ""

###############################################################################
# Step 7: HTTP 完整路径测试
###############################################################################
echo "── Step 7: HTTP 完整路径测试 ──"

http_code() {
  local url="$1"
  local code
  code=$(curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 10 --max-time 15 "$url" 2>/dev/null) || code="000"
  echo "$code"
}

is_http_reachable() {
  local code="$1"
  [[ "$code" == "200" || "$code" == "301" || "$code" == "302" ]]
}

HTTP_ZS=$(http_code "http://updates.zhangshu.xin/zhangshu/stable/windows-x64/latest.json")
HTTP_DL=$(http_code "http://downloads.zhangshu.xin/zhangshu/releases/test.txt")

echo "  updates.zhangshu.xin   -> HTTP $HTTP_ZS"
echo "  downloads.zhangshu.xin -> HTTP $HTTP_DL"

if [[ "$SKIP_EMAILBS" -eq 0 ]]; then
  HTTP_EB=$(http_code "http://updates.emailbs.xin/zhangshu/stable/windows-x64/latest.json")
  echo "  updates.emailbs.xin    -> HTTP $HTTP_EB"
  if is_http_reachable "$HTTP_EB"; then
    HTTP_EMAILBS_EXPECTED="$HTTP_EB"
  else
    WARN "updates.emailbs.xin HTTP 完整路径未通过，将暂时跳过备用域名证书申请"
    SKIP_EMAILBS=1
    HTTP_EMAILBS_EXPECTED="200"
    sed -i 's/ updates.emailbs.xin//' "$CONF_FILE"
    if nginx -t 2>&1 | sed 's/^/    /'; then
      systemctl reload nginx
      PASS "已从当前 Nginx 配置中暂时移除 updates.emailbs.xin 并重载"
    else
      ROLLBACK
      FAIL "移除 updates.emailbs.xin 后 nginx -t 失败，已回滚退出"
      exit 1
    fi
  fi
else
  HTTP_EMAILBS_EXPECTED="200"
fi

# 验证内容
echo ""
echo "  manifest 内容预览:"
curl -sS --connect-timeout 10 "http://updates.zhangshu.xin/zhangshu/stable/windows-x64/latest.json" 2>/dev/null | head -3 | sed 's/^/    /' || true

if ! is_http_reachable "$HTTP_ZS" || ! is_http_reachable "$HTTP_DL" || ! is_http_reachable "$HTTP_EMAILBS_EXPECTED"; then
  echo ""
  ROLLBACK
  FAIL "HTTP 测试未通过 (期望 200/301/302)，已回滚退出"
  FAIL "请检查:"
  echo "  - 阿里云安全组是否放通 80 端口入站"
  echo "  - 服务器防火墙: ufw status / iptables -L"
  exit 1
fi

if [[ "$HTTP_ZS" != "200" || "$HTTP_DL" != "200" || "$HTTP_EMAILBS_EXPECTED" != "200" ]]; then
  WARN "部分 HTTP 请求返回 301/302，说明已有 HTTPS 重定向；将继续验证 HTTPS 完整路径"
else
  PASS "HTTP 测试通过"
fi
echo ""

###############################################################################
# Step 8: 申请 HTTPS 证书
###############################################################################
echo "── Step 8: 申请 Let's Encrypt HTTPS 证书 ──"

if ! command -v certbot &>/dev/null; then
  echo "  Certbot 未安装，正在安装..."
  apt-get update -qq
  apt-get install -y -qq certbot python3-certbot-nginx
fi

echo "  Certbot: $(certbot --version 2>&1)"

CERTBOT_DOMAINS="-d updates.zhangshu.xin -d downloads.zhangshu.xin"
if [[ "$SKIP_EMAILBS" -eq 0 ]]; then
  CERTBOT_DOMAINS="$CERTBOT_DOMAINS -d updates.emailbs.xin"
fi

echo "  申请域名: $CERTBOT_DOMAINS"

CERTBOT_ARGS=(--nginx --expand)
for domain_arg in $CERTBOT_DOMAINS; do
  CERTBOT_ARGS+=("$domain_arg")
done
CERTBOT_ARGS+=(--non-interactive --agree-tos --redirect)
if [[ -n "$CERTBOT_EMAIL" ]]; then
  CERTBOT_ARGS+=(--email "$CERTBOT_EMAIL")
else
  WARN "未设置 CERTBOT_EMAIL，将使用 --register-unsafely-without-email"
  CERTBOT_ARGS+=(--register-unsafely-without-email)
fi

if ! certbot "${CERTBOT_ARGS[@]}"; then
  FAIL "Certbot 证书申请失败"
  FAIL "可能原因: DNS 未完全传播、80 端口未放通、Let's Encrypt 限流"
  ROLLBACK
  exit 1
fi

PASS "HTTPS 证书申请成功"

echo "  正在执行 certbot renew --dry-run..."
if timeout 180 certbot renew --dry-run; then
  PASS "certbot renew --dry-run 通过"
  CERTBOT_DRY_RUN="通过"
else
  WARN "certbot renew --dry-run 未通过或超时，请稍后手动复查"
  CERTBOT_DRY_RUN="未通过或超时"
fi
echo ""

###############################################################################
# Step 9: HTTPS 测试
###############################################################################
echo "── Step 9: HTTPS 完整路径测试 ──"

HTTPS_ZS=$(http_code "https://updates.zhangshu.xin/zhangshu/stable/windows-x64/latest.json")
HTTPS_DL=$(http_code "https://downloads.zhangshu.xin/zhangshu/releases/test.txt")

echo "  https://updates.zhangshu.xin/...latest.json -> HTTPS $HTTPS_ZS"
echo "  https://downloads.zhangshu.xin/...test.txt  -> HTTPS $HTTPS_DL"

if [[ "$SKIP_EMAILBS" -eq 0 ]]; then
  HTTPS_EB=$(http_code "https://updates.emailbs.xin/zhangshu/stable/windows-x64/latest.json")
  echo "  https://updates.emailbs.xin/...latest.json  -> HTTPS $HTTPS_EB"
  HTTPS_EMAILBS_EXPECTED="$HTTPS_EB"
else
  HTTPS_EMAILBS_EXPECTED="200"
fi

echo ""
echo "  manifest HTTPS 内容预览:"
curl -sS --connect-timeout 10 "https://updates.zhangshu.xin/zhangshu/stable/windows-x64/latest.json" 2>/dev/null | head -5 | sed 's/^/    /' || true

echo ""
echo "  下载文件 HTTPS 内容:"
curl -sS --connect-timeout 10 "https://downloads.zhangshu.xin/zhangshu/releases/test.txt" 2>/dev/null | sed 's/^/    /' || true

echo ""

if [[ "$HTTPS_ZS" != "200" || "$HTTPS_DL" != "200" || "$HTTPS_EMAILBS_EXPECTED" != "200" ]]; then
  FAIL "HTTPS 测试未通过"
  FAIL "请检查阿里云安全组是否放通 443 端口入站"
  exit 1
fi

PASS "HTTPS 测试通过"
echo ""

###############################################################################
# Step 10: 验证旧云服务
###############################################################################
echo "── Step 10: 验证 api.emailbs.xin ──"
API_CODE=$(http_code "https://api.emailbs.xin/health")
echo "  https://api.emailbs.xin/health -> $API_CODE"

if [[ "$API_CODE" =~ ^(200|301|302|404)$ ]]; then
  PASS "旧云服务响应正常"
else
  WARN "旧云服务返回 $API_CODE，请确认是否受影响"
fi
echo ""

###############################################################################
# Step 11: 证书信息
###############################################################################
echo "── 证书信息 ──"
echo | openssl s_client -connect updates.zhangshu.xin:443 -servername updates.zhangshu.xin 2>/dev/null \
  | openssl x509 -noout -subject -dates -ext subjectAltName 2>/dev/null | sed 's/^/  /' || WARN "无法读取证书信息"
echo ""

###############################################################################
# 执行报告
###############################################################################
echo "=========================================="
echo "  执行报告"
echo "=========================================="
echo ""
echo "备份目录        : $BACKUP_DIR"
echo ""
echo "DNS 解析:"
echo "  updates.zhangshu.xin   : ${DNS_ZS:-未解析}"
echo "  downloads.zhangshu.xin : ${DNS_DL:-未解析}"
echo "  updates.emailbs.xin    : ${DNS_EB:-未解析}"
echo ""
echo "nginx -t        : 通过"
echo "Nginx 重载      : 成功"
echo ""
echo "HTTP 测试:"
echo "  updates.zhangshu.xin   : $HTTP_ZS"
echo "  downloads.zhangshu.xin : $HTTP_DL"
if [[ "$SKIP_EMAILBS" -eq 0 ]]; then
  echo "  updates.emailbs.xin    : $HTTP_EB"
else
  echo "  updates.emailbs.xin    : 跳过 (DNS 未生效)"
fi
echo ""
echo "HTTPS 测试:"
echo "  updates.zhangshu.xin   : $HTTPS_ZS"
echo "  downloads.zhangshu.xin : $HTTPS_DL"
if [[ "$SKIP_EMAILBS" -eq 0 ]]; then
  echo "  updates.emailbs.xin    : $HTTPS_EB"
else
  echo "  updates.emailbs.xin    : 跳过 (DNS 未生效)"
fi
echo ""
echo "api.emailbs.xin : $API_CODE"
echo "certbot dry-run : ${CERTBOT_DRY_RUN:-未执行}"
echo ""
echo "新增服务器文件:"
echo "  $CONF_FILE"
echo "  /var/www/zhangshu-updates/zhangshu/stable/windows-x64/latest.json"
echo "  /var/www/zhangshu-downloads/zhangshu/releases/test.txt"
echo ""

if [[ "$SKIP_EMAILBS" -eq 1 ]]; then
  echo "=========================================="
  echo "  未完成: updates.emailbs.xin"
  echo "=========================================="
  echo ""
  echo "原因: DNS 尚未解析到 121.40.247.143"
  echo ""
  echo "DNS 生效后，在服务器上执行以下命令补申请证书:"
  echo ""
  echo "  certbot --nginx --expand \\"
  echo "    -d updates.zhangshu.xin \\"
  echo "    -d downloads.zhangshu.xin \\"
  echo "    -d updates.emailbs.xin \\"
  echo "    --non-interactive --agree-tos --redirect"
  echo ""
  echo "补完后验证:"
  echo "  curl -I https://updates.emailbs.xin/zhangshu/stable/windows-x64/latest.json"
  echo ""
fi

echo "=========================================="
echo "  配置完成"
echo "=========================================="
