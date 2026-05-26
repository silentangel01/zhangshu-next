#!/usr/bin/env bash
# ============================================================
# 章枢云 API — 部署前检查脚本 (Preflight)
# ============================================================
# 用法: bash deploy/preflight.sh
#
# 检查项目:
#   1. .env 必填项
#   2. JWT_SECRET_KEY 非默认
#   3. OSS_PUBLIC_ENDPOINT 非 internal
#   4. Docker Compose 配置可解析
#   5. 数据库可连接
#   6. HTTPS 健康检查 (如果域名已配置)
#   7. 磁盘空间
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
echo "[1/7] 环境配置文件"
if [[ -f .env ]]; then
    pass ".env 文件存在"

    # 必填项检查
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
echo "[2/7] JWT 密钥检查"
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
echo "[3/7] OSS 端点检查"
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
echo "[4/7] Docker Compose 配置"
if docker compose config > /dev/null 2>&1; then
    pass "docker-compose.yml 配置有效"
else
    fail "docker-compose.yml 配置无效"
fi

# ---------- 5. 数据库连接 ----------
echo ""
echo "[5/7] 数据库连接"
if docker compose ps postgres 2>/dev/null | grep -q "running"; then
    if docker compose exec -T postgres pg_isready -U zhangshu -d zhangshu_cloud > /dev/null 2>&1; then
        pass "PostgreSQL 可连接"
    else
        fail "PostgreSQL 容器运行中但无法连接"
    fi
else
    warn "PostgreSQL 容器未运行 (首次部署正常)"
fi

# ---------- 6. HTTPS 健康检查 ----------
echo ""
echo "[6/7] 服务健康检查"
if curl -sf http://127.0.0.1:9000/health > /dev/null 2>&1; then
    pass "本地 /health 响应正常"
else
    warn "本地 /health 未响应 (服务可能未启动)"
fi

if curl -sf http://127.0.0.1:9000/ready > /dev/null 2>&1; then
    pass "本地 /ready 响应正常"
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

# ---------- 7. 磁盘空间 ----------
echo ""
echo "[7/7] 磁盘空间"
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
