#!/usr/bin/env bash
# ============================================================
# 章枢云 API — 零停机更新脚本 (v2)
# ============================================================
# 用法: bash deploy/update.sh
#
# 功能:
#   1. 运行部署前检查
#   2. 备份数据库
#   3. 记录当前镜像 ID
#   4. 重新构建镜像
#   5. 滚动更新容器
#   6. 运行数据库迁移
#   7. 验证健康状态
#   8. 失败时提供回滚命令
# ============================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/zhangshu-cloud}"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

echo ""
echo "========================================="
echo "  章枢云 API 更新部署"
echo "  时间: ${TIMESTAMP}"
echo "========================================="
echo ""

cd "${APP_DIR}"

# ---------- 0. 部署前检查 (非阻塞) ----------
if [[ -f deploy/preflight.sh ]]; then
    log "运行部署前检查..."
    bash deploy/preflight.sh || {
        warn "部署前检查有失败项，继续部署但请注意风险"
    }
    echo ""
fi

# ---------- 1. 备份数据库 ----------
log "备份当前数据库..."
BACKUP_DIR="${APP_DIR}/backups"
mkdir -p "${BACKUP_DIR}"

docker compose exec -T postgres pg_dump \
    -U zhangshu \
    -d zhangshu_cloud \
    --format=custom \
    > "${BACKUP_DIR}/db_${TIMESTAMP}.dump"

sha256sum "${BACKUP_DIR}/db_${TIMESTAMP}.dump" > "${BACKUP_DIR}/db_${TIMESTAMP}.dump.sha256"

log "数据库已备份: backups/db_${TIMESTAMP}.dump"

# ---------- 2. 记录当前镜像 ID ----------
OLD_IMAGE_ID=$(docker compose images -q cloud-api 2>/dev/null | head -1 || echo "")

# ---------- 3. 重新构建镜像 ----------
log "重新构建 Docker 镜像..."
docker compose build --no-cache cloud-api

NEW_IMAGE_ID=$(docker compose images -q cloud-api 2>/dev/null | head -1 || echo "")

if [[ "${OLD_IMAGE_ID}" == "${NEW_IMAGE_ID}" && -n "${OLD_IMAGE_ID}" ]]; then
    warn "镜像未变化，跳过重启"
    exit 0
fi

# ---------- 4. 滚动更新 ----------
log "更新容器..."
docker compose up -d --no-deps cloud-api

# ---------- 5. 运行数据库迁移 ----------
log "运行数据库迁移..."
sleep 3  # 等待容器启动
docker compose exec -T cloud-api alembic upgrade head

# ---------- 6. 健康检查 ----------
log "验证服务健康状态..."
RETRIES=15
HEALTHY=false
for i in $(seq 1 $RETRIES); do
    if curl -sf http://127.0.0.1:9000/ready > /dev/null 2>&1; then
        HEALTHY=true
        break
    fi
    echo -n "."
    sleep 2
done

if ! $HEALTHY; then
    echo ""
    err "健康检查失败! 正在回滚..."
    echo ""
    echo "  回滚步骤:"
    echo "    1. 重启旧容器:  docker compose down cloud-api && docker compose up -d --no-deps cloud-api"
    echo "    2. 恢复数据库:  RESTORE_CONFIRM=yes bash deploy/restore-db.sh ${BACKUP_DIR}/db_${TIMESTAMP}.dump"
    echo ""

    # 自动回滚容器
    docker compose down cloud-api
    docker compose up -d --no-deps cloud-api

    err "已回滚容器到上一版本"
    err "如需恢复数据库，运行: RESTORE_CONFIRM=yes bash deploy/restore-db.sh ${BACKUP_DIR}/db_${TIMESTAMP}.dump"
    exit 1
fi

log "服务健康检查通过!"

# ---------- 7. 清理旧镜像 ----------
log "清理旧镜像..."
docker image prune -f 2>/dev/null || true

# ---------- 8. 清理旧备份 (保留最近 10 个) ----------
BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}"/db_*.dump 2>/dev/null | wc -l)
if [[ $BACKUP_COUNT -gt 10 ]]; then
    REMOVE_COUNT=$((BACKUP_COUNT - 10))
    ls -1t "${BACKUP_DIR}"/db_*.dump | tail -n "${REMOVE_COUNT}" | xargs rm -f
    # 同时清理校验文件
    ls -1t "${BACKUP_DIR}"/db_*.dump.sha256 | tail -n "${REMOVE_COUNT}" | xargs rm -f 2>/dev/null || true
    log "已清理 ${REMOVE_COUNT} 个旧备份"
fi

echo ""
log "更新部署完成!"
echo ""
echo "  备份位置: ${BACKUP_DIR}/db_${TIMESTAMP}.dump"
echo ""
echo "  回滚命令 (如需):"
echo "    docker compose down cloud-api && docker compose up -d --no-deps cloud-api"
echo "    RESTORE_CONFIRM=yes bash deploy/restore-db.sh ${BACKUP_DIR}/db_${TIMESTAMP}.dump"
echo ""
