#!/usr/bin/env bash
# ============================================================
# 章枢云 API — 数据库恢复脚本
# ============================================================
# 用法: bash deploy/restore-db.sh <dump_file>
#
# 安全措施:
#   1. 必须设置 RESTORE_CONFIRM=yes 才能执行
#   2. 恢复前自动备份当前数据库
#   3. 使用 pg_restore --clean --if-exists
# ============================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/zhangshu-cloud}"
BACKUP_DIR="${APP_DIR}/backups"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

# ---------- 参数检查 ----------
if [[ $# -lt 1 ]]; then
    err "用法: bash deploy/restore-db.sh <dump_file>"
    echo ""
    echo "  可用备份:"
    ls -lh "${BACKUP_DIR}"/db_*.dump 2>/dev/null || echo "    (无备份文件)"
    echo ""
    exit 1
fi

DUMP_FILE="$1"

if [[ ! -f "${DUMP_FILE}" ]]; then
    err "文件不存在: ${DUMP_FILE}"
    exit 1
fi

# ---------- 校验 (如果有校验文件) ----------
CHECKSUM_FILE="${DUMP_FILE}.sha256"
if [[ -f "${CHECKSUM_FILE}" ]]; then
    log "验证 SHA256 校验..."
    if sha256sum -c "${CHECKSUM_FILE}" > /dev/null 2>&1; then
        log "校验通过"
    else
        err "SHA256 校验失败! 备份文件可能已损坏。"
        echo "  如需强制恢复，删除校验文件后重试。"
        exit 1
    fi
fi

# ---------- 确认保护 ----------
echo ""
echo -e "${RED}=========================================${NC}"
echo -e "${RED}  ⚠  即将恢复数据库!${NC}"
echo -e "${RED}=========================================${NC}"
echo ""
echo "  恢复文件: ${DUMP_FILE}"
echo "  文件大小: $(du -h "${DUMP_FILE}" | cut -f1)"
echo ""
echo "  恢复将覆盖当前数据库中的所有数据。"
echo ""

if [[ "${RESTORE_CONFIRM:-}" != "yes" ]]; then
    err "安全确认未通过。"
    echo "  请设置环境变量后重试:"
    echo "    RESTORE_CONFIRM=yes bash deploy/restore-db.sh ${DUMP_FILE}"
    exit 1
fi

cd "${APP_DIR}"

# ---------- 1. 恢复前自动备份 ----------
log "恢复前备份当前数据库..."
PRE_RESTORE_DUMP="${BACKUP_DIR}/pre_restore_${TIMESTAMP}.dump"
mkdir -p "${BACKUP_DIR}"

docker compose exec -T postgres pg_dump \
    -U zhangshu \
    -d zhangshu_cloud \
    --format=custom \
    > "${PRE_RESTORE_DUMP}" 2>/dev/null

log "当前数据库已备份: ${PRE_RESTORE_DUMP}"

# ---------- 2. 执行恢复 ----------
log "执行数据库恢复..."
docker compose exec -T postgres pg_restore \
    -U zhangshu \
    -d zhangshu_cloud \
    --clean \
    --if-exists \
    --verbose \
    < "${DUMP_FILE}" 2>&1 | tail -5

log "数据库恢复完成"

# ---------- 3. 重启应用 ----------
log "重启 cloud-api 容器..."
docker compose restart cloud-api

# ---------- 4. 健康检查 ----------
log "验证服务健康状态..."
RETRIES=10
for i in $(seq 1 $RETRIES); do
    if curl -sf http://127.0.0.1:9000/ready > /dev/null 2>&1; then
        log "服务已恢复正常运行!"
        break
    fi
    if [[ $i -eq $RETRIES ]]; then
        warn "健康检查未通过，请检查日志"
        echo "  docker compose logs --tail=20 cloud-api"
    fi
    echo -n "."
    sleep 2
done

echo ""
log "恢复完成!"
echo "  恢复前备份: ${PRE_RESTORE_DUMP}"
echo "  如需回滚: RESTORE_CONFIRM=yes bash deploy/restore-db.sh ${PRE_RESTORE_DUMP}"
echo ""
