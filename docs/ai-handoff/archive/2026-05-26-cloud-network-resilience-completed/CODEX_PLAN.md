<!-- archived: 2026-05-26; reason: cloud network resilience task completed, superseded by production hardening planning -->

# Task Summary

本次任务是规划章枢云功能的网络适配与防护性改进，目标是在用户挂代理、使用校园网、公司网、运营商网络、网络 DNS/TLS/OSS endpoint 异常时，尽量避免登录、注册、云备份出现“只有开发者能排查”的连接问题。

重点不是新增云业务功能，而是增强现有云连接链路的鲁棒性：

- 把当前临时的 `IP 直连 + No-SNI + 关闭证书验证` 改造成可诊断、可回退、可配置的连接策略。
- 为用户提供“云服务连接诊断”入口和可理解的错误提示。
- 对代理、校园/公司网络 DPI/SNI 过滤、OSS 内外网 endpoint、TLS/HTTP2 兼容等场景增加防护。
- 云服务端补齐 OSS 公网/内网双 endpoint，避免预签名 URL 再次返回内网地址。
- 明确生产云 API 必须使用 HTTPS；仅允许 `localhost`、`127.0.0.1`、`::1` 等本地开发地址继续使用 HTTP，避免安全加固误伤本地联调。

Codex 未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

- 已阅读 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`，该活跃执行报告是“统一前端时间显示格式”，与当前云连接任务无直接关系，已按用户要求归档到：
  - `docs/ai-handoff/archive/2026-05-26-pre-network-resilience/CLAUDE_EXECUTION_REPORT.md`
- 已阅读并归档旧活跃计划：
  - `docs/ai-handoff/archive/2026-05-26-pre-network-resilience/CODEX_PLAN.md`
- 已阅读云服务连接问题文档：
  - `docs/Cloud_Service_Connection_Troubleshooting.md`
  - `docs/ai-handoff/CLOUD_DEPLOYMENT_LOG.md`
- 两份云连接文档确认的关键问题：
  - 国内服务器部署时 Docker、Docker Hub、PyPI 镜像源容易超时。
  - Python / Nginx TLS 组合曾出现误导性 `bad key share` 日志。
  - Clash / TUN / 系统代理可能影响 httpx 行为。
  - 校园网 DPI 会根据 TLS SNI 字段重置 `api.emailbs.xin` 连接。
  - 当前临时解决方式是 IP 直连、手动 Host 头、No-SNI、`CERT_NONE`、`trust_env=False`。
  - OSS 预签名 URL 曾因 `OSS_ENDPOINT=oss-cn-hangzhou-internal.aliyuncs.com` 返回阿里云内网地址，导致桌面端公网环境上传 403。
- 当前 `backend/app/infrastructure/cloud_api_client.py` 的状态：
  - 所有 HTTPS 云 API 都会自动把域名解析为 IP。
  - 所有请求都使用 No-SNI SSLContext。
  - 当前 SSLContext 设置 `verify_mode = ssl.CERT_NONE`，会跳过证书验证。
  - 当前强制 `maximum_version = ssl.TLSVersion.TLSv1_2`。
  - 当前 `httpx.Client(..., trust_env=False)`，不读取系统代理环境变量。
  - 该实现能绕过校园网 SNI 过滤，但作为默认路径安全性和适配性都不够理想。
- 当前 `backend/app/api/cloud.py` 只有账号、登录、启用、备份相关 API，没有云网络诊断、网络模式设置或诊断报告 API。
- 当前 `frontend/src/features/cloud/CloudAccountDialog.vue` 登录/注册失败只展示通用错误，没有引导用户进行连接诊断。
- 当前 `frontend/src/features/app-config/AppSettingsDialog.vue` 有“章枢云账户”状态，但没有云网络连接策略、诊断入口或代理/校园网提示。
- 当前 `cloud-server/app/infrastructure/oss_storage.py` 只有单一 `oss_endpoint`，既用于生成客户端预签名 URL，也用于服务端 `head_object/delete_object`。
- 当前 `cloud-server/app/core/config.py` 没有 `OSS_PUBLIC_ENDPOINT` / `OSS_INTERNAL_ENDPOINT` 双 endpoint 配置。

# Architecture Decision

## 1. 云连接策略从“单一路径”升级为“策略链”

新增桌面端云连接策略枚举：

- `auto`：默认。先走安全直连，失败后按诊断结果尝试兼容路径。
- `secure_direct`：域名 + SNI + 正常证书验证 + 不使用系统代理。
- `system_proxy`：域名 + SNI + 正常证书验证 + 允许读取系统代理环境变量。
- `compat_no_sni`：IP 直连 + Host 头 + No-SNI，作为校园/公司网 DPI 过滤的兼容路径。

默认模式必须是 `auto`。不允许继续把 `compat_no_sni` 作为所有 HTTPS 请求的无条件默认路径。

## 2. 安全优先级

连接策略优先级：

1. 优先使用完整 TLS 校验的安全路径。
2. 只有在检测到 TLS 握手重置、SNI 疑似过滤等场景时，才允许自动尝试 `compat_no_sni`。
3. `compat_no_sni` 必须被标记为“兼容模式”，并在 UI 中提示：该模式会降低证书校验强度，只应在普通连接失败时使用。
4. 诊断日志不得记录 JWT、refresh token、密码、OSS 签名 URL 完整 query、API key。

## 3. HTTPS 生产约束与本地豁免

生产级章枢云 API 不允许使用明文 HTTP。`ZHANGSHU_CLOUD_API_BASE_URL` 如果指向公网域名或公网 IP，必须使用 `https://`。

允许 HTTP 的范围只限本地开发和测试：

- `http://localhost:<port>`
- `http://127.0.0.1:<port>`
- `http://[::1]:<port>`

这条规则不应影响章枢桌面端访问自己的本地 sidecar，也不应影响 Claude Code 在本机启动 `cloud-server` 做联调。它只用于阻止用户把生产云服务配置成 `http://api.example.com` 这类明文远程地址。

如果用户显式配置了远程 HTTP 地址，客户端应：

- 在账号登录、注册、云备份前阻止请求或至少给出高危警告。
- 在诊断报告中标记为 `insecure_remote_http`。
- 提示用户改为 HTTPS，或通过 Nginx / Caddy / 云负载均衡配置 TLS。

## 4. 网络诊断是独立能力

新增独立的本地诊断服务，不把诊断逻辑塞进登录、注册或备份业务逻辑中。

建议分层：

- Infrastructure：HTTP/TCP/DNS/TLS/OSS URL 诊断工具。
- Service：编排诊断流程，生成用户可读建议。
- API：暴露诊断和网络设置接口。
- Frontend：展示诊断结果和连接模式设置。

## 5. 云服务端 OSS 双 endpoint

云服务端应区分：

- `OSS_PUBLIC_ENDPOINT`：用于生成给桌面端使用的 presigned PUT/GET URL，必须公网可达。
- `OSS_INTERNAL_ENDPOINT`：用于云服务端自身 `head_object/delete_object`，可选，用于阿里云内网访问以节省流量。

保留 `OSS_ENDPOINT` 作为兼容配置，但 README 应明确：如果只配置一个 endpoint，它必须是公网 endpoint。

# Files to Create or Modify

## 桌面端后端

- 修改：`backend/app/infrastructure/cloud_api_client.py`
  - 引入连接策略链。
  - 不再默认所有 HTTPS 请求都使用 No-SNI + `CERT_NONE`。
  - 增加错误分类和策略选择。
  - 增加远程 HTTP 风险判断：公网远程地址必须 HTTPS，本地 `localhost/127.0.0.1/::1` 可继续 HTTP。
- 新增：`backend/app/infrastructure/cloud_network_diagnostics.py`
  - DNS、TCP、HTTPS、No-SNI、代理、OSS URL 可达性诊断。
- 新增：`backend/app/services/cloud_network_service.py`
  - 读取/保存云网络模式，编排诊断报告。
- 修改：`backend/app/services/app_config_service.py`
  - 增加云网络配置 key 常量。
- 修改：`backend/app/infrastructure/config_crypto.py`
  - 如果支持带账号密码的代理 URL，则将 `cloud_proxy_url` 加入 `SENSITIVE_KEYS`。
  - 若 V1 不支持代理账号密码，则无需保存代理 URL，只保存 mode。
- 新增或修改：`backend/app/schemas/cloud_network.py` 或 `backend/app/schemas/cloud.py`
  - 增加网络设置和诊断响应 schema。
- 修改：`backend/app/api/cloud.py`
  - 增加云网络诊断与设置 API。
- 修改：`backend/packaged_main.py`
  - 保留 `ZHANGSHU_CLOUD_API_BASE_URL` 默认值。
  - 不在这里硬编码网络兼容模式。

## 桌面端前端

- 修改：`frontend/src/entities/cloud/types.ts`
  - 增加 `CloudNetworkMode`、`CloudNetworkSettings`、`CloudNetworkDiagnosticReport` 类型。
- 修改：`frontend/src/entities/cloud/api.ts`
  - 增加获取/保存网络设置、运行诊断的 API 封装。
- 新增：`frontend/src/features/cloud/CloudNetworkDiagnosticsPanel.vue`
  - 诊断按钮、策略选择、结果展示、用户建议。
- 修改：`frontend/src/features/cloud/CloudAccountDialog.vue`
  - 登录/注册失败时展示“运行连接诊断”入口。
  - 错误提示根据诊断类别区分代理、网络拦截、服务端不可达、账号错误。
- 修改：`frontend/src/features/app-config/AppSettingsDialog.vue`
  - 在“章枢云账户”区域增加“网络连接”二级区域。
  - 不把诊断面板做成大段技术文档；只展示状态、建议和高级设置入口。
- 可选修改：`frontend/src/features/cloud/CloudBackupPanel.vue`
  - 云备份上传失败时识别 OSS 内网 endpoint、403、签名 URL 过期、网络超时，并显示更具体提示。

## 云服务端

- 修改：`cloud-server/app/core/config.py`
  - 增加 `oss_public_endpoint`、`oss_internal_endpoint`。
  - 保留 `oss_endpoint` 作为旧配置兼容。
- 修改：`cloud-server/app/infrastructure/oss_storage.py`
  - 使用 public bucket 生成 presigned URL。
  - 使用 internal bucket 执行 `head_object/delete_object`；未配置 internal 时回退 public。
- 修改：`cloud-server/.env.example`
  - 增加双 endpoint 示例。
- 修改：`cloud-server/README.md`
  - 增加公网/内网 endpoint 说明。
  - 增加校园网/公司网/代理排查说明。
- 修改：`cloud-server/deploy/README.md`
  - 增加部署后检查项：公网 health、OSS public presigned URL、CORS。
- 可选修改：`cloud-server/deploy/deploy.sh`
  - 生成 `.env` 时写出 `OSS_PUBLIC_ENDPOINT` 和 `OSS_INTERNAL_ENDPOINT` 注释。

## 测试

- 新增：`backend/tests/test_cloud_api_client_network_modes.py`
- 新增：`backend/tests/test_cloud_network_diagnostics.py`
- 修改：`backend/tests/test_cloud_api.py`
- 修改或新增：`cloud-server/tests/test_oss_endpoint_config.py`
- 修改或新增前端类型检查相关测试，如项目已有 Vitest，则补：
  - `frontend/src/features/cloud/__tests__/CloudNetworkDiagnosticsPanel.spec.ts`

# Implementation Steps for Claude Code

## Phase 1: 梳理现有临时方案并建立枚举

1. 读取 `backend/app/infrastructure/cloud_api_client.py`，保留现有 No-SNI 兼容逻辑，但不要让它无条件接管所有 HTTPS 请求。
2. 在后端定义连接模式：

```python
CloudNetworkMode = Literal["auto", "secure_direct", "system_proxy", "compat_no_sni"]
```

3. 在 `AppConfigService` 增加 key：

```python
KEY_CLOUD_NETWORK_MODE = "cloud_network_mode"
KEY_CLOUD_LAST_WORKING_MODE = "cloud_last_working_mode"
KEY_CLOUD_LAST_DIAGNOSTIC = "cloud_last_diagnostic"
```

4. 默认 `cloud_network_mode` 为 `auto`。
5. 仅在用户明确选择或 `auto` 策略诊断命中时才使用 `compat_no_sni`。

## Phase 2: 重构 CloudApiClient 为策略链

1. 在 `CloudApiClient.__init__` 中保留原始 base URL：
   - `_original_base_url`
   - `_hostname`
   - `_scheme`
2. 新增私有方法：

```python
_build_secure_direct_client(timeout) -> httpx.Client
_build_system_proxy_client(timeout) -> httpx.Client
_build_compat_no_sni_client(timeout) -> tuple[httpx.Client, str]
_is_local_development_url(url) -> bool
_is_insecure_remote_http(url) -> bool
_request_with_mode(mode, method, path, json, timeout)
_classify_http_error(exc) -> CloudNetworkErrorKind
```

3. 在发起云 API 请求前做 URL 安全检查：
   - 如果 base URL 是 `http://localhost`、`http://127.0.0.1` 或 `http://[::1]`，允许继续，用于本地开发和测试。
   - 如果 base URL 是 `http://` 且 host 不是本地地址，返回明确错误：`生产云服务必须使用 HTTPS，请将 ZHANGSHU_CLOUD_API_BASE_URL 改为 https://...`。
   - 不要阻止桌面端访问自己的本地 sidecar；本检查只针对 `CloudApiClient` 访问远程章枢云 API。
4. `secure_direct`：
   - URL 使用原始域名。
   - `verify=True`。
   - `trust_env=False`。
5. `system_proxy`：
   - URL 使用原始域名。
   - `verify=True`。
   - `trust_env=True`。
   - 用于允许用户/系统代理接管请求。
6. `compat_no_sni`：
   - URL 使用解析后的 IP。
   - Header 带 `Host: 原始域名`。
   - `trust_env=False`。
   - SSLContext 可复用当前 `_build_no_sni_context()`，但必须用注释明确这是兼容路径。
7. `auto`：
   - 优先尝试 `secure_direct`。
   - 如果失败类型是代理/DNS/连接重置/SSL 握手失败，再尝试 `system_proxy`。
   - 如果仍失败且错误疑似 SNI 过滤，再尝试 `compat_no_sni`。
   - 如果某模式成功，可把 `cloud_last_working_mode` 保存为非敏感配置，但不要永久覆盖用户选择。
8. 登录、注册、项目、备份 API 都使用该策略链。
9. OSS `upload_backup(upload_url, content)` 不应使用 Cloud API 的 No-SNI 逻辑；它连接的是 OSS presigned URL，必须：
   - `trust_env` 根据网络模式决定；
   - 默认先直连；
   - 如果用户选择 `system_proxy`，允许代理；
   - 上传失败时解析 OSS 错误 XML，但不要输出完整签名 query。

## Phase 3: 新增网络诊断服务

1. 新建 `backend/app/infrastructure/cloud_network_diagnostics.py`。
2. 实现诊断步骤：
   - `config_check`：确认 `ZHANGSHU_CLOUD_API_BASE_URL` 是否存在、scheme 是否为 http/https。
   - `https_policy_check`：确认远程云 API 使用 HTTPS；本地 `localhost/127.0.0.1/::1` 允许 HTTP。
   - `dns_check`：解析 hostname，返回 IP 列表和耗时。
   - `tcp_check`：对 host:port 做 TCP 连接测试。
   - `secure_https_check`：用域名 + SNI + 证书验证 GET `/health`。
   - `system_proxy_check`：`trust_env=True` GET `/health`。
   - `compat_no_sni_check`：IP + Host + No-SNI GET `/health`。
   - `api_contract_check`：GET `/health` 或 `/api/auth/me`，无 token 时只验证服务是否可达。
3. 每一步返回：

```json
{
  "name": "secure_https",
  "ok": false,
  "latency_ms": 123,
  "error_kind": "tls_reset_or_sni_filtered",
  "message": "普通 HTTPS 连接被重置，可能是校园网或公司网拦截。",
  "suggestion": "可尝试系统代理或兼容模式。"
}
```

4. 错误分类建议：
   - `not_configured`
   - `invalid_url`
   - `dns_failed`
   - `tcp_unreachable`
   - `timeout`
   - `tls_failed`
   - `tls_reset_or_sni_filtered`
   - `proxy_required_or_interfered`
   - `http_status_error`
   - `cloud_unavailable`
   - `insecure_remote_http`
   - `oss_internal_endpoint`
   - `oss_forbidden_or_signature_error`
   - `unknown`
5. 诊断不得携带密码、token、refresh token。
6. 诊断响应 schema 应保留机器可读字段和用户可读建议。

## Phase 4: 新增本地 API

在 `backend/app/api/cloud.py` 增加：

1. `GET /api/cloud/network/settings`
   - 返回：

```json
{
  "mode": "auto",
  "last_working_mode": "secure_direct",
  "base_url_configured": true
}
```

2. `PUT /api/cloud/network/settings`
   - 请求：

```json
{"mode": "auto"}
```

   - 只允许四种 mode。
   - 如果用户设置 `compat_no_sni`，后端允许保存，但前端必须显示安全提示。
3. `POST /api/cloud/network/diagnose`
   - 请求可为空，或支持：

```json
{"include_oss": false}
```

   - 返回完整诊断报告。
4. 不要让这些接口触发登录、注册或上传备份。

## Phase 5: 前端设置和诊断面板

1. 在 `frontend/src/entities/cloud/types.ts` 增加类型：

```ts
export type CloudNetworkMode = 'auto' | 'secure_direct' | 'system_proxy' | 'compat_no_sni'

export interface CloudNetworkSettings {
  mode: CloudNetworkMode
  last_working_mode: CloudNetworkMode | null
  base_url_configured: boolean
}

export interface CloudNetworkDiagnosticStep {
  name: string
  ok: boolean
  latency_ms: number | null
  error_kind: string
  message: string
  suggestion: string
}

export interface CloudNetworkDiagnosticReport {
  ok: boolean
  recommended_mode: CloudNetworkMode
  summary: string
  steps: CloudNetworkDiagnosticStep[]
}
```

2. 在 `frontend/src/entities/cloud/api.ts` 增加：
   - `getCloudNetworkSettings()`
   - `setCloudNetworkSettings(mode)`
   - `runCloudNetworkDiagnostics()`
3. 新建 `CloudNetworkDiagnosticsPanel.vue`：
   - 顶部显示当前连接模式。
   - 提供“检测连接”按钮。
   - 用简洁列表显示 DNS、端口、HTTPS、代理、兼容模式结果。
   - 只在“高级设置”中暴露连接模式选择。
   - `compat_no_sni` 旁边显示提示：普通连接失败时才建议使用。
4. 修改 `AppSettingsDialog.vue`：
   - 在“章枢云账户”字段组下加入“网络连接”折叠区或二级区域。
   - 避免把诊断详情铺满主设置页。
5. 修改 `CloudAccountDialog.vue`：
   - 登录/注册失败时，如果错误不是 401 账号密码错误，显示“运行连接诊断”按钮。
   - 诊断后根据结果提示：
     - “可能被校园/公司网络拦截”
     - “可能需要使用系统代理”
     - “云服务暂时不可达”
     - “本地未配置云服务地址”

## Phase 6: OSS 预签名 URL 防护

1. 修改 `cloud-server/app/core/config.py`：

```python
oss_endpoint: str = "oss-cn-hangzhou.aliyuncs.com"
oss_public_endpoint: str = ""
oss_internal_endpoint: str = ""
```

2. 规则：
   - public endpoint = `OSS_PUBLIC_ENDPOINT or OSS_ENDPOINT`
   - internal endpoint = `OSS_INTERNAL_ENDPOINT or public endpoint`
3. 修改 `cloud-server/app/infrastructure/oss_storage.py`：
   - `_public_bucket` 用于 `generate_put_url()` 和 `generate_get_url()`。
   - `_internal_bucket` 用于 `head_object()` 和 `delete_object()`。
4. 在生成 presigned URL 后增加防御性检查：
   - 如果 URL host 包含 `-internal.aliyuncs.com`，记录 error，并返回服务端错误：

```json
{"detail": "云存储上传地址配置为内网地址，桌面端无法访问，请联系管理员修正 OSS_PUBLIC_ENDPOINT。"}
```

5. 修改 `.env.example`：

```env
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_PUBLIC_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_INTERNAL_ENDPOINT=oss-cn-hangzhou-internal.aliyuncs.com
```

6. 修改 `README.md` 和 `deploy/README.md`：
   - 明确“预签名 URL 给桌面端使用，必须公网可达”。
   - 服务端自用可配置 internal endpoint。

## Phase 7: 错误信息和日志收敛

1. 后端 `CloudApiError` 增加可选字段：
   - `status_code`
   - `error_kind`
   - `suggestion`
2. 本地 API 捕获连接异常时，返回更具体但不暴露敏感信息的 detail。
3. 日志规则：
   - 不记录完整 Authorization。
   - 不记录完整 presigned URL query。
   - 不记录密码、refresh token。
   - 可以记录 hostname、错误类型、耗时、策略模式。
4. 上传 OSS 失败时：
   - 若 response body 是 OSS XML，只提取 `Code` 和 `Message`，不要把完整 URL 打进日志。
   - 403 时提示可能原因：签名过期、Content-Type 不匹配、CORS、endpoint 内外网错误。

## Phase 8: 测试

1. `backend/tests/test_cloud_api_client_network_modes.py`
   - mock httpx，验证 `auto` 会先试 `secure_direct`。
   - secure 成功时不会触发 `compat_no_sni`。
   - secure 连接重置时会尝试 `system_proxy` / `compat_no_sni`。
   - 手动 `secure_direct` 不会使用 No-SNI。
   - 手动 `compat_no_sni` 会使用 Host 头。
2. `backend/tests/test_cloud_network_diagnostics.py`
   - 未配置 base URL 返回 `not_configured`。
   - 远程 HTTP 地址返回 `insecure_remote_http`。
   - `http://127.0.0.1:9000`、`http://localhost:9000`、`http://[::1]:9000` 不返回 `insecure_remote_http`。
   - DNS 失败返回 `dns_failed`。
   - TCP 不通返回 `tcp_unreachable`。
   - TLS reset 分类为 `tls_reset_or_sni_filtered`。
   - 诊断响应不包含 token。
3. `backend/tests/test_cloud_api.py`
   - 覆盖新增 `/api/cloud/network/settings`、`/api/cloud/network/diagnose`。
4. `cloud-server/tests/test_oss_endpoint_config.py`
   - public endpoint 生成的 presigned URL 不包含 `-internal.aliyuncs.com`。
   - internal endpoint 用于 head/delete。
   - 未设置 public endpoint 时回退到 `OSS_ENDPOINT`。
5. 前端：
   - 至少运行 type-check。
   - 如项目已有前端测试基础，再补 CloudNetworkDiagnosticsPanel 的状态渲染测试。

# Constraints

- 不要移除现有云登录、注册、备份 API 契约。
- 不要把云网络诊断逻辑混入 UI 组件、登录服务或备份服务主体流程。
- 不要继续默认所有 HTTPS 云请求都关闭证书验证。
- 不要让用户在普通设置页里看到过多 TLS/SNI/HTTP2 技术细节；技术细节可放在诊断详情中。
- 不要把代理账号密码、JWT、refresh token、OSS 签名 URL 写入日志。
- 不要在客户端保存 OSS AccessKey。
- 不要把 `compat_no_sni` 描述成“更安全”或“推荐模式”；它只是兼容模式。
- 不要因为云服务连接失败阻断章枢本地写作功能。
- 不要禁止本地开发使用 `http://localhost`、`http://127.0.0.1` 或 `http://[::1]` 连接本地 cloud-server；生产 HTTPS 约束只针对远程云 API。
- 不要新增大型网络库，优先基于 `httpx`、`socket`、`ssl`、现有 AppConfig 实现。
- 如果发现当前直接实现过的 No-SNI 代码存在安全风险，Claude Code 应修正为可控 fallback，而不是直接删除导致校园网用户再次不可用。

# Verification Commands

## 桌面端后端

```powershell
cd F:\zhangshu\backend
pytest tests/test_cloud_api.py -q
pytest tests/test_cloud_backup_service.py -q
pytest tests/test_cloud_api_client_network_modes.py -q
pytest tests/test_cloud_network_diagnostics.py -q
python -c "from app.main import app; print('ok')"
```

## 前端

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run build
```

## 云服务端

```powershell
cd F:\zhangshu\cloud-server
pytest -q
python -c "from app.main import app; print(app.title)"
```

## 手动诊断建议

在普通网络、代理网络、校园/公司网络中至少各做一轮：

```powershell
Test-NetConnection api.emailbs.xin -Port 443
Invoke-RestMethod https://api.emailbs.xin/health
```

在章枢 UI 中：

1. 打开应用设置。
2. 进入章枢云账户。
3. 运行“云服务连接诊断”。
4. 切换 `auto`、`secure_direct`、`system_proxy`、`compat_no_sni`，确认提示和结果一致。
5. 登录或注册云账户。
6. 触发一次云端备份。
7. 如果 OSS 返回 403，确认 UI 提示能区分签名、CORS、endpoint 内外网问题。

# Acceptance Criteria

- 活跃交接文件只剩新的 `docs/ai-handoff/CODEX_PLAN.md`。
- 旧 `CODEX_PLAN.md` 和 `CLAUDE_EXECUTION_REPORT.md` 已归档到 `docs/ai-handoff/archive/2026-05-26-pre-network-resilience/`。
- 默认云连接模式为 `auto`。
- 普通 HTTPS 安全连接成功时，不使用 No-SNI，不关闭证书验证。
- 远程生产云 API 使用 HTTP 时会被阻止或明确标记为高风险；本地 `localhost/127.0.0.1/::1` HTTP 联调不受影响。
- 校园/公司网 SNI 过滤时，`auto` 能通过诊断或 fallback 找到 `compat_no_sni`，并给出用户可理解提示。
- 用户可以在设置中手动选择连接模式。
- 用户可以一键运行云连接诊断，诊断报告能区分 DNS、TCP、TLS/SNI、代理、云服务不可达、OSS endpoint 等问题。
- 登录/注册失败时，不再只显示泛化失败文案；网络类失败能引导用户诊断。
- 云备份上传的 OSS presigned URL 不会再返回阿里云内网 endpoint。
- 云服务端支持 public/internal OSS endpoint 分离。
- 所有新增诊断和日志不泄露 token、密码、API key、OSS AccessKey、完整签名 URL。
- 本地写作功能在云服务不可用时不受影响。
- 后端、前端、云服务端验证命令通过，或 Claude 执行报告说明无法运行的具体原因。

# Risks and Watchpoints

- 当前 `compat_no_sni` 使用 `CERT_NONE`，如果继续默认启用，会扩大中间人风险；必须收束为 fallback 或手动兼容模式。
- `trust_env=False` 可以绕过代理干扰，但会让必须走代理的用户无法连接；因此需要 `system_proxy` 模式。
- Windows GUI/Tauri 打包环境未必继承命令行的 `HTTP_PROXY/HTTPS_PROXY` 环境变量，`system_proxy` 模式不一定覆盖所有代理软件；UI 文案应提示用户可在代理软件中为 `api.emailbs.xin` 配置规则。
- 一些校园/公司网会封 IP 直连或拦截 Host 头，`compat_no_sni` 也可能失败；诊断应给出“更换网络或使用可信代理”的建议。
- No-SNI 兼容模式下证书验证不可用，不能用于传输高敏感操作以外的长期默认路径。
- 生产 HTTP 不能因为“方便调试”被放行；但如果实现过严，把 `localhost` 也禁掉，会直接破坏本地 cloud-server 联调。
- OSS presigned URL 的上传失败可能来自 Content-Type 不匹配、CORS、签名过期、endpoint 内外网、代理改写 header；错误分类要谨慎，不要误导用户。
- 云服务端如果使用双 endpoint，public/internal bucket 初始化要避免配置混淆。
- 日志中如打印 `response.url`，可能泄露 presigned URL 签名参数，必须避免。
- 诊断接口可能被频繁点击，应设置合理 timeout，避免 UI 长时间卡住。
- 如果新增 proxy URL 配置并允许账号密码，需要加密存储；V1 建议先不支持带认证的代理 URL。

# Review Checklist

- [ ] 是否已阅读并遵循 `docs/Cloud_Service_Connection_Troubleshooting.md` 的问题复盘？
- [ ] 是否把 No-SNI 从默认路径改为 fallback / 手动兼容模式？
- [ ] `secure_direct` 是否保留完整证书验证？
- [ ] `system_proxy` 是否允许系统代理参与请求？
- [ ] `auto` 策略是否有清晰顺序和错误分类？
- [ ] 网络诊断是否覆盖 DNS、TCP、HTTPS、代理、No-SNI、云 health？
- [ ] 诊断结果是否用户可读，而不是只抛技术异常？
- [ ] 远程生产云 API 使用 HTTP 时，是否被阻止或明确标记为高风险？
- [ ] 本地 `localhost/127.0.0.1/::1` HTTP 联调是否不受影响？
- [ ] 前端是否提供连接诊断入口？
- [ ] 登录/注册失败是否能区分账号错误和网络错误？
- [ ] 云备份 OSS 403 是否有更具体提示？
- [ ] 云服务端是否支持 OSS public/internal endpoint 分离？
- [ ] 预签名 URL 是否不会使用 `-internal.aliyuncs.com`？
- [ ] 是否没有记录 JWT、refresh token、密码、OSS AccessKey、完整 presigned URL？
- [ ] 是否没有修改无关业务模块？
- [ ] 是否没有破坏现有 12 个云 API 契约？
- [ ] 是否补充了后端、前端、云服务端相关测试？
- [ ] Claude 执行报告是否说明哪些网络场景已验证、哪些需要用户实际网络环境复验？
