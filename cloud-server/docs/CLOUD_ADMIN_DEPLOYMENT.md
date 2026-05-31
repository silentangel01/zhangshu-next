# Cloud Admin Dashboard Deployment Guide

This document describes how to deploy the Zhangshu Cloud Admin dashboard.

## Prerequisites

- A running `cloud-server` instance with at least one admin user
- Node.js 20+ for building the admin frontend
- Nginx or similar reverse proxy for serving the admin UI

## Setting Up Admin Access

### Role-Based Access Control (RBAC)

Admin users are assigned one of five roles that determine their permissions:

| Role | Description |
|------|-------------|
| `owner` | Full access including role management |
| `admin` | Day-to-day management (all except role changes) |
| `support` | Customer support: view feedback, reply, view users |
| `ops` | Operations: monitoring, audit logs, announcements |
| `readonly` | Read-only access to dashboards and lists |

### Option 1: Environment Variable (Bootstrap)

Set the `ADMIN_EMAILS` environment variable before starting `cloud-server`:

```bash
export ADMIN_EMAILS="admin@example.com,admin2@example.com"
```

Users with these email addresses will automatically have `owner` role access even if `admin_role` is not set in the database.

### Option 2: Database

Update the `admin_role` field in the `users` table:

```sql
UPDATE users SET admin_role = 'owner' WHERE email = 'admin@example.com';
UPDATE users SET admin_role = 'support' WHERE email = 'support@example.com';
```

Legacy `is_admin` flag is also supported and maps to the `owner` role.

## Building the Admin Frontend

```bash
cd cloud-admin
npm install
npm run build
```

The build output will be in `cloud-admin/dist/`.

## Nginx Configuration

Deploy the admin UI to a path like `/admin/`:

```nginx
server {
    listen 443 ssl http2;
    server_name cloud.example.com;

    # Cloud server API
    location /api/ {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Admin frontend
    location /admin/ {
        alias /var/www/cloud-admin/dist/;
        try_files $uri $uri/ /admin/index.html;
    }

    # Redirect root to admin
    location = / {
        return 302 /admin/;
    }
}
```

## Security Requirements

### HTTPS

The admin dashboard **requires HTTPS** in production. The admin authentication uses HttpOnly Secure cookies which will not be transmitted over plain HTTP.

### CSRF Protection

In production (`ADMIN_REQUIRE_ORIGIN_CHECK=true`), all admin write requests (POST, PUT, PATCH, DELETE) require the custom header `X-Zhangshu-Admin-Request: 1`. The cloud-admin frontend automatically includes this header via the `apiRequest()` function.

If you access the admin API from tools like `curl` or Postman, include the header:

```bash
curl -X POST https://cloud.example.com/api/admin/auth/logout \
  -H "X-Zhangshu-Admin-Request: 1" \
  -b "zs_admin_token=..."
```

### Bearer Token Fallback

In production (`ENVIRONMENT=production`), Bearer token authentication is disabled for admin endpoints. All admin requests must use HttpOnly cookies obtained via the `/api/admin/auth/login` endpoint.

For local development or API testing, enable fallback:

```bash
export ADMIN_ALLOW_BEARER_FALLBACK=true
```

### Cookie Settings

The following settings are configured in `cloud-server`:

| Setting | Default | Description |
|---------|---------|-------------|
| `admin_cookie_secure` | `true` | Cookie requires HTTPS |
| `admin_cookie_samesite` | `lax` | CSRF protection level |
| `admin_access_token_expire_minutes` | `30` | Access token lifetime |
| `admin_refresh_token_expire_hours` | `8` | Refresh token lifetime |

### CORS Configuration

If the admin frontend is served from a different origin than the API, configure CORS in `cloud-server`:

```bash
export ADMIN_CORS_ORIGINS="https://admin.example.com"
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ADMIN_EMAILS` | No | Comma-separated list of owner-level admin emails |
| `JWT_SECRET_KEY` | Yes | Secret for signing admin tokens |
| `ENVIRONMENT` | No | `production` enables strict security (no Bearer fallback) |
| `ADMIN_REQUIRE_ORIGIN_CHECK` | No | `true` enables CSRF Origin validation + custom header |
| `ADMIN_ALLOW_BEARER_FALLBACK` | No | `true` allows Bearer token auth in production |
| `admin_cookie_secure` | No | Set to `false` only for local development |

## Running Locally for Development

```bash
# Terminal 1: Start cloud-server
cd cloud-server
.\.venv\Scripts\activate
uvicorn app.main:app --reload --port 8080

# Terminal 2: Start admin frontend dev server
cd cloud-admin
npm run dev
```

The admin frontend will run on `http://localhost:5190` and proxy API requests to `http://localhost:8080`.

For local development without HTTPS, set:

```bash
export admin_cookie_secure=false
```

## Verification Checklist

After deployment, verify:

- [ ] Admin login page loads at `/admin/`
- [ ] Login with admin credentials succeeds
- [ ] Dashboard shows user counts and activity
- [ ] Sidebar menu only shows items the current role has permission for
- [ ] Admin role label displays correctly in sidebar footer
- [ ] Feedback list loads and detail page works
- [ ] User list loads and detail page shows expected data (no password_hash, tokens)
- [ ] User detail: management operations only visible with proper permissions
- [ ] Announcement: create/publish/delete buttons only visible with proper permissions
- [ ] Logout clears cookies and redirects to login
- [ ] Non-admin users cannot access admin API endpoints
- [ ] Page refresh after session expiry redirects to login (not just sessionStorage check)
- [ ] Audit logs show masked IPs (e.g., `192.168.1.xxx`), not raw IPs

## Troubleshooting

### "401 Unauthorized" after login

- Check that the user has `is_admin = true` or is in `ADMIN_EMAILS`
- Verify `JWT_SECRET_KEY` is set and consistent across restarts
- Check browser cookies — access and refresh tokens should be present

### Cookies not being set

- Ensure HTTPS is enabled (or `admin_cookie_secure=false` for local dev)
- Check that `SameSite` policy allows the cookie (should be `lax` or `none` with Secure)
- Verify the API and frontend are on the same domain (or CORS is configured)

### Dashboard shows zeros

- Check that `cloud-server` has users and activity data
- Verify the admin API endpoints are accessible: `curl -H "Authorization: Bearer $TOKEN" https://cloud.example.com/api/admin/dashboard/summary`
