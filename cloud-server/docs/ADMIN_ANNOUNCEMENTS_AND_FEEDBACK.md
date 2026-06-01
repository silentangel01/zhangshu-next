# 管理员操作指南：公告通知与用户反馈

本文档面向章枢云服务管理员，说明如何配置管理员权限、发布公告、查看和管理用户反馈。

## 1. 管理员权限配置

### 1.1 环境变量 `ADMIN_EMAILS`

在 `cloud-server/.env` 中添加管理员邮箱白名单（逗号分隔）：

```bash
ADMIN_EMAILS=admin@example.com,ops@example.com
```

白名单中的邮箱注册登录后自动拥有管理员权限。

### 1.2 数据库设置 `is_admin`

也可以通过 API 或数据库直接将用户的 `is_admin` 字段设为 `true`：

```sql
UPDATE users SET is_admin = true WHERE email = 'admin@example.com';
```

### 1.3 获取管理员 Token

使用管理员账号登录后获取 JWT access token：

```bash
curl -X POST https://<CLOUD_HOST>/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "<PASSWORD>"}'
```

保存返回的 `access_token` 用于后续操作：

```bash
export ACCESS_TOKEN=<ACCESS_TOKEN>
```

---

## 2. 发布公告

### 2.1 创建公告（草稿）

```bash
curl -X POST https://<CLOUD_HOST>/api/admin/announcements \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "系统维护通知",
    "body": "今晚 23:00 至次日 01:00 进行云备份服务维护，届时云备份功能暂停使用。",
    "severity": "warning",
    "platform": null
  }'
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `title` | string | 是 | 标题，最多 120 字 |
| `body` | string | 是 | 正文，纯文本（不支持 HTML） |
| `severity` | string | 否 | `info` / `success` / `warning` / `critical`，默认 `info` |
| `audience` | string | 否 | 目前仅支持 `all` |
| `platform` | string | 否 | `windows` / `macos` / `linux`，不填则所有平台 |
| `min_app_version` | string | 否 | 最小客户端版本 |
| `max_app_version` | string | 否 | 最大客户端版本 |
| `starts_at` | datetime | 否 | 公告生效开始时间（ISO 8601） |
| `ends_at` | datetime | 否 | 公告生效结束时间（ISO 8601） |

### 2.2 发布公告

```bash
curl -X POST https://<CLOUD_HOST>/api/admin/announcements/<ANNOUNCEMENT_ID>/publish \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 2.3 查看公告列表

```bash
curl "https://<CLOUD_HOST>/api/admin/announcements?status=published&limit=20" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 2.4 归档公告

```bash
curl -X POST https://<CLOUD_HOST>/api/admin/announcements/<ANNOUNCEMENT_ID>/archive \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 2.5 删除公告

```bash
curl -X DELETE https://<CLOUD_HOST>/api/admin/announcements/<ANNOUNCEMENT_ID> \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

---

## 3. 管理用户反馈

### 3.1 查看反馈列表

```bash
curl "https://<CLOUD_HOST>/api/admin/feedback?status=open&category=bug&limit=50" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

**筛选参数：**

| 参数 | 说明 |
|------|------|
| `status` | `open` / `triaged` / `in_progress` / `closed` / `spam` |
| `category` | `bug` / `suggestion` / `data_loss` / `cloud` / `ui` / `other` |
| `limit` | 每页条数（1-200） |
| `offset` | 偏移量 |

### 3.2 查看单条反馈详情

```bash
curl "https://<CLOUD_HOST>/api/admin/feedback/<FEEDBACK_ID>" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### 3.3 更新反馈状态

```bash
curl -X PATCH "https://<CLOUD_HOST>/api/admin/feedback/<FEEDBACK_ID>" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "status": "triaged",
    "priority": "high",
    "admin_note": "已复现，排入下个迭代修复。"
  }'
```

### 3.4 下载反馈附件

```bash
curl "https://<CLOUD_HOST>/api/admin/feedback/<FEEDBACK_ID>/attachments/<ATTACHMENT_ID>/download-url" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

返回短期有效的签名下载 URL（默认 30 分钟）。

### 3.5 删除反馈

```bash
curl -X DELETE "https://<CLOUD_HOST>/api/admin/feedback/<FEEDBACK_ID>" \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

软删除反馈记录，并删除 OSS 中的附件文件。

---

## 4. 安全注意事项

- **不要把 admin token、JWT、OSS Key 写入文档示例** — 始终使用 `<ACCESS_TOKEN>` 等占位符。
- 管理员接口仅通过 API 和 Swagger 访问，不在普通桌面客户端中暴露。
- presigned URL 不会出现在日志、审计日志或错误提示中。
- 查看用户反馈时，联系方式仅管理员可见。
- 账号删除后，用户反馈自动匿名化（移除 `user_id` 和 `contact_email`），附件 OSS 对象被删除。

## 5. OSS 生命周期建议

- 为 `feedback/` 前缀配置 **180-365 天** 生命周期规则。
- 已关闭（`closed`）或标记为垃圾（`spam`）的反馈附件可定期清理。
- 示例 OSS Lifecycle Rule：

```json
{
  "rules": [
    {
      "id": "feedback-cleanup",
      "prefix": "feedback/",
      "status": "Enabled",
      "expiration": { "days": 365 }
    }
  ]
}
```

## 6. 限流配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `RATE_LIMIT_FEEDBACK_CREATE_PER_HOUR` | 5 | 每小时反馈提交次数 |
| `RATE_LIMIT_FEEDBACK_UPLOAD_PER_HOUR` | 20 | 每小时附件上传次数 |

如遭受滥用攻击，可降低限流阈值或结合 IP 封禁处理。详见 `docs/INCIDENT_RUNBOOK.md`。
