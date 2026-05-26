---
date: 2026-05-26
task: 云网络韧性增强 (Cloud Network Resilience Enhancement)
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

将章枢云连接从"无条件 No-SNI/CERT_NONE 单一策略"升级为"策略链 + 网络诊断 + 双 endpoint"架构，覆盖桌面端后端、前端、云服务端共 8 个阶段。

## Files Changed

### 桌面端后端

- 新增：`backend/app/infrastructure/cloud_network_diagnostics.py` — 7 步网络诊断工具
- 新增：`backend/app/services/cloud_network_service.py` — 网络设置与诊断编排服务
- 修改：`backend/app/infrastructure/cloud_api_client.py` — 策略链重构 (auto → secure_direct → system_proxy → compat_no_sni)
- 修改：`backend/app/services/cloud_auth_service.py` — 传播 error_kind/suggestion、网络模式管理
- 修改：`backend/app/services/cloud_backup_service.py` — 传播 error_kind/suggestion
- 修改：`backend/app/services/app_config_service.py` — 新增 cloud_network_mode / cloud_last_working_mode key
- 修改：`backend/app/api/cloud.py` — 新增 3 个网络端点 + _build_error_detail 辅助函数
- 修改：`backend/app/schemas/cloud.py` — 新增网络设置/诊断 schema

### 桌面端前端

- 新增：`frontend/src/features/cloud/CloudNetworkDiagnosticsPanel.vue` — 诊断面板组件
- 修改：`frontend/src/entities/cloud/types.ts` — CloudNetworkMode/Settings/DiagnosticReport 类型
- 修改：`frontend/src/entities/cloud/api.ts` — 3 个新 API 封装
- 修改：`frontend/src/features/app-config/AppSettingsDialog.vue` — 集成诊断面板
- 修改：`frontend/src/features/cloud/CloudAccountDialog.vue` — 登录失败时显示诊断入口
- 修改：`frontend/src/features/cloud/CloudBackupPanel.vue` — OSS 错误识别

### 云服务端

- 修改：`cloud-server/app/core/config.py` — oss_public_endpoint / oss_internal_endpoint
- 修改：`cloud-server/app/infrastructure/oss_storage.py` — 双 Bucket 模式
- 修改：`cloud-server/.env.example` — 双 endpoint 示例
- 修改：`cloud-server/README.md` — endpoint 文档
- 修改：`cloud-server/deploy/README.md` — 部署后 OSS 端点验证

### 测试

- 新增：`backend/tests/test_cloud_api_client_network_modes.py` — 26 个测试
- 新增：`backend/tests/test_cloud_network_diagnostics.py` — 12 个测试
- 修改：`backend/tests/test_cloud_api.py` — 新增 6 个网络端点测试
- 修改：`backend/tests/test_cloud_backup_service.py` — 修复 2 个预存测试问题
- 新增：`cloud-server/tests/test_oss_endpoint_config.py` — 8 个测试

## Implementation Notes

1. **策略链设计**：auto 模式按 secure_direct → system_proxy → compat_no_sni 顺序尝试。非网络错误 (401/403/404) 不触发 fallback，避免不必要的重试。
2. **安全约束**：远程 HTTP 地址被 `_check_url_security()` 拒绝；localhost/127.0.0.1/::1 的 HTTP 联调不受影响。
3. **错误传播链**：`CloudApiError.error_kind/suggestion` → `CloudAuthError`/`CloudBackupError` → API `_build_error_detail()` → 前端。当存在 error_kind 时，HTTP detail 从 string 变为 dict `{message, error_kind, suggestion}`。
4. **OSS 双 Bucket**：presigned URL 使用 public bucket，head/delete 使用 internal bucket。生成 presigned URL 后防御性检查是否包含 `-internal.aliyuncs.com`。
5. **日志安全**：不记录 Authorization、presigned URL query、密码、refresh token。`_parse_oss_error()` 只提取 Code/Message。

## Deviations from Codex Plan

- Codex Plan 中 Phase 1 提到 `KEY_CLOUD_LAST_DIAGNOSTIC` 配置 key，实际未实现。当前只保存 `cloud_network_mode` 和 `cloud_last_working_mode`。诊断报告不持久化存储，每次运行时生成。
- Codex Plan 提到 `cloud_proxy_url` 加密存储，实际未实现代理 URL 配置功能（V1 不支持带认证的代理 URL）。

## Verification Commands Run

- `python -c "from app.main import app; print('ok')"` → ✅ (backend)
- `pytest tests/ -q` → ✅ 443 passed (backend)
- `pytest tests/test_cloud_api_client_network_modes.py -q` → ✅ 26 passed
- `pytest tests/test_cloud_network_diagnostics.py -q` → ✅ 12 passed
- `pytest tests/test_cloud_api.py -q` → ✅ 14 passed
- `pytest tests/ -q` → ✅ 45 passed (cloud-server)
- `npm run type-check` → ✅ (frontend)
- `npm run build` → ✅ (frontend)

## Verification Results

全部验证通过。后端 443 测试、云服务端 45 测试、前端 type-check 和 build 均无错误。

## Known Issues

- `system_proxy` 模式在 Windows Tauri 打包环境中可能不继承 `HTTP_PROXY/HTTPS_PROXY` 环境变量，需要用户在代理软件中为 `api.emailbs.xin` 配置规则。
- `compat_no_sni` 使用 `CERT_NONE`，存在中间人风险。UI 已标注为"兼容模式"并提示安全风险。
- 手动验证（普通网络、代理网络、校园/公司网络各一轮）需用户在实际环境中完成。

## Suggested Next Review Points for Codex

1. `error_kind` dict detail 是否影响前端已有的错误消息解析逻辑？需要确认前端 `getErrorMessage()` 能处理 dict 类型 detail。
2. `KEY_CLOUD_LAST_DIAGNOSTIC` 是否需要实现？当前诊断报告不持久化。
3. 代理 URL 配置是否需要在 V2 中支持？当前 V1 只支持模式切换。
4. `compat_no_sni` 在 TLS 1.3 环境中的行为是否需要额外测试？
