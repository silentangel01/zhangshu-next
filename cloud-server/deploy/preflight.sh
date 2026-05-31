#!/usr/bin/env bash
# ============================================================
# 章枢云 API — 部署前检查脚本 (Preflight)
# ============================================================
# 用法: bash deploy/preflight.sh
#
# 检查项目:
#   1. .env 必填项
#   2. JWT_SECRET_KEY 非默认
#   3. OSS 端点
#   4. Docker Compose 配置
#   5. PostgreSQL 连接 + 非 SQLite
#   6. Redis 连接
#   7. Nginx 限流配置
#   8. Worker × Pool 连接数
#   9. 服务健康检查
#  10. 磁盘空间
# ============================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/zhangshu-cloud}"
DOMAIN="${ZHANGSHU_DOMAIN:-}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASS=0
WARN=0
FAIL=0

pass() { echo -e "  ${GREEN}[PASS]${NC} $*"; PASS=$((PASS + 1)); }
warn() { echo -e "  ${YELLOW}[WARN]${NC} $*"; WARN=$((WARN + 1)); }
fail() { echo -e "  ${RED}[FAIL]${NC} $*"; FAIL=$((FAIL + 1)); }

echo ""
echo "========================================="
echo "  章枢云 API 部署前检查"
echo "  时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="
echo ""

cd "${APP_DIR}"

# ---------- 1. .env 文件 ----------
echo "[1/10] 环境配置文件"
if [[ -f .env ]]; then
    pass ".env 文件存在"

    REQUIRED_VARS=(
        "DATABASE_URL"
        "JWT_SECRET_KEY"
        "OSS_ACCESS_KEY_ID"
        "OSS_ACCESS_KEY_SECRET"
        "OSS_BUCKET_NAME"
        "OSS_ENDPOINT"
        "CORS_ORIGINS"
    )

    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "^${var}=" .env; then
            value=$(grep "^${var}=" .env | head -1 | cut -d'=' -f2-)
            if [[ -z "$value" || "$value" == "your-"* ]]; then
                fail "${var} 值为空或为占位符"
            else
                pass "${var} 已设置"
            fi
        else
            fail "${var} 未定义"
        fi
    done
else
    fail ".env 文件不存在"
fi

# ---------- 2. JWT_SECRET_KEY ----------
echo ""
echo "[2/10] JWT 密钥检查"
if [[ -f .env ]]; then
    JWT_SECRET=$(grep "^JWT_SECRET_KEY=" .env 2>/dev/null | cut -d'=' -f2- || echo "")
    if [[ "$JWT_SECRET" == "change-me-in-production" ]]; then
        fail "JWT_SECRET_KEY 使用默认值，生产环境必须设置随机密钥"
    elif [[ -n "$JWT_SECRET" && ${#JWT_SECRET} -lt 32 ]]; then
        warn "JWT_SECRET_KEY 长度不足 32 字符，建议使用更长的密钥"
    elif [[ -n "$JWT_SECRET" ]]; then
        pass "JWT_SECRET_KEY 已设置 (${#JWT_SECRET} 字符)"
    fi
fi

# ---------- 3. OSS 端点 ----------
echo ""
echo "[3/10] OSS 端点检查"
if [[ -f .env ]]; then
    OSS_PUBLIC=$(grep "^OSS_PUBLIC_ENDPOINT=" .env 2>/dev/null | cut -d'=' -f2- || echo "")
    OSS_INTERNAL=$(grep "^OSS_INTERNAL_ENDPOINT=" .env 2>/dev/null | cut -d'=' -f2- || echo "")
    OSS_ENDPOINT=$(grep "^OSS_ENDPOINT=" .env 2>/dev/null | cut -d'=' -f2- || echo "")

    EFFECTIVE_PUBLIC="${OSS_PUBLIC:-$OSS_ENDPOINT}"

    if [[ "$EFFECTIVE_PUBLIC" == *"-internal.aliyuncs.com"* ]]; then
        fail "OSS 公网端点使用了内网地址: ${EFFECTIVE_PUBLIC}"
    elif [[ -n "$EFFECTIVE_PUBLIC" ]]; then
        pass "OSS 公网端点: ${EFFECTIVE_PUBLIC}"
    else
        warn "OSS 端点未配置"
    fi

    if [[ -n "$OSS_INTERNAL" ]]; then
        pass "OSS 内网端点: ${OSS_INTERNAL}"
    fi
fi

# ---------- 4. Docker Compose ----------
echo ""
echo "[4/10] Docker Compose 配置"
if docker compose config > /dev/null 2>&1; then
    pass "docker-compose.yml 配置有效"
else
    fail "docker-compose.yml 配置无效"
fi

# Check redis service exists in docker-compose
if docker compose config 2>/dev/null | grep -q "redis:"; then
    pass "docker-compose 包含 Redis 服务"
else
    warn "docker-compose 未包含 Redis 服务"
fi

# ---------- 5. PostgreSQL ----------
echo ""
echo "[5/10] PostgreSQL 检查"
if [[ -f .env ]]; then
    DB_URL=$(grep "^DATABASE_URL=" .env 2>/dev/null | cut -d'=' -f2- || echo "")
    if [[ "$DB_URL" == sqlite* ]]; then
        fail "DATABASE_URL 使用了 SQLite，生产环境必须使用 PostgreSQL"
    elif [[ "$DB_URL" == postgresql* || "$DB_URL" == postgres* ]]; then
        pass "DATABASE_URL 使用 PostgreSQL"
    elif [[ -n "$DB_URL" ]]; then
        warn "DATABASE_URL 使用了未知数据库类型"
    fi
fi

if docker compose ps postgres 2>/dev/null | grep -q "running"; then
    if docker compose exec -T postgres pg_isready -U zhangshu -d zhangshu_cloud > /dev/null 2>&1; then
        pass "PostgreSQL 可连接"

        # Check max_connections
        MAX_CONN=$(docker compose exec -T postgres psql -U zhangshu -d zhangshu_cloud -t -c "SHOW max_connections;" 2>/dev/null | tr -d ' ' || echo "")
        if [[ -n "$MAX_CONN" ]]; then
            pass "PostgreSQL max_connections = ${MAX_CONN}"
        fi
    else
        fail "PostgreSQL 容器运行中但无法连接"
    fi
else
    warn "PostgreSQL 容器未运行 (首次部署正常)"
fi

# ---------- 6. Redis ----------
echo ""
echo "[6/10] Redis 检查"
REDIS_ENABLED=$(grep "^REDIS_ENABLED=" .env 2>/dev/null | cut -d'=' -f2- || echo "true")

if [[ "$REDIS_ENABLED" == "true" ]]; then
    if docker compose ps redis 2>/dev/null | grep -q "running"; then
        if docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
            pass "Redis 可连接 (PONG)"
        else
            fail "Redis 容器运行中但无法 PING"
        fi
    else
        warn "Redis 容器未运行 (首次部署正常)"
    fi

    # Check rate limit backend
    RL_BACKEND=$(grep "^RATE_LIMIT_BACKEND=" .env 2>/dev/null | cut -d'=' -f2- || echo "database")
    if [[ "$RL_BACKEND" == "redis" ]]; then
        pass "RATE_LIMIT_BACKEND = redis"
    else
        warn "RATE_LIMIT_BACKEND = ${RL_BACKEND}，生产建议使用 redis"
    fi

    CACHE_BE=$(grep "^CACHE_BACKEND=" .env 2>/dev/null | cut -d'=' -f2- || echo "memory")
    if [[ "$CACHE_BE" == "redis" ]]; then
        pass "CACHE_BACKEND = redis"
    else
        warn "CACHE_BACKEND = ${CACHE_BE}，生产建议使用 redis"
    fi
else
    warn "REDIS_ENABLED = false，生产环境必须启用 Redis"
fi

# ---------- 7. Nginx 限流 ----------
echo ""
echo "[7/10] Nginx 限流配置"
NGINX_CONF="/etc/nginx/conf.d/rate-limits.conf"
if [[ -f "$NGINX_CONF" ]]; then
    if grep -q "limit_req_zone" "$NGINX_CONF"; then
        pass "Nginx rate-limits.conf 包含限流区域"
    else
        warn "Nginx rate-limits.conf 存在但缺少限流区域"
    fi
else
    warn "Nginx rate-limits.conf 不存在 (deploy.sh 会自动创建)"
fi

SITE_CONF="/etc/nginx/sites-available/zhangshu-cloud"
if [[ -f "$SITE_CONF" ]]; then
    if grep -q "limit_req" "$SITE_CONF"; then
        pass "Nginx 站点配置包含限流规则"
    else
        warn "Nginx 站点配置缺少限流规则"
    fi
    if grep -q "client_max_body_size" "$SITE_CONF"; then
        BODY_SIZE=$(grep "client_max_body_size" "$SITE_CONF" | head -1 | awk '{print $2}' | tr -d ';')
        pass "client_max_body_size = ${BODY_SIZE}"
    fi
else
    warn "Nginx 站点配置不存在 (deploy.sh 会自动创建)"
fi

# ---------- 8. Worker × Pool 连接数 ----------
echo ""
echo "[8/10] Worker × 连接池计算"
API_WORKERS=$(grep "^API_WORKERS=" .env 2>/dev/null | cut -d'=' -f2- || echo "2")
POOL_SIZE=$(grep "^DATABASE_POOL_SIZE=" .env 2>/dev/null | cut -d'=' -f2- || echo "5")
MAX_OVERFLOW=$(grep "^DATABASE_MAX_OVERFLOW=" .env 2>/dev/null | cut -d'=' -f2- || echo "5")

TOTAL_CONN=$(( API_WORKERS * (POOL_SIZE + MAX_OVERFLOW) ))

echo "  API_WORKERS = ${API_WORKERS}"
echo "  DATABASE_POOL_SIZE = ${POOL_SIZE}"
echo "  DATABASE_MAX_OVERFLOW = ${MAX_OVERFLOW}"
echo "  总连接数 = ${API_WORKERS} × (${POOL_SIZE} + ${MAX_OVERFLOW}) = ${TOTAL_CONN}"

if [[ -n "${MAX_CONN:-}" ]]; then
    if [[ $TOTAL_CONN -gt $MAX_CONN ]]; then
        fail "总连接数 (${TOTAL_CONN}) 超过 PostgreSQL max_connections (${MAX_CONN})"
    elif [[ $((TOTAL_CONN * 2)) -gt $MAX_CONN ]]; then
        warn "总连接数 (${TOTAL_CONN}) 接近 max_connections (${MAX_CONN}) 的一半"
    else
        pass "连接池公式安全: ${TOTAL_CONN} / ${MAX_CONN}"
    fi
else
    if [[ $TOTAL_CONN -le 50 ]]; then
        pass "连接池公式: ${TOTAL_CONN} (默认 max_connections=100 下安全)"
    else
        warn "连接池公式: ${TOTAL_CONN}，请确认不超过 PostgreSQL max_connections"
    fi
fi

# ---------- 9. 服务健康检查 ----------
echo ""
echo "[9/10] 服务健康检查"
if curl -sf http://127.0.0.1:9000/health > /dev/null 2>&1; then
    pass "本地 /health 响应正常"
else
    warn "本地 /health 未响应 (服务可能未启动)"
fi

if curl -sf http://127.0.0.1:9000/ready > /dev/null 2>&1; then
    READY_BODY=$(curl -sf http://127.0.0.1:9000/ready 2>/dev/null || echo "")
    if echo "$READY_BODY" | grep -q '"ok"'; then
        pass "本地 /ready 状态正常"
    else
        warn "本地 /ready 返回非 ok 状态"
    fi
else
    warn "本地 /ready 未响应 (服务可能未启动)"
fi

if [[ -n "$DOMAIN" ]]; then
    if curl -sf "https://${DOMAIN}/health" > /dev/null 2>&1; then
        pass "远程 https://${DOMAIN}/health 响应正常"
    else
        warn "远程 https://${DOMAIN}/health 未响应"
    fi
fi

# ---------- 10. 磁盘空间 ----------
echo ""
echo "[10/10] 磁盘空间"
DISK_USAGE=$(df "${APP_DIR}" | tail -1 | awk '{print $5}' | tr -d '%')
DISK_AVAIL=$(df -h "${APP_DIR}" | tail -1 | awk '{print $4}')

if [[ $DISK_USAGE -ge 95 ]]; then
    fail "磁盘使用率 ${DISK_USAGE}% (剩余 ${DISK_AVAIL})，空间严重不足"
elif [[ $DISK_USAGE -ge 85 ]]; then
    warn "磁盘使用率 ${DISK_USAGE}% (剩余 ${DISK_AVAIL})，建议清理"
else
    pass "磁盘使用率 ${DISK_USAGE}% (剩余 ${DISK_AVAIL})"
fi

# ---------- 汇总 ----------
echo ""
echo "========================================="
echo -e "  结果: ${GREEN}${PASS} 通过${NC}, ${YELLOW}${WARN} 警告${NC}, ${RED}${FAIL} 失败${NC}"
echo "========================================="
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo -e "${RED}有 ${FAIL} 项检查未通过，请修复后再部署。${NC}"
    exit 1
elif [[ $WARN -gt 0 ]]; then
    echo -e "${YELLOW}有 ${WARN} 项警告，请确认不影响生产运行。${NC}"
    exit 0
else
    echo -e "${GREEN}所有检查通过，可以部署。${NC}"
    exit 0
fi
