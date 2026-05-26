#!/bin/bash
set -e

# ============================================================
# SSH 安全加固脚本
# 在部署完成并测试成功后运行
# ============================================================

echo "=========================================="
echo "  SSH 安全加固"
echo "=========================================="
echo ""
echo "警告：此脚本将禁用 root 登录和密码登录"
echo "      请确保你已经有 SSH 密钥可以登录"
echo ""
read -p "是否继续？(输入 yes 确认): " confirm

if [ "$confirm" != "yes" ]; then
    echo "已取消"
    exit 0
fi

# 备份原始配置
cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup.$(date +%Y%m%d%H%M%S)

# 禁用 root 登录
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config

# 禁用密码登录
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config

# 重启 SSH
systemctl restart sshd

echo ""
echo "✓ SSH 加固完成"
echo ""
echo "已禁用："
echo "  - root 用户登录"
echo "  - 密码登录"
echo ""
echo "现在只能使用 SSH 密钥登录"
echo "如需恢复，编辑 /etc/ssh/sshd_config 并重启 sshd"
