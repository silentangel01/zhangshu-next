<!-- archived: 2026-05-25; task: cloud-backup-v1 -->

# Task Summary

本次任务是规划 **可选账号登录 + 阿里云 OSS 云端保存 V1**。

产品目标：

- 章枢继续保持本地优先，不强制用户登录。
- 未登录用户可以完整使用本地写作、资料管理、导出、备份等功能。
- 登录后才显示或启用“云端保存 / 云备份 / 云端恢复”能力。
- 云端 V1 先做“项目云备份”，不做实时云同步，不做多端冲突合并。
- 云存储首选阿里云 OSS，后续预留腾讯云 COS / S3 兼容适配层。

本计划只规划架构和执行方案。Codex 未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

当前项目是本地优先架构：

- `frontend/`: Vue 3 + TypeScript + Vite。
- `backend/`: FastAPI + SQLAlchemy + SQLite。
- Tauri 壳已存在于 `frontend/src-tauri/`，本地 sidecar 默认监听 `127.0.0.1:8765`。
- 当前没有账号、用户、登录、注册、远程云服务或云同步模块。

当前已有可复用能力：

- `backend/app/services/backup_service.py`
  - 已能把项目、章节、版本、人物、设定、伏笔、时间线、关系图、大纲及关联表打包为项目备份 zip。
  - 已支持封面资产写入备份 zip。
  - 已支持从项目备份 zip 恢复为新项目。
  - 当前备份格式为 `zhangshu.project_backup`，版本为 `1`。

- `backend/app/api/backups.py`
  - `POST /api/projects/{project_id}/backup`：导出项目备份 zip。
  - `POST /api/projects/backup/restore`：上传 zip 并恢复为新项目。

- `frontend/src/entities/project/backupApi.ts`
  - 已有下载项目备份和上传恢复的前端 API。
  - 当前下载通过 Blob URL + `a.download` 完成。

- `frontend/src/pages/imports/ProjectBackupPage.vue`
  - 已有“导出项目备份”和“从备份恢复项目”页面。
  - 这是新增“云端保存 / 云端恢复”的最自然入口。

- `backend/app/services/app_config_service.py`
- `backend/app/models/app_config.py`
- `backend/app/infrastructure/config_crypto.py`
  - 已有本地敏感配置加密存储机制。
  - 当前敏感 key 只包含 `dashscope_api_key`。
  - 后续可扩展存储云账号 refresh token，但不应存储阿里云 OSS AccessKey。

- `backend/app/models/project.py`
  - 当前 `Project` 没有云端字段。
  - 建议不要直接把大量云状态塞进 `projects` 表，优先新增独立云端关联表，保持本地项目模型干净。

云服务调研结论：

- 阿里云 OSS 适合作为章枢首选云存储。
  - OSS 官方文档说明其具备多层级数据保护能力，并支持同城冗余、跨区域复制、版本控制、定时备份等数据保护能力。
  - OSS 跨区域复制可把源 Bucket 对象自动、异步复制到另一个地域的目标 Bucket，适合高级灾备。
  - OSS 版本控制可以保留对象历史版本，用于应对误删除或覆盖。
  - 参考：
    - https://help.aliyun.com/zh/oss/user-guide/data-protection-overview
    - https://www.alibabacloud.com/help/zh/oss/user-guide/cross-region-replication-with-the-same-account
    - https://www.alibabacloud.com/zh/product/oss/pricing

# Architecture Decision

采用 **Local-first + Optional Cloud Backup** 架构。

核心决策：

1. 不强制登录
   - 未登录时，章枢完整本地可用。
   - 登录入口可以存在于项目列表页、应用设置、备份页面，但不能阻塞本地功能。
   - 未登录时只显示轻量提示，例如“登录后可启用云端保存”。

2. 云端 V1 只做云备份，不做实时同步
   - 云端保存 V1 的数据单位是项目备份包。
   - 复用 `BackupService` 生成的项目 zip。
   - 上传云端后记录备份元数据。
   - 恢复时默认恢复为新项目，不覆盖本地现有项目。
   - 不做章节级实时同步，不做冲突合并，不做多端协作。

3. 阿里云 OSS 是云存储主实现
   - Bucket 必须私有。
   - 推荐开启标准存储 + 同城冗余 ZRS。
   - 推荐开启版本控制。
   - 推荐配置生命周期规则，旧备份转低频或归档，控制成本。
   - 高级灾备再启用跨区域复制。

4. 桌面客户端不得保存 OSS AccessKey
   - 不允许在 Tauri 客户端、本地 SQLite 或前端代码中保存阿里云永久 AccessKey。
   - 章枢客户端只保存章枢账号 token。
   - OSS 凭证应只存在于远程 Zhangshu Cloud 服务端。
   - 如果需要客户端直传 OSS，应由云服务端签发短时上传凭证或预签名 URL。

5. 需要区分两个后端
   - 当前 `backend/` 是本地 FastAPI sidecar，负责本地数据库、本地项目和本地备份。
   - 真正的账号注册、登录、云备份元数据、OSS 上传授权，应属于远程 Zhangshu Cloud API。
   - 不要把本地 sidecar 直接当公网账号服务器使用。

6. 当前仓库可以先实现本地云入口和远程 API client 边界
   - 本地 sidecar 增加 `cloud` 模块，用于调用远程 Zhangshu Cloud API。
   - 远程云服务可以后续单独部署或独立仓库实现。
   - 如果短期没有远程云服务，Claude Code 应先实现清晰边界和 UI 状态，不要用本地假登录冒充真正云服务。

7. 预留多云适配
   - 首版固定阿里云 OSS。
   - 后端云服务内部使用 `CloudStorageProvider` 抽象。
   - 后续可增加 Tencent COS 或 S3-compatible Provider。
   - 本地客户端不感知具体云厂商，只感知“章枢云端保存”。

# Files to Create or Modify

本计划分为两个执行层面：当前本地客户端/sidecar 改造，以及未来远程 Zhangshu Cloud 服务。Claude Code 如果只在当前仓库执行，应优先完成“当前仓库范围”。

## 当前仓库范围

后端可新增：

- `backend/app/models/cloud_project_link.py`
- `backend/app/models/cloud_backup_record.py`
- `backend/app/repositories/cloud_project_link_repo.py`
- `backend/app/repositories/cloud_backup_record_repo.py`
- `backend/app/schemas/cloud.py`
- `backend/app/services/cloud_auth_service.py`
- `backend/app/services/cloud_backup_service.py`
- `backend/app/infrastructure/cloud_api_client.py`
- `backend/app/api/cloud.py`
- `backend/tests/test_cloud_backup_service.py`
- `backend/tests/test_cloud_api.py`

后端可修改：

- `backend/app/infrastructure/database.py`
  - 导入新模型。
  - 增加轻量 schema ensure 函数，或按项目后续迁移策略创建表。

- `backend/app/main.py`
  - include `cloud_router`。

- `backend/app/infrastructure/config_crypto.py`
  - 将云端 refresh token、access token 等 key 加入 `SENSITIVE_KEYS`。
  - 不加入 OSS AccessKey，因为客户端不应保存 OSS AccessKey。

- `backend/app/services/backup_service.py`
  - 如当前 `export_project_backup()` 只适合 StreamingResponse，可增加一个内部方法，例如 `build_project_backup_bytes(project_id)`，供云备份服务复用。
  - 不改变现有导出接口语义。

前端可新增：

- `frontend/src/entities/cloud/types.ts`
- `frontend/src/entities/cloud/api.ts`
- `frontend/src/features/cloud/CloudAccountDialog.vue`
- `frontend/src/features/cloud/CloudBackupPanel.vue`

前端可修改：

- `frontend/src/pages/projects/ProjectsPage.vue`
  - 增加轻量登录状态入口。
  - 未登录时显示“登录后启用云端保存”，不要阻塞新建/打开/编辑本地项目。

- `frontend/src/pages/imports/ProjectBackupPage.vue`
  - 在本地备份旁增加“云端保存”区域。
  - 未登录：显示说明和登录按钮。
  - 已登录：显示云备份按钮、最近云备份状态、云端备份列表入口。

- `frontend/src/features/app-config/AppSettingsDialog.vue`
  - 可增加“云端账号”区域，但不要混入 DashScope API Key 区域。

不应修改：

- 章节、人物、设定、知识库等业务模块的核心逻辑。
- 当前本地备份 zip 格式，除非为了添加 manifest 字段且保持兼容。
- 当前本地导出和恢复流程。
- Tauri 壳配置，除非云端 API base 需要桌面环境变量。
- 任何 `data/`、`logs/`、打包产物或本地配置文件。

## 远程 Zhangshu Cloud 服务范围

如果后续创建云服务，建议作为独立部署服务，不直接复用本地 sidecar。

建议模块：

- `cloud_backend/app/models/user.py`
- `cloud_backend/app/models/cloud_project.py`
- `cloud_backend/app/models/cloud_backup.py`
- `cloud_backend/app/api/auth.py`
- `cloud_backend/app/api/cloud_backups.py`
- `cloud_backend/app/services/auth_service.py`
- `cloud_backend/app/services/cloud_backup_service.py`
- `cloud_backend/app/infrastructure/storage/base.py`
- `cloud_backend/app/infrastructure/storage/aliyun_oss.py`

远程服务需要依赖：

- 密码哈希库，例如 `argon2-cffi` 或 `passlib[bcrypt]`。
- JWT 或 session token 库。
- 阿里云 OSS SDK，例如 `oss2`，仅用于云服务端。

# Implementation Steps for Claude Code

## Phase 0: 云存储方案确认

1. 确认产品策略
   - 云端保存不强制登录。
   - 云端 V1 是手动云备份，不是实时同步。
   - 恢复云备份默认恢复为新项目。

2. 确认阿里云 OSS 配置建议
   - Bucket 私有读写。
   - 推荐 Region：优先国内用户低延迟地域，例如华东 1、华东 2、华北 2。
   - 推荐存储类型：标准存储。
   - 推荐冗余：预算允许则 ZRS，同城冗余。
   - 开启版本控制。
   - 配置生命周期：
     - 保留最近 N 个标准备份。
     - 旧备份转低频或归档。
     - 超过保留期的非标记备份清理。
   - 高级灾备开启跨区域复制。

3. 明确安全原则
   - 桌面客户端不保存 OSS AccessKey。
   - 所有 OSS 操作由远程 Zhangshu Cloud 服务端完成，或由服务端签发短时预签名 URL。
   - 用户项目备份包上传前应计算 SHA-256。
   - 服务端保存 `checksum_sha256`、`size_bytes`、`object_key`、`created_at` 等元数据。

## Phase 1: 当前仓库内建立本地云状态边界

1. 新增本地云端关联模型
   - `CloudProjectLink`
     - `id`
     - `project_id`
     - `cloud_project_id`
     - `cloud_enabled`
     - `provider`
     - `last_backup_at`
     - `last_restore_at`
     - `status`
     - `last_error`
     - `created_at`
     - `updated_at`
   - `CloudBackupRecord`
     - `id`
     - `project_id`
     - `cloud_backup_id`
     - `object_key`
     - `filename`
     - `size_bytes`
     - `checksum_sha256`
     - `encryption_mode`
     - `status`
     - `error_message`
     - `created_at`
     - `uploaded_at`

2. 新增 Repository
   - `CloudProjectLinkRepository`
   - `CloudBackupRecordRepository`
   - Repository 只负责数据库读写，不写上传、登录或业务判断。

3. 扩展 `config_crypto.py`
   - 增加敏感 key：
     - `zhangshu_cloud_access_token`
     - `zhangshu_cloud_refresh_token`
     - `zhangshu_cloud_user_id`
   - 不增加任何 OSS AccessKey key。

4. 新增 `CloudApiClient`
   - 路径：`backend/app/infrastructure/cloud_api_client.py`
   - 职责：
     - 调用远程 Zhangshu Cloud API。
     - 附带 access token。
     - 处理 401 refresh。
     - 不直接操作 OSS。
   - 远程 API base 建议来自环境变量或 app config：
     - `ZHANGSHU_CLOUD_API_BASE_URL`
     - 默认可为空。为空时云功能显示为“未配置云服务”。

## Phase 2: 可选登录接口

1. 新增本地 cloud API
   - `GET /api/cloud/account/status`
     - 返回是否登录、用户昵称/邮箱、云服务是否可用。
   - `POST /api/cloud/auth/register`
     - body: `email`, `password`, `display_name?`
     - 调用远程云 API 注册。
     - 保存返回 token。
   - `POST /api/cloud/auth/login`
     - body: `email`, `password`
     - 调用远程云 API 登录。
     - 保存 token。
   - `POST /api/cloud/auth/logout`
     - 删除本地 token。
     - 不删除本地项目。

2. 前端新增云账号 UI
   - `CloudAccountDialog.vue`
     - Tab：登录 / 注册。
     - 登录成功后显示账号状态。
     - 退出登录只关闭云端能力，不影响本地项目。
   - 登录入口位置：
     - 项目列表页右上角。
     - 应用设置。
     - 备份页面云端保存区域。

3. UI 行为
   - 未登录：
     - 本地功能不受影响。
     - “云端保存”区域显示“登录后可启用云端保存”。
   - 已登录：
     - 显示“云端保存”按钮。
     - 显示最近一次云备份时间和状态。

## Phase 3: 云端保存 V1

1. 后端新增 `CloudBackupService`
   - 依赖：
     - `BackupService`
     - `CloudApiClient`
     - `CloudProjectLinkRepository`
     - `CloudBackupRecordRepository`
   - 主要流程：
     - 确认用户已登录。
     - 使用 `BackupService` 生成项目备份 zip bytes。
     - 计算 `size_bytes` 和 `checksum_sha256`。
     - 可选：对备份包做应用层加密。
     - 调用远程云 API 创建备份上传任务。
     - 上传备份包。
     - 调用远程云 API 确认上传完成。
     - 写入本地 `CloudBackupRecord`。

2. 后端新增 API
   - `POST /api/projects/{project_id}/cloud/enable`
     - 建立本地项目与云端项目映射。
   - `GET /api/projects/{project_id}/cloud/status`
     - 返回云端启用状态、最近备份、错误信息。
   - `POST /api/projects/{project_id}/cloud/backups`
     - 手动创建一次云备份。
   - `GET /api/projects/{project_id}/cloud/backups`
     - 列出云端备份摘要。
   - `POST /api/projects/{project_id}/cloud/backups/{cloud_backup_id}/restore`
     - 下载云备份并恢复为新项目。
     - 不覆盖当前项目。

3. 前端新增 `CloudBackupPanel.vue`
   - 放在 `ProjectBackupPage.vue`。
   - 未登录状态：
     - 显示说明和登录按钮。
   - 已登录未启用：
     - 显示“为本书启用云端保存”。
   - 已启用：
     - 显示“立即云端保存”。
     - 显示最近备份时间。
     - 显示备份列表。
     - 显示“从云端恢复为新项目”。

4. 文案边界
   - 使用“云端保存”或“云备份”。
   - 不使用“同步”作为 V1 主文案，避免用户误解为实时多端同步。
   - 恢复按钮必须明确“恢复为新项目，不覆盖当前本地项目”。

## Phase 4: 远程 Zhangshu Cloud API 设计

如果后续实现远程云服务，建议接口：

1. Auth
   - `POST /auth/register`
   - `POST /auth/login`
   - `POST /auth/refresh`
   - `POST /auth/logout`
   - `GET /auth/me`

2. Cloud project
   - `POST /cloud/projects`
   - `GET /cloud/projects`
   - `GET /cloud/projects/{cloud_project_id}`

3. Cloud backup
   - `POST /cloud/projects/{cloud_project_id}/backups/init`
     - 返回 `cloud_backup_id`、`upload_url` 或 `upload_session`。
   - `PUT upload_url`
     - 如果使用预签名 URL，由客户端直传 OSS。
   - `POST /cloud/backups/{cloud_backup_id}/complete`
     - 服务端校验 size/checksum 并记录完成。
   - `GET /cloud/projects/{cloud_project_id}/backups`
   - `GET /cloud/backups/{cloud_backup_id}/download`
     - 返回短时下载 URL 或由云服务端代理下载。
   - `DELETE /cloud/backups/{cloud_backup_id}`

4. OSS object key 规范
   - `users/{user_id}/projects/{cloud_project_id}/backups/{yyyy}/{mm}/{backup_id}.zsbak`
   - 不在 object key 中包含书名、作者名等敏感明文。

## Phase 5: 灾备与成本策略

阿里云 OSS 推荐配置：

1. 基础版
   - 标准存储 LRS。
   - Bucket 私有。
   - 开启版本控制。
   - 生命周期清理旧版本。

2. 稳妥版
   - 标准存储 ZRS。
   - Bucket 私有。
   - 开启版本控制。
   - 生命周期转低频 / 归档。

3. 高级灾备版
   - 标准存储 ZRS。
   - 跨区域复制到第二 Region。
   - 关键备份可标记为长期保留。

章枢默认建议从“稳妥版”开始，但产品早期可先用“基础版”控制成本。

# Constraints

- 不强制登录。
- 不做实时同步。
- 不做多人协作。
- 不做章节级云端合并。
- 不在桌面客户端保存 OSS AccessKey。
- 不把 OSS SDK 直接接进前端。
- 不把 AI/RAG 向量索引和云备份混在同一任务中。
- 不改变现有本地备份恢复语义。
- 不覆盖本地项目，云端恢复必须恢复为新项目。
- 不上传 `data/`、`logs/`、临时文件、密钥或本地配置。
- 不把云端保存入口做成强制登录弹窗。
- 不在未登录状态隐藏本地备份、导出、恢复等现有能力。

# Verification Commands

后端基础验证：

```powershell
cd backend
python -c "import app.main; print('backend import ok')"
pytest tests/test_backup_service.py
pytest tests/test_project_package_import_service.py
```

如新增云模块测试：

```powershell
cd backend
pytest tests/test_cloud_backup_service.py
pytest tests/test_cloud_api.py
```

前端验证：

```powershell
cd frontend
npm run type-check
npm run build
npm run test:unit -- --run
```

Tauri 壳基础验证：

```powershell
cd frontend
npm run tauri:dev
```

手动验证：

- 未登录状态：
  - 项目列表、本地写作、本地备份、本地恢复全部可用。
  - 不出现强制登录遮挡。
  - 云端保存入口显示为可选说明。
- 登录状态：
  - 项目备份页显示云端保存入口。
  - 能触发云备份流程。
  - 云备份失败时显示明确错误，不影响本地数据。
- 退出登录：
  - 本地项目仍可打开。
  - 云端保存按钮回到未登录状态。
- 云端恢复：
  - 恢复为新项目。
  - 不覆盖当前项目。
- 安全检查：
  - 前端代码没有 OSS AccessKey。
  - SQLite app_config 中没有 OSS AccessKey。
  - token 存储为加密值。

# Acceptance Criteria

- 未登录用户可以完整使用章枢本地功能。
- 登录入口存在，但不强制。
- 登录后才显示或启用云端保存能力。
- 云端 V1 是项目备份包上传，不是实时同步。
- 本地项目与云端项目通过独立表关联，不污染核心 `projects` 表。
- 云备份复用现有 `BackupService`，不复制一套备份打包逻辑。
- 桌面客户端不保存阿里云 OSS AccessKey。
- 云服务端或预签名机制负责 OSS 上传。
- 云备份对象 key 不包含书名、作者名等敏感明文。
- 云端恢复默认创建新项目。
- 所有 token 类配置通过本地加密存储。
- `npm run type-check`、`npm run build`、相关后端测试通过。
- 未修改无关业务模块。

# Risks and Watchpoints

- 如果没有远程 Zhangshu Cloud 服务，单靠本地 sidecar 不能实现真正账号注册和云端保存。
- 如果把 OSS AccessKey 存到客户端，会带来严重安全风险，必须避免。
- 云备份不是实时同步，文案必须避免让用户误解。
- 云端恢复如果覆盖本地项目，风险很高，V1 必须恢复为新项目。
- 项目备份包包含小说正文、人物秘密、设定、知识库等敏感内容，必须私有存储，后续应规划应用层加密。
- OSS 版本控制和跨区域复制会增加成本，需要生命周期策略。
- 如果使用预签名 URL，过期时间应短，并限制 object key、content length 和 checksum。
- 本地 token 加密依赖当前机器和用户，换机器后可能无法解密，这是可接受但需要 UI 提示重新登录。
- 远程云服务与本地 sidecar 的 API 边界必须清楚，避免把公网用户系统塞进本地 API。
- 未来做真正同步时需要冲突检测、版本向量或变更日志，本任务不解决。

# Review Checklist

- [ ] 是否保持未登录完整本地可用？
- [ ] 是否没有强制登录弹窗？
- [ ] 是否把 V1 明确限定为云备份，而不是实时同步？
- [ ] 是否复用 `BackupService`，没有复制备份打包逻辑？
- [ ] 是否没有在前端或本地 SQLite 保存 OSS AccessKey？
- [ ] token 是否通过 `config_crypto.py` 加密存储？
- [ ] 是否新增了独立云项目关联表，而不是污染核心 `projects` 表？
- [ ] 云端恢复是否恢复为新项目？
- [ ] 云备份对象 key 是否避免书名、作者名等敏感明文？
- [ ] 是否为 OSS 私有 Bucket、版本控制、生命周期、ZRS/CRR 写清楚部署要求？
- [ ] 是否没有修改章节、人物、设定、知识库等无关业务逻辑？
- [ ] 是否没有引入 AI/RAG/向量索引相关改动？
- [ ] 后端测试是否通过？
- [ ] 前端 type-check/build 是否通过？
- [ ] Claude 执行报告是否说明哪些部分需要远程云服务支持，哪些已在当前仓库完成？
