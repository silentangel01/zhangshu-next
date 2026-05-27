# 事故处置手册

常见生产事故的排查和处置流程。

## 用户无法登录

### 症状
用户报告登录失败，返回 401 或 429。

### 排查步骤

1. **检查日志**
   ```bash
   docker compose logs --tail=50 cloud-api | grep "login_failed\|AUDIT"
   ```

2. **检查频率限制**
   - 查看审计日志中是否有 `reason_code=429`
   - 频率限制为每 5 分钟 10 次（可按 IP+邮箱组合重置）
   - 重启 cloud-api 容器可清空内存中的频率限制记录

3. **检查数据库**
   ```bash
   docker compose exec postgres psql -U zhangshu -d zhangshu_cloud \
       -c "SELECT id, email, is_active FROM users WHERE email = 'user@example.com';"
   ```
   - 如果 `is_active = false`，账号已被禁用
   - 如果用户不存在，确认邮箱拼写

4. **检查密码**
   - 确认用户输入的密码正确（bcrypt 验证）
   - 密码 UTF-8 编码后不得超过 72 字节

### 处置
- 频率限制：等待 5 分钟或重启容器
- 账号被禁用：数据库中设置 `is_active = true`
- 密码错误：引导用户重置密码（目前无自助重置功能）

---

## 云备份上传失败

### 症状
桌面端提示上传失败，HTTP 状态码 400/500/503。

### 排查步骤

1. **检查审计日志**
   ```bash
   docker compose logs --tail=100 cloud-api | grep "backup_init_failed\|backup_complete_failed"
   ```

2. **检查 OSS 配置**
   ```bash
   docker compose exec cloud-api python -c "
   from app.core.config import get_settings
   s = get_settings()
   print(f'key={s.oss_access_key_id[:6]}...')
   print(f'secret={\"set\" if s.oss_access_key_secret else \"empty\"}')
   print(f'bucket={s.oss_bucket_name}')
   print(f'endpoint={s.oss_endpoint}')
   "
   ```

3. **检查配额**
   - 存储配额：`default_storage_quota_bytes`（默认 1 GB）
   - 备份数量：`default_backup_count_quota`（默认 100）
   - 频率限制：`rate_limit_backup_init_per_hour`（默认 30/小时）

4. **检查超时上传**
   ```bash
   docker compose exec postgres psql -U zhangshu -d zhangshu_cloud \
       -c "SELECT id, filename, status, created_at FROM cloud_backups WHERE status = 'uploading' ORDER BY created_at DESC LIMIT 10;"
   ```

### 处置
- 配额不足：提示用户删除旧备份，或调高配额
- OSS 未配置：编辑 `.env` 填入 AccessKey，重启容器
- 超时上传：调用 cleanup 接口或手动将 `status` 改为 `failed`

---

## OSS 403 Forbidden

### 症状
备份 init 成功但上传/下载返回 403。

### 排查步骤

1. **检查 AccessKey 权限**
   - 确认 AccessKey 有 `oss:PutObject`、`oss:GetObject`、`oss:DeleteObject` 权限
   - 检查 RAM 策略是否限制了 Bucket 或 IP

2. **检查 Bucket 策略**
   - 确认 Bucket 未被设置为完全私有（阻止 presigned URL）
   - 检查 Bucket 是否开启了防盗链

3. **检查时间同步**
   - OSS 签名对时间敏感，服务器时间偏差 > 15 分钟会导致 403
   ```bash
   date -u
   ntpstat 2>/dev/null || timedatectl status
   ```

### 处置
- 修复 RAM 权限策略
- 同步服务器时间：`ntpdate ntp.aliyun.com`
- 重新生成 AccessKey（如已泄露）

---

## 数据库连接失败

### 症状
API 返回 500，日志中出现 `sqlalchemy.exc.OperationalError`。

### 排查步骤

1. **检查 PostgreSQL 容器**
   ```bash
   docker compose ps postgres
   docker compose logs --tail=20 postgres
   ```

2. **检查连接**
   ```bash
   docker compose exec postgres pg_isready -U zhangshu -d zhangshu_cloud
   ```

3. **检查资源**
   ```bash
   docker stats --no-stream postgres
   df -h
   free -h
   ```

### 处置
- 容器未运行：`docker compose up -d postgres`
- 磁盘满：清理旧备份或日志
- 内存不足：调高 PostgreSQL 容器内存限制

---

## 磁盘空间满

### 症状
日志写入失败、数据库崩溃、上传失败。

### 排查步骤

1. **检查磁盘使用**
   ```bash
   df -h
   du -sh /opt/zhangshu-cloud/backups/
   du -sh /var/lib/docker/
   docker system df
   ```

2. **找到大文件**
   ```bash
   du -sh /opt/zhangshu-cloud/* | sort -rh | head -10
   ```

### 处置
- 清理旧备份：`KEEP_DAYS=7 bash deploy/backup-db.sh`（只保留 7 天）
- 清理 Docker：`docker system prune -f`
- 清理旧镜像：`docker image prune -a -f`
- 清理 Docker 日志：`truncate -s 0 /var/lib/docker/containers/*/*-json.log`

---

## SSL 证书过期

### 症状
浏览器提示证书无效，`curl https://...` 返回证书错误。

### 排查步骤

1. **检查证书到期时间**
   ```bash
   echo | openssl s_client -connect ${DOMAIN}:443 -servername ${DOMAIN} 2>/dev/null | \
       openssl x509 -noout -dates
   ```

2. **检查 certbot 状态**
   ```bash
   certbot certificates
   systemctl status certbot.timer
   journalctl -u certbot.timer --no-pager -n 20
   ```

### 处置
- 手动续期：`certbot renew --force-renewal`
- 重新部署证书：`bash deploy/enable-ssl.sh`
- 检查 certbot timer 是否启用：`systemctl enable --now certbot.timer`

---

## 网络诊断显示 SNI 过滤

### 症状
桌面端网络诊断显示 `compat_no_sni` 或连接失败。

### 排查步骤

1. 确认服务器 HTTPS 配置支持 SNI
2. 检查 Nginx 版本：`nginx -V`（需 0.9.8+）
3. 确认没有使用 IP 直连 HTTPS（需要域名访问）

### 处置
- 确保使用域名访问而非 IP 地址
- 更新 Nginx 到较新版本
- 检查 CDN/WAF 是否正确传递 SNI

---

## 滥用攻击：批量注册或登录

### 症状
- 短时间内大量注册或登录请求
- `rate_limit_events` 表快速膨胀
- 正常用户被误限流

### 排查步骤

1. **检查限流表**
   ```bash
   docker compose exec postgres psql -U zhangshu -d zhangshu_cloud \
       -c "SELECT scope, COUNT(*) FROM rate_limit_events GROUP BY scope ORDER BY count DESC;"
   ```

2. **检查异常 IP**
   ```bash
   docker compose exec postgres psql -U zhangshu -d zhangshu_cloud \
       -c "SELECT client_ip, COUNT(*) FROM rate_limit_events WHERE created_at > now() - interval '1 hour' GROUP BY client_ip ORDER BY count DESC LIMIT 10;"
   ```

3. **检查审计日志**
   ```bash
   docker compose logs --tail=200 cloud-api | grep "AUDIT.*rate_limited"
   ```

### 处置
- 清理过期限流记录：数据库会自动清理 `expires_at < now()` 的记录
- 手动清理：`DELETE FROM rate_limit_events WHERE expires_at < now();`
- 临时封禁 IP：通过 Nginx/WAF 添加黑名单
- 调整限流参数：修改 `.env` 中的频率限制配置

---

## 账号删除失败

### 症状
用户请求删除账号后返回错误，或部分 OSS 对象未删除。

### 排查步骤

1. **检查删除请求状态**
   ```bash
   docker compose exec postgres psql -U zhangshu -d zhangshu_cloud \
       -c "SELECT id, user_id, expires_at, used_at FROM account_deletion_requests ORDER BY created_at DESC LIMIT 5;"
   ```

2. **检查用户状态**
   ```bash
   docker compose exec postgres psql -U zhangshu -d zhangshu_cloud \
       -c "SELECT id, email, deleted_at, anonymized_at FROM users WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC LIMIT 5;"
   ```

3. **检查审计日志**
   ```bash
   docker compose logs --tail=100 cloud-api | grep "account_delete"
   ```

### 处置
- 如果 OSS 删除部分失败：
  - 日志中会记录 `account_delete_partial_failed`
  - 手动清理 OSS 对象：使用 `aliyun oss rm` 命令
  - 确认数据库中标记为 `pending_deletion` 的备份已实际删除
- 如果用户已匿名化但 OSS 残留：
  - 根据 `user_id` 查找 OSS 前缀：`users/{user_id}/`
  - 手动删除对应 OSS 对象
- 如果删除请求过期未确认：
  - 过期请求不会被执行，用户需重新发起

---

## 配额耗尽

### 症状
用户报告无法上传备份，返回 429 或配额相关错误。

### 排查步骤

1. **检查用户使用情况**
   ```bash
   docker compose exec postgres psql -U zhangshu -d zhangshu_cloud \
       -c "SELECT u.email, COUNT(b.id) as backup_count, COALESCE(SUM(b.size_bytes), 0) as total_size FROM users u LEFT JOIN cloud_projects p ON p.user_id = u.id LEFT JOIN cloud_backups b ON b.project_id = p.id AND b.status = 'success' GROUP BY u.email ORDER BY total_size DESC LIMIT 10;"
   ```

2. **检查频率限制**
   ```bash
   docker compose exec postgres psql -U zhangshu -d zhangshu_cloud \
       -c "SELECT key, scope, COUNT(*) FROM rate_limit_events WHERE scope = 'backup_init' AND created_at > now() - interval '1 hour' GROUP BY key, scope;"
   ```

### 处置
- 引导用户删除旧备份释放空间
- 如需调高配额：修改数据库中的用户配额字段（目前使用全局默认值）
- 频率限制超限：等待限流窗口过期（默认 1 小时）

---

## 紧急回滚流程

1. **停止当前服务**
   ```bash
   cd /opt/zhangshu-cloud
   docker compose down cloud-api
   ```

2. **恢复数据库**
   ```bash
   RESTORE_CONFIRM=yes bash deploy/restore-db.sh backups/db_XXXXXXXX_XXXXXX.dump
   ```

3. **重启服务**
   ```bash
   docker compose up -d cloud-api
   ```

4. **验证**
   ```bash
   curl -sf http://127.0.0.1:9000/ready
   bash deploy/preflight.sh
   ```
