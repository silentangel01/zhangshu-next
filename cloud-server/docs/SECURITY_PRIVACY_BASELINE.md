# 安全与隐私基线

本文档记录章枢云管理后台已实现的安全和隐私保护措施。所有功能均已通过自动化测试验证。

## 1. 角色权限矩阵 (RBAC)

### 角色定义

| 角色 | 说明 | 关键权限 |
|------|------|----------|
| `owner` | 最高管理员 | 全部 17 项权限 |
| `admin` | 日常管理 | 除 `admin_roles:manage` 外全部 |
| `support` | 客服/反馈 | 仪表盘、反馈查看/回复、用户查看、公告查看、搜索 |
| `ops` | 运维/监控 | 仪表盘、监控、审计、公告查看 |
| `readonly` | 只读 | 仪表盘、反馈/用户/公告查看 |

### 权限检查

- 后端：每个 API 端点通过 `require_admin_permission(perm)` 依赖注入强制检查
- 前端：菜单项、操作按钮、页面区域根据 `useAdminSession().hasPermission()` 显示/隐藏
- 路由守卫：页面级权限校验，无权限重定向至仪表盘

### 兼容性

- 已有 `is_admin=true` 或 `ADMIN_EMAILS` 中的用户自动映射为 `owner` 角色
- `admin_role` 字段存储在 `users` 表，`null` 表示使用兼容性映射

## 2. 认证安全

### 管理员认证

- **HttpOnly Cookie**：生产环境管理员会话使用 HttpOnly Secure Cookie（`zs_admin_token`）
- **Bearer 降级禁止**：`ENVIRONMENT=production` 时禁止 Bearer token 回退，必须通过 Cookie 认证
- **短生命周期**：Access Token 30 分钟，Refresh Token 8 小时

### 密码修改即时失效

- 修改密码时设置 `password_changed_at` 时间戳
- 所有在此之前签发的 Access Token 在下次请求时被拒绝（JWT `iat` 对比）
- 所有 Refresh Token 在密码修改时被撤销

### Refresh Token 重放检测

- 每次 Refresh Token 使用后，旧 token 被标记为 `rotated` 并关联 `replaced_by_id`
- 重放已轮换的 Refresh Token 会触发安全警报：该用户的**所有**活跃会话全部被撤销
- 审计日志记录 `refresh_token_reuse_detected` 事件

### CSRF/Origin 防护

- `AdminCSRFMiddleware`：管理员写请求（POST/PUT/PATCH/DELETE）需要 `X-Zhangshu-Admin-Request: 1` 自定义头
- Origin/Referer 验证：`ADMIN_REQUIRE_ORIGIN_CHECK=true` 时校验请求来源
- 前端 `apiRequest()` 自动为管理员写请求添加自定义头

## 3. 高风险操作控制

### 最后 Owner 保护

- 不能禁用或降级最后一个 `owner` 角色的管理员
- 防止系统失去最高管理员权限

### 风险操作确认

- 禁用/启用用户、强制下线、角色变更：必须提供 `reason`（操作原因）
- 角色变更：额外需要 `confirm_text="确认变更角色"`
- 附件下载：需要提供 `reason`，记录审计日志
- 反馈删除：需要提供 `reason`，标记为 `risk_level: high`

### 操作后强制下线

- 角色变更：撤销该用户所有活跃 Refresh Token，强制重新登录
- 禁用用户：同时撤销所有活跃会话

## 4. 审计日志

### 记录范围

所有关键操作写入 `audit_logs` 表：

- 登录/登出（成功和失败）
- 用户注册、密码修改
- 管理员操作（角色变更、禁用用户、强制下线）
- 反馈管理（状态变更、回复、附件下载、删除）
- 公告管理（创建、发布、归档、删除）
- Refresh Token 重放检测

### 审计字段

| 字段 | 说明 |
|------|------|
| `event` | 事件类型标识符 |
| `client_ip` | 脱敏后的 IP（如 `192.168.1.xxx`） |
| `client_ip_hash` | IP 的 SHA-256 前 16 字符（用于关联查询） |
| `client_ip_masked` | 脱敏后的 IP |
| `actor_user_id` | 操作者用户 ID |
| `target_user_id` | 目标用户 ID（如适用） |
| `result` | `success` 或 `failure` |
| `reason_code` | 错误码或操作原因 |
| `extra_json` | 额外上下文（受禁止键过滤） |

### 禁止记录字段

`extra_json` 中自动过滤包含以下子串的键：`password`, `token`, `secret`, `access_key`, `upload_url`, `download_url`, `authorization`, `cookie`。

## 5. 隐私脱敏

### IP 地址

| 操作 | 示例 | 用途 |
|------|------|------|
| 掩码 | `192.168.1.42` → `192.168.1.xxx` | 日志展示、审计记录 |
| 哈希 | SHA-256 前 16 字符 | 关联查询（同一 IP 的多次事件） |
| IPv6 | `2001:db8::1` → `2001:xxxx` | IPv6 掩码 |

### 邮箱地址

`john@example.com` → `j***@example.com`

### 其他

- `safe_user_agent()`：截断超长 User-Agent（默认 200 字符）
- `sanitize_filename()`：移除路径遍历攻击字符
- 审计日志中 IP 自动脱敏，原始 IP 不落库

## 6. 前端安全措施

### 会话管理

- 登录时设置 `sessionStorage` 标记
- 页面加载时通过 `/api/admin/auth/me` API 校验真实会话（不仅依赖 sessionStorage）
- 25 分钟定时器自动刷新 Token
- 刷新失败时清除会话并重定向至登录页

### 权限感知 UI

- 侧边栏菜单根据权限显示/隐藏
- 操作按钮根据权限显示/隐藏（反馈管理、公告管理、用户操作）
- 风险操作使用 `RiskActionDialog` 组件要求确认原因
- 全局搜索仅对拥有 `search:global` 权限的用户可用

### Cookie 安全

- Access Token 和 Refresh Token 存储在 HttpOnly Cookie 中
- `Secure` 标志在生产环境启用（要求 HTTPS）
- `SameSite=Lax` 提供 CSRF 基础保护

## 7. 测试覆盖

| 测试文件 | 覆盖范围 |
|----------|----------|
| `test_admin_auth.py` | 管理员登录、刷新、登出、/me |
| `test_admin_sensitive_actions.py` | 角色变更、禁用、强制下线、最后 Owner 保护 |
| `test_admin_csrf.py` | CSRF 中间件拦截与放行 |
| `test_token_invalidation.py` | 密码修改后 Token 失效、Refresh Token 重放检测 |
| `test_privacy_redaction.py` | IP 掩码/哈希、邮箱掩码、审计日志脱敏、禁止键过滤 |
| `test_admin_feedback.py` | 反馈管理权限分级 |
| `test_admin_announcements.py` | 公告管理权限分级 |
| `test_admin_dashboard.py` | 仪表盘权限 |
| `test_admin_users.py` | 用户列表权限 |
| `test_admin_monitoring.py` | 监控权限 |

运行测试：

```bash
cd cloud-server
.venv/Scripts/python.exe -m pytest tests/ -v
```
