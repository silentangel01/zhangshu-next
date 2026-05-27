---
archived_at: 2026-05-25
archive_reason: Cloud Backup V1 local client boundary completed; planning real auth/register cloud service
date: 2026-05-25
task: Cloud Backup V1 — 可选账户登录 + 阿里云 OSS 云端备份
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary
实现可选的章枢云账户登录和云端备份功能 V1。本地优先架构不变，云功能为可选附加，未配置云服务时优雅降级。

## Files Changed
- 新增：`backend/app/models/cloud_project_link.py` — 本地项目与云端项目的关联表
- 新增：`backend/app/models/cloud_backup_record.py` — 云端备份上传记录表
- 新增：`backend/app/repositories/cloud_project_link_repo.py` — CloudProjectLink 数据访问层
- 新增：`backend/app/repositories/cloud_backup_record_repo.py` — CloudBackupRecord 数据访问层
- 新增：`backend/app/infrastructure/cloud_api_client.py` — 远程章枢云 API HTTP 客户端
- 新增：`backend/app/schemas/cloud.py` — 云端认证和备份的 Pydantic schema
- 新增：`backend/app/services/cloud_auth_service.py` — 云账户认证服务层
- 新增：`backend/app/services/cloud_backup_service.py` — 云端备份业务逻辑服务层
- 新增：`backend/app/api/cloud.py` — 9 个云端 API 路由端点
- 新增：`backend/tests/test_cloud_backup_service.py` — CloudBackupService 单元测试（8 用例）
- 新增：`backend/tests/test_cloud_api.py` — Cloud API 端点集成测试（9 用例）
- 新增：`frontend/src/entities/cloud/types.ts` — 云端相关 TypeScript 类型定义
- 新增：`frontend/src/entities/cloud/api.ts` — 云端相关 API 请求封装
- 新增：`frontend/src/features/cloud/CloudAccountDialog.vue` — 云账户登录/注册/退出弹窗
- 新增：`frontend/src/features/cloud/CloudBackupPanel.vue` — 项目云端备份操作面板
- 修改：`backend/app/infrastructure/config_crypto.py` — SENSITIVE_KEYS 新增 4 个云端 token key
- 修改：`backend/app/infrastructure/database.py` — init_database() 注册 2 个新模型
- 修改：`backend/app/services/backup_service.py` — 新增 build_project_backup_bytes() 方法
- 修改：`backend/app/main.py` — 注册 cloud_router 和 projects_cloud_router
- 修改：`frontend/src/pages/projects/ProjectsPage.vue` — 添加云账户按钮和 CloudAccountDialog
- 修改：`frontend/src/pages/imports/ProjectBackupPage.vue` — 添加 CloudBackupPanel 组件
- 修改：`frontend/src/features/app-config/AppSettingsDialog.vue` — 添加章枢云账户状态 section

## Implementation Notes
1. **CloudApiNotConfiguredError** 在所有 CloudApiClient 方法开头调用 `_ensure_configured()`，未配置 base URL 时立即抛错
2. **Token 加密** 复用现有 config_crypto.py Fernet 机制，`SENSITIVE_KEYS` 新增 `cloud_access_token`、`cloud_refresh_token`、`cloud_user_id`、`cloud_user_email`
3. **CloudAuthService** 通过 AppConfigService 存取 token，加密自动透明
4. **CloudBackupService.trigger_backup** 创建 pending 记录 → 生成 zip → SHA256 → 上传 → 更新为 success/failed，失败不影响本地数据
5. **前端三态 UI**: 未登录 → 提示登录; 已登录未启用 → 启用按钮; 已启用 → 备份/恢复操作
6. **API 测试** 使用 FastAPI dependency_overrides 注入 mock service，避免依赖真实数据库
7. 新增 15 个文件 + 修改 7 个文件，零业务模块变更（chapters/characters/settings/knowledge 未触碰）

## Deviations from Codex Plan
无

## Verification Commands Run
- `python -c "from app.main import app; print('ok')"` → ✅
- `pytest tests/test_cloud_backup_service.py -v` → ✅ 8 passed
- `pytest tests/test_cloud_api.py -v` → ✅ 9 passed
- `npm run type-check` → ✅
- `npm run build` → ✅ (493.92 kB js, 235.74 kB css)

## Verification Results
全部通过。后端 17 个测试全绿，前端类型检查和生产构建均成功。

## Known Issues
1. 章枢云远程 API 尚不存在，所有云端调用会在 `CloudApiNotConfiguredError` 中优雅降级
2. 后端 `on_startup` 使用已弃用的 `@app.on_event`，FastAPI 推荐使用 lifespan，但不影响功能
3. 云端备份 V1 为手动触发上传，非实时同步

## Suggested Next Review Points for Codex
1. CloudApiClient 的 presigned URL 上传流程是否需要分片上传支持（大项目 > 100MB）
2. CloudBackupService 是否需要后台任务化（避免请求超时）
3. 云端备份记录是否需要自动清理/过期策略
4. CloudAccountDialog 是否需要记住上次登录邮箱
5. 是否需要增加云端备份的自动触发机制（如每日自动备份）
