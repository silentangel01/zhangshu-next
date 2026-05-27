# Task Summary

本次任务是规划“章枢发布前总体验收清单（Release Candidate Acceptance Checklist）”。

目标是让 Claude Code 生成一份可实际执行、可签核、可记录结果的发布前验收文档，用于在正式发布或打包给用户前，从桌面端、本地后端、云服务端、Tauri 壳、数据安全、云备份、网络适配、隐私合规、成本防护、灾备恢复等维度做完整收口。

本任务只生成验收清单文档，不实现业务功能、不修复代码。Codex 未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

- 当前 `docs/ai-handoff/` 中没有活跃旧 `CODEX_PLAN.md`、`CLAUDE_EXECUTION_REPORT.md`、`CODEX_REVIEW.md`，可直接创建新计划。
- 当前仓库包含三个主要交付面：
  - `frontend/`：Vue 3 + TypeScript + Vite + Tauri v2 壳。
  - `backend/`：桌面端本地 FastAPI sidecar + SQLite。
  - `cloud-server/`：独立章枢云 API 服务端，FastAPI + PostgreSQL + OSS + Docker。
- 当前已有相关文档：
  - `docs/MVP_Phase1_Acceptance_Checklist.md`
  - `cloud-server/docs/PRODUCTION_CHECKLIST.md`
  - `cloud-server/docs/INCIDENT_RUNBOOK.md`
  - `cloud-server/docs/DISASTER_RECOVERY.md`
  - `docs/Cloud_Service_Connection_Troubleshooting.md`
  - `docs/ai-handoff/CLOUD_DEPLOYMENT_LOG.md`
- 当前前端脚本包括：
  - `npm run type-check`
  - `npm run build`
  - `npm run test:unit`
  - `npm run tauri:build`
  - `npm run tauri:build:backend`
- 当前云服务端已有生产基线能力：
  - `/health`、`/ready`
  - 生产配置校验
  - 结构化日志、请求 ID、安全响应头、审计事件
  - 数据库备份/恢复脚本
  - 云账户隐私、使用量和数据库级限流能力已由上一轮计划执行完成
- 当前发布前最大风险不再是单个功能缺失，而是：
  - 多模块联动没有从“用户视角”完整跑通。
  - Tauri 打包后的路径、端口、sidecar、云连接可能和开发环境不同。
  - 云服务、OSS、代理/校园网、HTTPS、隐私删除、配额等失败场景需要被验证。
  - Git / release 产物可能混入 `.env`、数据库、日志、安装包、临时文件。

# Architecture Decision

## 1. 验收文档是本轮唯一产物

Claude Code 本轮只应创建或更新验收清单文档，不应修改业务代码。建议新增：

`docs/release/RELEASE_CANDIDATE_ACCEPTANCE_CHECKLIST.md`

如果 `docs/release/` 不存在，Claude Code 可以创建该目录。

## 2. 清单必须可执行、可记录、可签核

验收清单不是泛泛说明，应包含：

- 检查项编号。
- 优先级：P0 / P1 / P2。
- 验收步骤。
- 预期结果。
- 实际结果记录栏。
- 状态：Pass / Fail / Blocked / N/A。
- 负责人或执行人。
- 备注和缺陷链接。

## 3. 发布阻断标准必须明确

清单中应明确：

- P0 Fail：阻断发布。
- P1 Fail：默认阻断，除非用户明确接受风险。
- P2 Fail：可记录为后续改进，不阻断发布。

## 4. 验收必须覆盖“本地优先 + 可选云端”

章枢的基本原则仍然是本地优先。验收必须同时证明：

- 不登录云账户时，本地写作和资料管理完整可用。
- 登录云账户后，云备份和云账户能力可用。
- 云服务不可用时，不影响本地写作。

# Files to Create or Modify

Claude Code 只允许创建或修改以下文档文件：

- 新增：`docs/release/RELEASE_CANDIDATE_ACCEPTANCE_CHECKLIST.md`

可选，如果 Claude Code 认为拆分更清楚，也可以新增：

- `docs/release/RELEASE_TEST_REPORT_TEMPLATE.md`

但不建议超过两个文件，避免文档碎片化。

不得修改：

- `frontend/` 业务代码。
- `backend/` 业务代码。
- `cloud-server/` 业务代码。
- 启动脚本、构建脚本、配置文件。
- 数据库迁移文件。

# Implementation Steps for Claude Code

## Phase 1: 创建文档骨架

在 `docs/release/RELEASE_CANDIDATE_ACCEPTANCE_CHECKLIST.md` 中创建以下结构：

1. Release Candidate 信息
2. 状态说明与发布阻断标准
3. 验收环境矩阵
4. 自动化命令验收
5. 桌面端本地功能验收
6. 云账户与云备份验收
7. 网络适配与失败场景验收
8. 隐私、安全与滥用防护验收
9. 云服务端生产验收
10. Tauri 打包与安装验收
11. 数据迁移、备份与恢复验收
12. Git / Release 产物安全检查
13. 最终签核表

## Phase 2: 文档开头写清执行规则

文档顶部必须包含：

- 本清单用于正式发布前验收。
- 所有 P0 项必须 Pass。
- P1 项原则上必须 Pass；若未通过，必须记录风险和用户确认。
- 不得使用真实用户隐私数据做破坏性测试。
- 删除云账号、恢复数据库、清空备份等高风险测试必须使用测试账号、测试项目、测试 Bucket 或本地测试环境。
- 验收中发现 bug 时，本轮只记录，不直接修复。

## Phase 3: Release Candidate 信息

添加表格：

| 字段 | 内容 |
|---|---|
| RC 编号 | 例如 RC-YYYYMMDD-01 |
| 执行日期 | |
| 执行人 | |
| Git branch | |
| Git commit | |
| 前端版本 | |
| 后端版本 | |
| cloud-server 版本 | |
| Tauri build 类型 | dev / release |
| 云 API 地址 | |
| OSS Bucket | 测试 / 生产 |
| 结论 | Ready / Not Ready |

## Phase 4: 验收环境矩阵

至少包含以下环境：

| 环境 | 必测 | 说明 |
|---|---|---|
| 本地 Web 开发环境 | 是 | frontend + backend，便于快速回归 |
| 本地 Tauri dev | 是 | `npm run tauri:dev` |
| Tauri release 包 | 是 | 最接近用户真实使用 |
| cloud-server 本地 Docker | 是 | PostgreSQL + cloud-api |
| 云服务器 staging/production | 是 | 如果可用 |
| 无云服务配置 | 是 | 验证本地优先 |
| 普通网络 | 是 | 正常 HTTPS |
| 系统代理网络 | 建议 | Clash / VPN / 公司代理 |
| 校园或公司网络 | 建议 | SNI / DPI 兼容 |
| 断网或云服务不可达 | 是 | 本地功能不受影响 |

## Phase 5: 自动化命令验收

为每条命令提供状态栏。

### 后端本地 sidecar

```powershell
cd F:\zhangshu\backend
pytest tests/ -q
python -c "from app.main import app; print('ok')"
```

验收重点：

- 全部测试通过。
- `app.main` 可导入。
- 不出现迁移、模型、路由注册错误。

### 前端

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run build
npm run test:unit
```

验收重点：

- TypeScript 无错误。
- Vite build 成功。
- 单元测试通过；如果项目暂未覆盖某些组件，应记录测试缺口。

### Tauri

```powershell
cd F:\zhangshu\frontend
npm run tauri:build:backend
npm run tauri:build
```

验收重点：

- sidecar exe 生成。
- release 包生成。
- 启动后能打开应用。
- 不依赖开发服务器。

### cloud-server

```powershell
cd F:\zhangshu\cloud-server
pytest -q
python -c "from app.main import app; print(app.title)"
docker compose config
```

如果 Docker 可用：

```powershell
docker compose up --build
```

另开终端：

```powershell
Invoke-RestMethod http://127.0.0.1:9000/health
Invoke-RestMethod http://127.0.0.1:9000/ready
```

## Phase 6: 桌面端本地核心功能验收

清单必须覆盖以下 P0 功能：

1. 启动应用
   - 能进入项目列表。
   - 本地数据库可创建。
   - `data/` 和 `logs/` 路径符合预期。
2. 项目管理
   - 新建项目。
   - 编辑书名、作者、封面、简介、标签。
   - 打开项目详情。
   - 删除或软删除项目行为符合预期。
3. 分卷与章节
   - 新建分卷。
   - 新建章节。
   - 拖拽排序大纲/章节时顺序保存。
   - 刷新后顺序不丢失。
4. 写作编辑器
   - 输入正文。
   - 手动保存。
   - 自动保存。
   - 版本快照。
   - 恢复历史版本。
   - 首行缩进、行距、段间距、对齐、自动排版。
5. 本地资料模块
   - 人物。
   - 设定树。
   - 伏笔。
   - 时间轴。
   - 关系图。
   - 知识库。
   - 违禁词/敏感词检查。
6. 导入导出
   - 旧 JSON 导入。
   - zip/txt/md 导入。
   - DOCX 正文导出。
   - 项目备份/恢复。

每项都要有：

- 操作步骤。
- 预期结果。
- 是否影响本地数据。
- Pass / Fail / Blocked。

## Phase 7: 云账户验收

清单必须覆盖：

1. 未配置云服务
   - UI 显示云服务未配置。
   - 本地写作不受影响。
2. 注册
   - 新邮箱注册成功。
   - 重复邮箱注册失败。
   - 弱密码失败。
   - 错误提示不泄露敏感信息。
3. 登录 / 刷新 / 退出
   - 正确密码登录。
   - 错误密码失败。
   - refresh token 可轮换。
   - 退出登录清理本地 token。
4. 修改密码
   - 输入旧密码和新密码。
   - 修改成功后旧 refresh token 失效。
5. 会话管理
   - 查看会话。
   - 退出全部设备。
6. 账号资料
   - 修改显示名。
   - 本地 UI 同步状态。
7. 隐私导出
   - 导出账号元数据。
   - 导出不包含 password_hash、refresh token、OSS AccessKey、完整 presigned URL。
8. 删除云账号
   - 发起删除请求需密码。
   - 二次确认文本错误时不能删除。
   - 确认后删除云端账号和云端备份。
   - 删除后本地作品仍存在。
   - 删除后云账户变为未登录。

## Phase 8: 云备份验收

必须覆盖：

1. 启用云端备份
   - 已登录后可为项目启用云端保存。
   - 云端项目创建成功。
2. 上传备份
   - 生成本地备份 zip。
   - 初始化 upload。
   - PUT 到 OSS presigned URL。
   - complete 成功。
   - 列表显示备份记录。
3. 恢复备份
   - 获取 download-url。
   - 下载 zip。
   - 恢复为新项目或按当前设计恢复。
   - 恢复后章节、资料数量正确。
4. 删除备份
   - 删除云端备份。
   - 列表不再显示。
   - OSS 对象删除或软删除状态符合设计。
5. 配额和成本
   - 显示已用容量。
   - 显示容量上限。
   - 超过单文件大小限制时提示明确。
   - 超过备份数量限制时提示明确。
   - 超过频率限制时返回 429 或对应提示。
6. 失败场景
   - OSS endpoint 配错为 internal 时能被识别。
   - OSS 403 时提示可能原因。
   - 上传中断后 stale record 可清理或标记失败。

## Phase 9: 网络适配验收

必须覆盖：

1. `secure_direct`
   - 普通 HTTPS 直连成功。
   - 证书验证开启。
2. `system_proxy`
   - 在系统代理环境中可连接。
   - 不泄露 token 到日志。
3. `compat_no_sni`
   - 只作为兼容模式。
   - UI 明确提示安全风险。
4. `auto`
   - 优先尝试安全直连。
   - 失败后按策略 fallback。
5. HTTP 策略
   - 远程 HTTP 被阻止或标记为高风险。
   - `localhost/127.0.0.1/::1` HTTP 本地联调不受影响。
6. 诊断面板
   - DNS、TCP、HTTPS、代理、No-SNI、health 诊断可显示。
   - 用户能理解建议，不只是看到异常堆栈。

## Phase 10: 隐私、安全、滥用防护验收

清单必须包含：

1. 密钥和敏感文件
   - `.env` 未提交。
   - JWT_SECRET_KEY 非默认。
   - OSS AccessKey 未进入桌面端。
   - 日志不含 token、密码、完整 presigned URL。
2. HTTPS
   - 生产云 API 使用 HTTPS。
   - HTTP 自动跳转或被禁止。
3. CORS
   - 生产不使用 `*`。
   - 桌面端实际 origin 可访问。
4. 安全响应头
   - `X-Content-Type-Options`
   - `X-Frame-Options`
   - `Referrer-Policy`
   - 认证响应不缓存。
5. 限流
   - 登录限流跨进程生效。
   - 注册限流生效。
   - 备份 init 限流生效。
6. 审计
   - 登录成功/失败。
   - 注册。
   - token refresh。
   - 备份 init/complete/delete。
   - 删除账号。
7. 用户数据权利
   - 导出。
   - 删除。
   - 退出全部设备。

## Phase 11: 云服务端生产验收

覆盖：

1. Docker
   - `docker compose config` 通过。
   - `cloud-api` 只绑定本机端口。
   - PostgreSQL 只绑定本机端口。
   - 容器自动重启策略存在。
2. Nginx / SSL
   - 443 可访问。
   - 证书有效。
   - 证书续期可检查。
3. Health / Ready
   - `/health` 正常。
   - `/ready` 检查数据库。
4. 备份和恢复
   - `backup-db.sh` 可执行。
   - 生成 `.dump` 和 SHA256。
   - `restore-db.sh` 有显式确认。
   - 至少在测试环境演练一次。
5. Runbook
   - 事故手册覆盖登录失败、OSS 403、数据库故障、磁盘满、证书过期。

## Phase 12: Tauri 打包和安装验收

覆盖：

1. 构建产物
   - sidecar exe 存在。
   - Tauri installer / executable 存在。
   - 启动不依赖 Vite dev server。
2. 首次安装
   - 可打开项目列表。
   - 本地数据目录创建正确。
   - 日志目录创建正确。
3. 升级安装
   - 旧数据不丢失。
   - 数据库自动兼容或迁移。
4. 卸载 / 重装
   - 明确本地数据是否保留。
5. 云功能
   - 打包后默认云 API 地址正确。
   - 网络诊断可用。
   - 云登录/备份可用。

## Phase 13: Git 和 Release 产物安全检查

必须包含命令：

```powershell
cd F:\zhangshu
git status --short
git diff --stat
```

敏感内容扫描：

```powershell
rg -n "OSS_ACCESS_KEY_SECRET|OSS_ACCESS_KEY_ID|JWT_SECRET_KEY|dashscope_api_key|cloud_access_token|cloud_refresh_token|BEGIN PRIVATE KEY|sk-|LTAI" -g "!node_modules" -g "!frontend/dist" -g "!frontend/src-tauri/target" -g "!*.lock"
```

文件风险检查：

```powershell
Get-ChildItem -Recurse -Force -Include ".env","*.db","*.sqlite","*.sqlite3","python-*.exe","*.log" | Select-Object FullName
```

验收文档必须写清：

- 如果发现 `.env`、数据库、日志、安装包、临时诊断脚本进入 git diff，P0 Fail。
- 不得提交 `data/`、`logs/`、`release/`、本地数据库、云服务真实密钥。

## Phase 14: 最终签核

文档最后加入签核表：

| 角色 | 结论 | 签名/记录 | 日期 | 备注 |
|---|---|---|---|---|
| 产品验收 | Ready / Not Ready | | | |
| 本地功能验收 | Ready / Not Ready | | | |
| 云功能验收 | Ready / Not Ready | | | |
| 安全隐私验收 | Ready / Not Ready | | | |
| 发布负责人 | Ready / Not Ready | | | |

并明确最终结论：

- Ready for RC
- Ready with Known Issues
- Not Ready

# Constraints

- 本轮只创建发布前验收清单文档，不修改业务代码。
- 不运行破坏性生产操作。
- 删除账号、恢复数据库、OSS 删除等危险验收必须使用测试账号和测试环境。
- 不把真实密钥写入验收文档。
- 不要求所有建议都自动化；手动场景可以记录为 Manual。
- 不把历史 archive 文档作为 Claude 必读执行前提，除非需要回溯。
- 不能把本地开发失败直接等同于发布失败；必须区分环境问题、测试阻断和真实缺陷。

# Verification Commands

Claude Code 完成文档后执行：

```powershell
Test-Path docs/release/RELEASE_CANDIDATE_ACCEPTANCE_CHECKLIST.md
```

检查章节完整性：

```powershell
Select-String -Path docs/release/RELEASE_CANDIDATE_ACCEPTANCE_CHECKLIST.md -Pattern "Release Candidate 信息|发布阻断标准|验收环境矩阵|自动化命令验收|桌面端本地功能验收|云账户验收|云备份验收|网络适配验收|隐私、安全、滥用防护验收|Tauri 打包|Git|最终签核"
```

检查是否误改业务代码：

```powershell
git status --short -- docs/release docs/ai-handoff
```

如 Claude Code 执行了额外文件变更，必须在执行报告说明原因。

# Acceptance Criteria

- 新增 `docs/release/RELEASE_CANDIDATE_ACCEPTANCE_CHECKLIST.md`。
- 清单足够详细，可以由人逐项执行，而不是概念性建议。
- 清单包含 P0/P1/P2 优先级和 Pass/Fail/Blocked/N/A 状态。
- 清单包含发布阻断标准。
- 清单覆盖本地写作核心流程。
- 清单覆盖云账户、隐私、云备份、配额、滥用防护。
- 清单覆盖网络适配和失败场景。
- 清单覆盖 Tauri 打包后真实用户路径。
- 清单覆盖 cloud-server 生产部署、备份恢复、runbook。
- 清单覆盖 git 和 release 产物安全检查。
- 清单包含最终签核表。
- 除该文档外不修改业务代码。

# Risks and Watchpoints

- 清单过粗会导致“看起来验收了，实际上没跑通”。必须写出操作步骤和预期结果。
- 清单过度自动化会忽略 Tauri 打包、云网络、真实 OSS 等人工场景。必须保留手动验收矩阵。
- 删除账号和数据库恢复是危险项，必须强调测试环境。
- 真实云服务和 OSS 测试会产生费用，必须使用测试 Bucket 或小文件。
- 网络适配无法在单一机器完全覆盖，需要记录未覆盖环境。
- 如果当前 README 仍有旧路径或旧端口，清单中应要求记录文档不一致问题。

# Review Checklist

- [ ] 是否只创建验收清单文档？
- [ ] 是否没有修改业务代码？
- [ ] 是否包含 Release Candidate 信息表？
- [ ] 是否包含发布阻断标准？
- [ ] 是否覆盖自动化命令？
- [ ] 是否覆盖桌面端本地写作核心流程？
- [ ] 是否覆盖所有主要资料模块？
- [ ] 是否覆盖云账户和隐私流程？
- [ ] 是否覆盖云备份端到端？
- [ ] 是否覆盖网络适配场景？
- [ ] 是否覆盖生产安全和滥用防护？
- [ ] 是否覆盖 cloud-server 部署、备份和恢复？
- [ ] 是否覆盖 Tauri 打包、安装、升级？
- [ ] 是否覆盖 Git 和 release 产物安全扫描？
- [ ] 是否有最终签核表？
- [ ] Claude 执行报告是否列明新增文档路径和未执行实际验收的说明？
