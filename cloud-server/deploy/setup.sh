#!/bin/bash
set -e

# ============================================================
# 章枢云 - Ubuntu 服务器初始化脚本 (v2)
# 适用于阿里云轻量应用服务器 Ubuntu 22.04
# 使用阿里云镜像源，适配国内网络
# ============================================================

echo "=========================================="
echo "  章枢云服务器初始化脚本"
echo "=========================================="
echo ""

# 检查是否以 root 运行
if [ "$EUID" -ne 0 ]; then
    echo "错误: 请使用 root 用户运行此脚本"
    exit 1
fi

# 设置域名（如果没设置环境变量）
DOMAIN=${ZHANGSHU_DOMAIN:-"api.emailbs.xin"}
EMAIL=${ZHANGSHU_EMAIL:-"admin@example.com"}

echo "配置信息:"
echo "  域名: $DOMAIN"
echo "  邮箱: $EMAIL"
echo ""

# ============================================================
# 第一步：系统更新
# ============================================================
echo "[1/8] 更新系统包..."
export DEBIAN_FRONTEND=noninteractive

# 禁用交互式提示（needrestart、dpkg 配置文件冲突）
echo '* libraries/restart-suffix no-restart-note' | sudo debconf-set-selections 2>/dev/null || true
apt-get install -y needrestart 2>/dev/null || true
if [ -f /etc/needrestart/needrestart.conf ]; then
    sed -i 's/^#\?\$nrconf{restart}.*/\$nrconf{restart} = "a";/' /etc/needrestart/needrestart.conf
fi

apt-get update -y
apt-get upgrade -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold"
echo "✓ 系统更新完成"
echo ""

# ============================================================
# 第二步：安装基础工具
# ============================================================
echo "[2/8] 安装基础工具..."
apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" \
    curl \
    wget \
    git \
    vim \
    htop \
    ca-certificates \
    gnupg \
    lsb-release \
    ufw \
    fail2ban
echo "✓ 基础工具安装完成"
echo ""

# ============================================================
# 第三步：安装 Docker（使用阿里云镜像）
# ============================================================
echo "[3/8] 安装 Docker..."

# 如果 Docker 已安装，跳过
if command -v docker &> /dev/null; then
    echo "Docker 已安装，跳过"
else
    # 清理可能残留的旧配置
    rm -f /etc/apt/sources.list.d/docker.list
    rm -f /etc/apt/keyrings/docker.asc

    # 添加 Docker GPG 密钥（阿里云镜像）
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc

    # 添加阿里云 Docker 源
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://mirrors.aliyun.com/docker-ce/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list

    # 安装 Docker
    apt-get update -y
    apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" docker-ce docker-ce-cli containerd.io docker-compose-plugin docker-buildx-plugin

    # 启动 Docker
    systemctl enable docker
    systemctl start docker

    echo "✓ Docker 安装完成"
fi

# 验证 Docker
docker version
echo ""

# ============================================================
# 第四步：安装 Nginx
# ============================================================
echo "[4/8] 安装 Nginx..."

# 如果 Nginx 已安装且正常，跳过
if command -v nginx &> /dev/null && systemctl is-active --quiet nginx; then
    echo "Nginx 已安装且运行正常，跳过"
else
    # 清理可能损坏的 Nginx 包
    apt-get remove --purge -y nginx nginx-common nginx-core libnginx-mod-* 2>/dev/null || true
    apt-get autoremove -y
    apt-get clean
    dpkg --configure -a
    apt-get install -f -y

    # 重新安装
    apt-get install -y nginx
    systemctl enable nginx
    systemctl start nginx

    echo "✓ Nginx 安装完成"
fi

# 验证 Nginx
nginx -v
systemctl status nginx --no-pager
echo ""

# ============================================================
# 第五步：安装 Certbot
# ============================================================
echo "[5/8] 安装 Certbot..."

if command -v certbot &> /dev/null; then
    echo "Certbot 已安装，跳过"
else
    apt-get install -y certbot python3-certbot-nginx
    echo "✓ Certbot 安装完成"
fi
echo ""

# ============================================================
# 第六步：配置 Swap（2GB 内存需要）
# ============================================================
echo "[6/8] 配置 Swap..."

if [ -f /swapfile ]; then
    echo "Swap 已存在，跳过"
else
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    sysctl vm.swappiness=10
    echo 'vm.swappiness=10' >> /etc/sysctl.conf
    echo "✓ Swap 配置完成 (2GB)"
fi

# 显示 Swap 状态
swapon --show
free -h
echo ""

# ============================================================
# 第七步：配置防火墙
# ============================================================
echo "[7/8] 配置防火墙..."

ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
echo "y" | ufw enable
systemctl enable ufw

echo "✓ 防火墙配置完成"
ufw status
echo ""

# ============================================================
# 第八步：配置 Fail2ban
# ============================================================
echo "[8/8] 配置 Fail2ban..."

systemctl enable fail2ban
systemctl start fail2ban

echo "✓ Fail2ban 已启动"
echo ""

# ============================================================
# 完成提示
# ============================================================
echo "=========================================="
echo "  ✓ 服务器初始化完成！"
echo "=========================================="
echo ""
echo "已安装和配置："
echo "  - Docker + Docker Compose"
echo "  - Nginx"
echo "  - Certbot (Let's Encrypt)"
echo "  - 防火墙 (UFW)"
echo "  - Fail2ban (防暴力破解)"
echo "  - Swap (2GB)"
echo ""
echo "下一步操作："
echo "  1. 确认域名 DNS 已指向此服务器 IP"
echo "  2. 上传项目代码到 /opt/zhangshu-cloud"
echo "  3. 运行部署脚本: bash /opt/zhangshu-cloud/deploy/deploy.sh"
echo ""
echo "注意：SSH 安全加固（禁用 root 登录和密码登录）"
echo "      建议在部署完成并测试后再执行："
echo "      bash /opt/zhangshu-cloud/deploy/harden-ssh.sh"
echo ""
