# 章枢自动更新失效排查复盘（2026-06-02）

本文档整理 2026-06-02 前后章枢 Windows 安装版自动更新失效的发现、判断、处理与当前结论。信息来源包括本轮对话、用户手动执行命令输出，以及最近归档的 Claude/Codex 交接文件：

- `docs/ai-handoff/archive/2026-06-02-desktop-updater-mvp-executed/`
- `docs/ai-handoff/archive/2026-06-02-server-static-update-endpoints/`
- `docs/ai-handoff/archive/2026-06-02-updater-url-inno-build/`
- `docs/ai-handoff/archive/2026-06-02-e2e-updater-081-uploaded/`
- `docs/ai-handoff/CODEX_PLAN.md`
- `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`

## 一、背景

章枢桌面端自动更新采用“完整安装包覆盖更新”方案：

1. 桌面端从 HTTPS release manifest 获取最新版本信息。
2. manifest 声明版本、安装包 URL、SHA256、大小和更新说明。
3. Rust/Tauri 端下载安装包并校验 SHA256。
4. 校验成功后由独立 `zhangshu-updater.exe` 启动 Inno Setup 安装器。

该方案不做差分补丁，不直接热替换运行中的程序文件。

最初的自动更新 MVP 已由 Claude 实现，归档于 `2026-06-02-desktop-updater-mvp-executed`。当时已完成版本收束、manifest 生成、Rust 端更新检查/下载/SHA256 校验、前端更新 UI、独立 updater helper、Inno Setup 打包集成。

## 二、问题时间线

### 1. 自动更新 MVP 实现后仍缺真实更新源

归档文件：`2026-06-02-desktop-updater-mvp-executed`

当时执行结果：

- `frontend/src-tauri/src/updater.rs` 新增 updater 核心模块。
- `frontend/src/entities/update/api.ts` 新增前端调用封装。
- `frontend/src-tauri/src/bin/zhangshu-updater.rs` 新增独立更新 helper。
- `scripts/generate_update_manifest.ps1` 和 `scripts/smoke_updater_manifest.ps1` 用于生成和验证 manifest。
- Inno 安装包成功构建。

遗留问题：

- 默认 manifest URL 仍是占位域名 `release.zhangshu.app`。
- 真实更新服务器、真实 HTTPS manifest 与下载入口尚未完全接入。
- 端到端安装更新流程需要真实服务器验证。

判断摘要：

当时自动更新能力“代码闭环”已经初步具备，但“发布基础设施闭环”还没有完成。也就是说，程序会检查更新，但检查的地址还不是最终生产更新源。

处理结果：

进入下一阶段：配置 `zhangshu.xin` 相关更新域名。

### 2. 配置 `updates.zhangshu.xin` 与 `downloads.zhangshu.xin`

归档文件：`2026-06-02-server-static-update-endpoints`

目标：

- `https://updates.zhangshu.xin/zhangshu/stable/windows-x64/latest.json`
- `https://downloads.zhangshu.xin/zhangshu/releases/test.txt`

Claude 执行结果：

- 在服务器 `121.40.247.143` 上新增 Nginx 静态站点配置。
- 创建测试 manifest 与测试下载文件。
- 申请并部署 `updates.zhangshu.xin` / `downloads.zhangshu.xin` HTTPS 证书。
- 服务器端验证 HTTPS 返回 200。
- 未修改既有云服务 `api.emailbs.xin`。

已知问题：

- `certbot renew --dry-run` 曾超时。
- `zhangshu.xin` 指向中国内地服务器，存在备案风险。

判断摘要：

服务器静态入口在当时看似可用，但备案风险已经埋下。该风险后来被证实会影响 HTTP-01 证书验证和未备案域名 HTTP 访问。

处理结果：

进入下一阶段：把客户端 URL 从占位域名切换到 `zhangshu.xin`。

### 3. updater URL 切换到新域名并打包 Inno 安装包

归档文件：`2026-06-02-updater-url-inno-build`

Claude 修改：

- `frontend/src/entities/update/api.ts`
  - 主更新源改为 `https://updates.zhangshu.xin/zhangshu/stable/windows-x64/latest.json`
  - 备用更新源设为 `https://updates.emailbs.xin/zhangshu/stable/windows-x64/latest.json`
  - 新增 `checkForUpdateWithFallback()`
- `frontend/src/pages/account/AppVersionPanel.vue`
  - 使用 fallback 检查逻辑
  - 记录 `activeManifestUrl`，下载阶段使用实际命中的 manifest URL
- `docs/release/updater.md`
  - 更新 manifest URL、fallback 说明和发布流程

当时生成：

- `release/章枢_Setup_0.8.0_windows_x64.exe`
- `release/latest.windows-x64.json`

已知问题：

- 服务器上的 `latest.json` 当时仍是测试 manifest。
- 安装包和 manifest 只是本地构建产物，尚未真正上传为生产测试包。

判断摘要：

客户端已经指向新更新源，但服务器端还没有放上与真实安装包匹配的 release manifest。因此下一步需要构建更高版本并上传，做真实更新链路测试。

处理结果：

进入下一阶段：构建并上传 `0.8.1`。

### 4. 构建并上传 `0.8.1` 后，用户测试仍失败

归档文件：`2026-06-02-e2e-updater-081-uploaded`

Claude 执行：

- 版本提升到 `0.8.1`：
  - `frontend/package.json`
  - `frontend/src-tauri/tauri.conf.json`
  - `frontend/src-tauri/Cargo.toml`
- 构建 Inno 安装包。
- 上传安装包和 manifest 到服务器：
  - `/var/www/zhangshu-downloads/zhangshu/releases/0.8.1/章枢_Setup_0.8.1_windows_x64.exe`
  - `/var/www/zhangshu-updates/zhangshu/stable/windows-x64/latest.json`
- 服务器端验证 manifest 与安装包 HTTPS 返回 200。

当时已知问题：

- `updates.emailbs.xin` 证书不覆盖该域名。
- 本地网络到服务器 HTTPS 可能存在 TLS 握手失败。
- 阶段 B 仍需用户手动安装测试。

用户随后反馈：

```text
检查更新失败
主用与备用更新源均不可用，请检查网络连接后重试。
```

同时用户确认：

- 浏览器直接访问 `latest.json` 正常。
- 浏览器直接访问安装包 URL 可自动下载 exe。

判断摘要：

浏览器可访问说明 DNS 和服务器静态文件不是完全不可用。但安装版失败说明 Tauri/Rust 更新器的网络栈、权限或代理处理仍存在问题。此时不能简单判断为“服务器挂了”。

处理结果：

进入下一轮：排查 Tauri ACL、代理与 Rust 网络请求。

### 5. 安装版出现 Tauri ACL 报错

用户提供的新报错：

```text
检查更新失败
主用与备用更新源均不可用。
源1: Command check_update not allowed by ACL；
源2: Command check_update not allowed by ACL
```

判断摘要：

这不是服务器问题，也不是网络问题，而是 Tauri v2 capability 权限配置问题。安装版主窗口实际加载的是 `http://127.0.0.1:8765`，如果 capability 没有允许该 remote origin 调用 `check_update`，Tauri 会直接拒绝命令。

处理：

- 修改 `frontend/src-tauri/capabilities/default.json`
  - 增加 remote URL：
    - `http://localhost:5180`
    - `http://127.0.0.1:5180`
    - `http://127.0.0.1:8765`
  - 增加权限：
    - `allow-check-update`
    - `allow-download-update`
    - `allow-install-update`
- 新增 `frontend/src-tauri/permissions/update.toml`
  - 显式允许：
    - `check_update`
    - `download_update`
    - `install_update`

处理结果：

ACL 报错被消除。后续安装版报错进入真实网络请求阶段，说明 Tauri command 权限问题已解决。

### 6. ACL 修复后出现真实网络错误

用户提供的新报错：

```text
检查更新失败
主用与备用更新源均不可用。
源1: 无法获取有效更新清单
（系统代理(127.0.0.1:7897): 连接失败: error sending request for url (...);
直连: 连接失败: error sending request for url (...);
默认网络: 连接失败: error sending request for url (...)）；
源2: 无法获取有效更新清单
（系统代理(127.0.0.1:7897): 连接失败: error sending request for url (...);
直连: 连接失败: error sending request for url (...);
默认网络: 连接失败: error sending request for url (...)）
```

判断摘要：

这说明：

- Tauri ACL 已经通过。
- Rust updater 已经实际发起网络请求。
- 更新器已经尝试三种策略：
  - 系统代理
  - 直连
  - 默认网络
- 三种策略都失败，问题不再是“命令没权限”，而是 HTTPS 网络栈、代理链路或服务器兼容性问题。

本地诊断结果：

- Node `fetch` 可以访问 `https://updates.zhangshu.xin/...latest.json`。
- TCP 到 `updates.zhangshu.xin:443` 成功。
- Rust `reqwest` 探针失败。
- PowerShell `Invoke-WebRequest` 失败。
- curl/SChannel 失败。
- `updates.emailbs.xin` 在 Node 下报 `ERR_TLS_CERT_ALTNAME_INVALID`，证书不覆盖备用域名。

判断依据：

不同客户端表现不同：

- 浏览器/Node 可访问。
- Rust/PowerShell/curl 失败。

这说明服务器并非完全不可用，而是源站 HTTPS、代理路径、证书、备案拦截或客户端 TLS 栈之间存在兼容问题。

处理：

- Rust updater 增加代理兼容策略：
  - 系统代理优先。
  - 可信更新域名允许直连兜底。
  - 最后尝试默认网络。
- `frontend/src/entities/update/api.ts` 的 fallback 错误信息增加 `源1` / `源2` 细节。
- `frontend/src-tauri/src/updater.rs` 增加底层错误链摘要，让后续错误能显示更接近真实原因，而不是只有 `error sending request`。

验证：

用户执行：

```powershell
cd F:\zhangshu\frontend\src-tauri
cargo check --locked
```

结果：

```text
Finished `dev` profile [unoptimized + debuginfo] target(s) in 1.77s
```

处理结果：

代码侧可编译，ACL 已修，错误诊断能力增强。但安装版的更新源访问问题仍未完全解决，焦点转向服务器/域名/备案/CDN。

### 7. 尝试修复 `updates.emailbs.xin` 备用源证书失败

用户执行：

```powershell
ssh root@121.40.247.143 "certbot --nginx --expand -d updates.zhangshu.xin -d downloads.zhangshu.xin -d updates.emailbs.xin --non-interactive --agree-tos --redirect && nginx -t && systemctl reload nginx"
```

返回：

```text
Domain: updates.emailbs.xin
Type: unauthorized
Detail: 121.40.247.143: Invalid response from http://updates.emailbs.xin/.well-known/acme-challenge/...: 403
```

初步判断：

Let's Encrypt HTTP-01 验证到达了 `121.40.247.143`，但 ACME challenge 路径返回 403。此时先怀疑是 Nginx 没有放行 `/.well-known/acme-challenge/`。

处理尝试：

- 创建 `/var/www/letsencrypt/.well-known/acme-challenge/ping`
- 写入临时 Nginx ACME server block
- 处理 PowerShell 对 `$uri` 的转义问题

随后用户验证：

```powershell
curl.exe --noproxy "*" -i http://updates.emailbs.xin/.well-known/acme-challenge/ping
```

返回：

```text
HTTP/1.1 403 Forbidden
Server: Beaver
<title>Non-compliance ICP Filing</title>
```

判断摘要：

`Server: Beaver` 和 `Non-compliance ICP Filing` 说明请求在到达 Nginx 前已被阿里云备案合规层拦截。这不是 Nginx location 没写对，而是未备案域名指向中国内地阿里云服务器被阻断。

处理结果：

`updates.emailbs.xin` 无法通过 HTTP-01 申请证书；即使 DNS 指向正确，也不能作为可靠备用更新源。

### 8. 验证 `updates.zhangshu.xin` HTTP 也被备案拦截

用户提出疑问：为什么测 `emailbs.xin` 而不是 `zhangshu.xin`。

随后用户执行：

```powershell
curl.exe --noproxy "*" -i http://updates.zhangshu.xin/.well-known/acme-challenge/ping
```

返回：

```text
HTTP/1.1 403 Forbidden
Server: Beaver
<title>Non-compliance ICP Filing</title>
```

判断摘要：

这确认了 `zhangshu.xin` 当前也触发阿里云未备案拦截。也就是说，只要该域名指向中国内地阿里云服务器，HTTP 访问就可能被 Beaver 拦截。它不仅影响 ACME HTTP-01 验证，也说明当前更新域名的长期生产可用性存在备案前置问题。

处理结果：

自动更新问题的根因从“代码缺陷”进一步收束为：

1. 客户端代码层：
   - Tauri ACL 已修。
   - 代理/直连 fallback 已实现。
   - 错误诊断已增强。
2. 备用源：
   - `updates.emailbs.xin` 证书不匹配。
   - 且未备案拦截导致 HTTP-01 证书补签失败。
3. 主源：
   - `updates.zhangshu.xin` HTTPS 在浏览器/Node 可访问。
   - 但 HTTP 被未备案拦截。
   - Rust/PowerShell/curl 等客户端仍存在 HTTPS 访问失败，生产可用性不能只以浏览器访问为准。
4. 基础设施：
   - 当前域名备案状态不足以支撑阿里云中国内地服务器上的正式更新服务。

## 三、关键错误与处理结果汇总

| 阶段 | 用户提供的错误或现象 | 判断 | 处理 | 当前结果 |
|---|---|---|---|---|
| 初始安装版更新失败 | 主用与备用更新源均不可用 | 可能是 URL、服务器、ACL 或网络栈问题 | 先读计划、报告、代码和 manifest 配置 | 进入分层排查 |
| 浏览器可访问 manifest/安装包 | 浏览器打开 URL 正常 | 服务器不是完全不可用 | 对比安装版与浏览器差异 | 焦点转向 Tauri/Rust |
| ACL 报错 | `Command check_update not allowed by ACL` | Tauri capability 未授权 remote origin 调命令 | 增加 capability remote URLs 与 update permissions | ACL 问题已解决 |
| 真实网络错误 | 系统代理、直连、默认网络均 `error sending request` | Rust updater 已进入网络层，但 HTTPS/代理链路失败 | 增加代理优先、直连兜底、错误细节 | 代码可编译，但链路仍需基础设施修复 |
| 备用源证书错误 | `updates.emailbs.xin` 证书不覆盖 | fallback 不是有效备用源 | 尝试 certbot expand | 被 HTTP-01 403 拦截 |
| ACME ping 403 | `Server: Beaver`, `Non-compliance ICP Filing` | 阿里云未备案拦截，非 Nginx 配置问题 | 测 `emailbs` 和 `zhangshu` 两个域名 | 备案成为生产前置条件 |
| `cargo check` | 本地 cargo check 通过 | 代码侧无明显编译错误 | 记录验证结果 | 可进入下一轮打包，但不建议绕过备案上线 |

## 四、当前结论

自动更新失效不是单一问题，而是多层问题叠加：

1. **Tauri ACL 问题已确认并修复**
   - 报错 `Command check_update not allowed by ACL` 已定位为 capability 配置缺失。
   - 已通过 `default.json` 和 `permissions/update.toml` 修复。

2. **Rust updater 网络策略已增强**
   - 已支持系统代理、直连和默认网络多策略。
   - 已限制直连兜底只对可信更新域名生效。
   - 已增强错误信息，便于下一次安装版定位 TLS/代理底层原因。

3. **备用源 `updates.emailbs.xin` 当前不可作为可靠 fallback**
   - 证书不匹配。
   - HTTP-01 证书验证被阿里云 ICP 合规层拦截。
   - 在备案或 DNS-01 证书方案完成前，不应依赖它做更新兜底。

4. **主源 `updates.zhangshu.xin` 仍受备案问题影响**
   - HTTP 访问被 `Non-compliance ICP Filing` 拦截。
   - HTTPS 在浏览器/Node 下可访问，但 Rust/PowerShell/curl 路径仍失败。
   - 因此不能把“浏览器可访问”视为生产级更新链路已稳定。

5. **生产路线需要先完成备案或换可用更新源**
   - 如果继续使用阿里云中国内地轻量服务器，`zhangshu.xin` 备案是长期正解。
   - 若想立即测试 0.8.1 -> 0.8.2 更新链路，应使用临时可用 HTTPS 源，例如非内地服务器、对象存储默认域名、GitHub Releases、Cloudflare/R2 等。

## 五、建议的下一步

### A. 生产路线

1. 以 `zhangshu.xin` 作为章枢正式主域名，在当前轻量应用服务器备案流程中填写：
   - 网站名称：章枢 / 章枢写作助手
   - 域名：`zhangshu.xin`
   - 网站首页 URL：`www.zhangshu.xin`
   - 网站内容：写作辅助工具、账号服务、软件下载与更新服务
2. 备案完成后统一规划：
   - `www.zhangshu.xin`：官网/下载页/隐私政策
   - `api.zhangshu.xin`：章枢云账号 API
   - `updates.zhangshu.xin`：更新清单
   - `downloads.zhangshu.xin`：安装包下载
3. 备案完成后重新验证：
   - HTTP ACME challenge 不再被 Beaver 拦截。
   - HTTPS manifest 和 installer 对浏览器、Node、Rust、PowerShell、curl 均可访问。
4. 再考虑接入 CDN，提升更新包下载稳定性。

### B. 临时测试路线

如果不想等备案完成，可先临时换一个不受阿里云备案拦截的 HTTPS 更新源：

- GitHub Releases
- Cloudflare R2
- 海外服务器
- 可公开访问的对象存储默认域名

临时更新源只用于验证：

- `0.8.1` 能检查到 `0.8.2`
- manifest 拉取成功
- 安装包下载成功
- SHA256 校验成功
- updater helper 能拉起 Inno 安装器
- 覆盖安装后版本更新且用户数据不丢失

### C. 代码收束建议

1. 在 `updates.emailbs.xin` 证书和备案问题解决前，考虑临时移除该 fallback，避免错误信息误导。
2. 保留 Rust updater 的多策略网络请求和错误链输出。
3. 下一次打包前执行：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run build
npm run test:unit
```

```powershell
cd F:\zhangshu\frontend\src-tauri
cargo check --locked
cargo build --release
```

4. 只有当更新源对非浏览器客户端也稳定后，再推进 `0.8.2` 真实更新测试。

## 六、收束状态

截至本文档记录时：

- 自动更新代码已从 MVP 进入可诊断、可代理兜底的状态。
- 安装版 ACL 问题已定位并处理。
- `0.8.1` 构建与上传流程已由 Claude 执行过。
- 服务器 manifest/安装包路径已形成规范。
- 当前阻断项主要是域名备案与更新源基础设施稳定性，而不是单纯的前端按钮或 updater 命令缺失。

最终建议：

先不要把 `0.8.2` 测试建立在当前阿里云未备案更新域名上。应先完成备案，或临时切换到一个确定能被 Rust/PowerShell/curl 访问的 HTTPS 更新源，再进行真实自动更新验证。
