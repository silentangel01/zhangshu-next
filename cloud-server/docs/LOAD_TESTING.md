# 负载测试指南

本文档说明如何运行 k6 负载测试来验证章枢云 API 的并发性能。

## 安装 k6

### Windows

```powershell
winget install k6
```

### macOS

```bash
brew install k6
```

### Linux (Debian/Ubuntu)

```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E34327
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt update && sudo apt install k6
```

## 运行测试

### 基础测试（无需认证）

```bash
cd cloud-server
k6 run load-tests/k6-cloud-api-smoke.js
```

测试内容：
- `/health` 和 `/ready` 端点响应时间
- `/api/auth/login` 限流行为（429 响应）

### 完整测试（含管理员端点）

```bash
# 先获取管理员 token
ADMIN_TOKEN=$(curl -s http://127.0.0.1:9000/api/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "..."}' \
  | python -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))")

# 运行完整测试
k6 run --env ADMIN_TOKEN=$ADMIN_TOKEN load-tests/k6-cloud-api-smoke.js
```

### 远程服务器测试

```bash
k6 run --env BASE_URL=https://api.example.com load-tests/k6-cloud-api-smoke.js
```

## 性能目标

| 端点 | p95 目标 | 说明 |
|------|----------|------|
| `/health` | < 100ms | 纯内存检查 |
| `/ready` | < 200ms | 含 DB 和 Redis 健康检查 |
| `/api/admin/dashboard/summary` | < 300ms | 缓存命中时 |
| `/api/admin/search?q=keyword` | < 500ms | 使用 pg_trgm 索引 |
| `/api/auth/login` | 正确返回 429 | 5 次/分钟限流生效 |

## 测试场景

当前脚本包含以下阶段：

```
 0s ─── 10s:  5 VUs (预热)
10s ─── 30s:  5 VUs (稳态)
30s ─── 40s: 20 VUs (压力峰值，触发限流)
40s ─── 50s:  5 VUs (恢复)
50s ─── 60s:  0 VUs (结束)
```

## 结果分析

### 关键指标

- **http_req_duration p(95)**: 95% 请求的响应时间应低于目标
- **http_req_failed**: 错误率应 < 5%（429 限流不算错误）
- **auth_rate_limited**: 压力阶段应观察到限流触发
- **dashboard_duration p(95)**: 多次请求应命中缓存，响应时间稳定

### 输出文件

测试结果自动保存到 `load-tests/results/smoke-summary.json`。

## 自定义测试

### 增加并发

```bash
k6 run --vus 50 --duration 60s load-tests/k6-cloud-api-smoke.js
```

### 只测试特定端点

```bash
k6 run --env SKIP_ADMIN=true load-tests/k6-cloud-api-smoke.js
```

## 常见问题

### 连接池耗尽

如果看到 `pool_timeout` 错误，说明 `API_WORKERS × (POOL_SIZE + MAX_OVERFLOW)` 不够。增加 `DATABASE_POOL_SIZE` 或 `DATABASE_MAX_OVERFLOW`。

### Redis 连接超时

检查 Redis 容器资源限制。高并发下可能需要增加 Redis 的 `maxclients`。

### 429 过多

Nginx 限流和应用层限流可能叠加。如果正常用户被误限，可以调大 Nginx `burst` 值或提高 rate。

### 搜索超时

确认 PostgreSQL `pg_trgm` 索引已创建（Alembic 迁移 008）。可以用以下命令验证：

```bash
docker compose exec postgres psql -U zhangshu -d zhangshu_cloud \
  -c "SELECT indexname FROM pg_indexes WHERE tablename = 'users';"
```

## 扩展阅读

- [k6 文档](https://k6.io/docs/)
- [k6 HTTP API](https://k6.io/docs/javascript-api/k6-http/)
- [k6 阈值](https://k6.io/docs/using-k6/thresholds/)
