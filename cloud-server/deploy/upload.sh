#!/usr/bin/env bash
# ============================================================
# 章枢云 API — 上传代码到服务器
# ============================================================
# 用法: bash deploy/upload.sh <服务器IP>
#
# 在本地 (Windows) 运行此脚本，将代码上传到服务器
# 需要安装: Git Bash 或 WSL (提供 ssh/scp)
# ============================================================

set -euo pipefail

SERVER_IP="${1:-}"
DEPLOY_USER="deploy"
APP_DIR="/opt/zhangshu-cloud"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*" >&2; }

if [[ -z "${SERVER_IP}" ]]; then
    err "请提供服务器 IP 地址"
    echo "用法: bash deploy/upload.sh <服务器IP>"
    echo "示例: bash deploy/upload.sh 47.100.xx.xx"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo ""
echo "========================================="
echo "  上传章枢云代码到服务器"
echo "  服务器: ${SERVER_IP}"
echo "  本地路径: ${SCRIPT_DIR}"
echo "========================================="
echo ""

# ---------- 排除不需要的文件 ----------
EXCLUDE=(
    "--exclude=.git"
    "--exclude=.venv"
    "--exclude=__pycache__"
    "--exclude=.pytest_cache"
    "--exclude=.env"
    "--exclude=*.pyc"
    "--exclude=*.db"
    "--exclude=release"
    "--exclude=build"
)

# ---------- 1. 确保服务器目录存在 ----------
log "创建远程目录..."
ssh "${DEPLOY_USER}@${SERVER_IP}" "sudo mkdir -p ${APP_DIR} && sudo chown ${DEPLOY_USER}:${DEPLOY_USER} ${APP_DIR}"

# ---------- 2. 同步文件 ----------
log "上传文件 (rsync)..."
if command -v rsync &>/dev/null; then
    rsync -avz --delete "${EXCLUDE[@]}" \
        "${SCRIPT_DIR}/" \
        "${DEPLOY_USER}@${SERVER_IP}:${APP_DIR}/"
else
    warn "rsync 未安装，使用 scp 替代..."
    scp -r "${SCRIPT_DIR}/"* "${DEPLOY_USER}@${SERVER_IP}:${APP_DIR}/"
fi

log "上传完成!"
echo ""
echo "下一步:"
echo "  1. SSH 登录服务器:"
echo "     ssh ${DEPLOY_USER}@${SERVER_IP}"
echo ""
echo "  2. 编辑 .env 配置 (首次部署):"
echo "     cd ${APP_DIR} && nano .env"
echo ""
echo "  3. 运行部署脚本:"
echo "     bash deploy/deploy.sh"
echo ""
