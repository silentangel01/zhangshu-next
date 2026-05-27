---
date: 2026-05-28
task: admin-monitoring-dashboard
codex_plan: plan file (quirky-fluttering-star.md)
---

## Task Summary
实现管理后台"运维监控"页面，展示阿里云 BSS 账户余额、OSS 存储详情、轻量应用服务器（SWAS）运行状态和实时监控数据（CPU/内存/磁盘/网络）。

## Files Changed

### 后端 (cloud-server)
- 修改：`cloud-server/app/core/config.py` — 新增 4 个监控配置字段（`aliyun_monitor_access_key_id`、`aliyun_monitor_access_key_secret`、`swas_instance_id`、`swas_region_id`）
- 新增：`cloud-server/app/infrastructure/aliyun_monitor.py` — 三个阿里云 API 客户端类（`BSSMonitor`、`OSSMonitor`、`SWASMonitor`），封装 BSS 余额查询、OSS 存储统计、SWAS 实例信息和监控数据
- 新增：`cloud-server/app/services/admin_monitoring_service.py` — 带内存缓存的聚合服务，类级别 `_cache` dict，每个模块独立 TTL（billing: 1h, oss: 1h, server: 5min），支持部分失败容错
- 新增：`cloud-server/app/schemas/admin_monitoring.py` — Pydantic 响应模型（`ModuleResponse`、`MonitoringOverviewResponse`）
- 新增：`cloud-server/app/api/admin_monitoring.py` — 两个路由（`GET /overview`、`POST /refresh`）
- 修改：`cloud-server/app/main.py` — 注册 `admin_monitoring_router`

### 前端 (cloud-admin)
- 新增：`cloud-admin/src/entities/admin-monitoring/types.ts` — TypeScript 接口定义
- 新增：`cloud-admin/src/entities/admin-monitoring/api.ts` — API 客户端封装
- 新增：`cloud-admin/src/pages/MonitoringPage.vue` — 监控页面（四卡片布局：余额、OSS、服务器状态、资源监控）
- 修改：`cloud-admin/src/router/index.ts` — 新增 `/monitoring` 路由
- 修改：`cloud-admin/src/components/AdminLayout.vue` — 侧边栏新增"运维监控"链接

## Implementation Notes

### SDK 安装
- `alibabacloud_bssopenapi20171214` — BSS 余额查询
- `alibabacloud_swas_open20200601` — SWAS 服务器管理和监控
- `oss2` — 已安装（OSS 存储统计）

### 缓存设计
- 使用类变量 `_cache: dict[str, _CacheEntry]`（进程级共享），不依赖 Redis
- `threading.Lock` 保护缓存读写，避免并发请求重复调用阿里云 API
- fetcher 在锁外执行，避免慢 API 调用阻塞其他线程
- 每个模块独立 TTL：billing/oss 1h，server 5min（服务器状态变化更频繁）

### AccessKey 回退逻辑
- 优先使用 `aliyun_monitor_access_key_id`（RAM 只读子账号）
- 如未配置，回退到 `oss_access_key_id`（方便开发环境复用同一 AK）

### SWAS 监控指标
- CPU: `cpu_total`、内存: `memory_usedutilization`
- 磁盘读: `disk_readbytes`、磁盘写: `disk_writebytes`
- 入网: `networkin_rate`、出网: `networkout_rate`
- 查询最近 5 分钟数据，取最新数据点

### 部分失败容错
- 某个阿里云 API 调用失败时，该模块返回 `{ data: null, error: "错误消息" }`
- 其他模块正常返回，不影响整个页面

### 前端页面设计
- 2×2 网格布局 + 底部跨两列的资源监控卡片
- 每个卡片：加载态（全局 loading）、错误态（显示错误 + 重试按钮）、数据态
- CPU/内存使用进度条（绿/黄/红三色），磁盘/网络吞吐数字展示
- 服务器到期提醒（≤7天黄色警告，已过期红色标记）
- 缓存时间显示 + 单模块刷新按钮 + 全局刷新按钮

## Deviations from Codex Plan
无 Codex Plan（基于会话中的 plan file 实现）。

## Verification Commands Run
- `cd cloud-server && .venv/Scripts/python.exe -c "from app.infrastructure.aliyun_monitor import BSSMonitor, OSSMonitor, SWASMonitor"` → ✅
- `cd cloud-server && .venv/Scripts/python.exe -c "from app.services.admin_monitoring_service import AdminMonitoringService"` → ✅
- `cd cloud-server && .venv/Scripts/python.exe -c "from app.main import app"` → ✅
- 路由验证：`/api/admin/monitoring/overview` 和 `/api/admin/monitoring/refresh` 已注册 → ✅
- `cd cloud-admin && npx vue-tsc --build` → ✅
- `cd cloud-admin && npx vite build` → ✅ (67 modules, 718ms)

## Verification Results
- 后端所有模块导入正常
- 监控路由正确注册
- 前端 TypeScript 类型检查通过
- 前端生产构建成功

## Known Issues
- SWAS 实例 ID（`swas_instance_id`）和区域 ID（`swas_region_id`）需要在 `.env` 中配置，用户尚未提供实例 ID
- 阿里云 RAM 子账号需要附加 `AliyunBSSReadOnlyAccess`、`AliyunOSSReadOnlyAccess`、`AliyunSWASReadOnlyAccess` 策略
- BSS 余额查询需要主账号或已开通"费用中心"权限的 RAM 子账号
- `oss2.Bucket.get_bucket_stat()` 要求 bucket 开启统计功能（默认开启）
- SWAS 监控数据有约 1-3 分钟延迟（阿里云侧限制）

## Suggested Next Review Points for Codex
- 缓存使用类变量（进程级），如果 cloud-server 改为多 worker 部署，缓存不共享——是否需要改为 Redis？
- `_fetch_oss()` 使用 `effective_internal_endpoint`（内网），但 BSS/SWAS 使用公网 endpoint——是否需要在 VPC 外部署时回退到公网 OSS endpoint？
- 前端 `MonitoringPage.vue` 在移动端（<768px）的 2 列网格可能需要调整为 1 列
- 监控数据是否需要历史趋势图？当前只显示最新值
