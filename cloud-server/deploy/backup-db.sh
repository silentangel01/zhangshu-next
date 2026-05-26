#!/usr/bin/env bash
# ============================================================
# 章枢云 API — 数据库备份脚本 (v2)
# ============================================================
# 用法: bash deploy/backup-db.sh
#
# 环境变量:
#   KEEP_DAYS    保留天数 (默认 30)
#   APP_DIR      应用目录 (默认 /opt/zhangshu-cloud)
#
# 可配合 crontab 定时执行:
#   0 3 * * * /opt/zhangshu-cloud/deploy/backup-db.sh
# ============================================================

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/zhangshu-cloud}"
BACKUP_DIR="${APP_DIR}/backups"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
KEEP_DAYS="${KEEP_DAYS:-30}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

mkdir -p "${BACKUP_DIR}"
cd "${APP_DIR}"

# ---------- 1. 全量备份 (自定义格式，支持 pg_restore) ----------
DUMP_FILE="${BACKUP_DIR}/db_${TIMESTAMP}.dump"

log "执行全量备份..."
docker compose exec -T postgres pg_dump \
    -U zhangshu \
    -d zhangshu_cloud \
    --format=custom \
    --verbose \
    > "${DUMP_FILE}" 2>/dev/null

DUMP_SIZE=$(du -h "${DUMP_FILE}" | cut -f1)
log "全量备份完成: ${DUMP_FILE} (${DUMP_SIZE})"

# ---------- 2. 生成 SHA256 校验 ----------
CHECKSUM_FILE="${DUMP_FILE}.sha256"
sha256sum "${DUMP_FILE}" > "${CHECKSUM_FILE}"
log "校验文件: ${CHECKSUM_FILE}"

# ---------- 3. 验证备份 ----------
log "验证备份完整性..."
docker compose exec -T postgres pg_restore \
    --list "${DUMP_FILE}" > /dev/null 2>&1

if [[ $? -eq 0 ]]; then
    log "备份验证通过"
else
    err "备份验证失败!"
    exit 1
fi

# ---------- 4. 清理旧备份 ----------
CLEANED=0
while IFS= read -r -d '' file; do
    rm -f "$file"
    # 也删除对应的校验文件
    rm -f "${file}.sha256"
    CLEANED=$((CLEANED + 1))
done < <(find "${BACKUP_DIR}" -name "db_*.dump" -mtime +${KEEP_DAYS} -print0 2>/dev/null)

if [[ $CLEANED -gt 0 ]]; then
    log "已清理 ${CLEANED} 个超过 ${KEEP_DAYS} 天的旧备份"
fi

# ---------- 汇总 ----------
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
BACKUP_COUNT=$(ls -1 "${BACKUP_DIR}"/db_*.dump 2>/dev/null | wc -l)

echo ""
log "备份完成!"
echo "  本次备份:"
echo "    ${DUMP_FILE} (${DUMP_SIZE})"
echo "    ${CHECKSUM_FILE}"
echo "  备份目录: ${BACKUP_DIR} (${TOTAL_SIZE}, ${BACKUP_COUNT} 份)"
echo ""
echo "  恢复命令:"
echo "    bash deploy/restore-db.sh ${DUMP_FILE}"
echo ""
