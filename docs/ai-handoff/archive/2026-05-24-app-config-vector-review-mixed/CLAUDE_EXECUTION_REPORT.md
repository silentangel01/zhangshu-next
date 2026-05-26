---
archived_for_next_task: knowledge-retrieval-quality-tuning
date: 2026-05-24
task: API Key 设置 UI — 加密存储 + 应用设置弹窗
codex_plan: Claude Code plan mode (iridescent-twirling-wolf.md)
---

## Task Summary

新增应用级设置系统：DashScope API Key 通过 Fernet (AES-128-CBC + HMAC) 加密存储到 SQLite，前端提供设置弹窗（密码输入、测试连接、保存），`embedding_settings.py` 支持 env → DB → None 回退链。

## Files Changed

### 新增

- `backend/app/infrastructure/config_crypto.py` — Fernet 加密模块。PBKDF2-SHA256 密钥派生（platform.node + getuser + 固定 salt，200k iterations），`encrypt_value()`、`decrypt_value()`、`is_sensitive()`
- `backend/app/models/app_config.py` — `app_config` 表 ORM 模型。自然主键 `config_key`，字段 `config_value`、`is_encrypted`、`updated_at`
- `backend/app/repositories/app_config_repo.py` — `AppConfigRepository`，方法：`get`、`get_all`、`upsert`、`delete`
- `backend/app/services/app_config_service.py` — `AppConfigService`，敏感值自动加密存储、masked 读取、解密读取
- `backend/app/schemas/app_config.py` — Pydantic schemas：`AppConfigSetRequest`、`AppConfigResponse`、`TestDashScopeRequest`、`TestDashScopeResponse`
- `backend/app/api/app_config.py` — 3 个 API 端点：`GET /api/app-config`、`PUT /api/app-config`、`POST /api/app-config/test-dashscope`
- `frontend/src/entities/app-config/types.ts` — 前端类型定义
- `frontend/src/entities/app-config/api.ts` — 前端 API client（`getAppConfig`、`setAppConfig`、`testDashScopeConnection`）
- `frontend/src/features/app-config/AppSettingsDialog.vue` — 设置弹窗组件：密码输入 + 显示/隐藏、测试连接、保存、masked 预览、解密失败提示

### 修改

- `backend/app/infrastructure/database.py` — `init_database()` 中添加 `from app.models import app_config  # noqa: F401`
- `backend/app/main.py` — 添加 `app_config_router` 导入和 `include_router`
- `backend/app/infrastructure/embedding_settings.py` — 新增 `_get_api_key_from_db()`，`get_dashscope_api_key()` 改为 env → DB → None 回退链（延迟导入避免循环依赖）
- `frontend/src/pages/projects/ProjectDetailPage.vue` — "更多"菜单末尾新增"应用设置"按钮，挂载 `AppSettingsDialog`，扩展 `.more-menu-list` CSS 支持 `<button>` 元素

## Implementation Notes

1. **加密方案**：使用 `cryptography` 包的 Fernet（AES-128-CBC + HMAC-SHA256）。密钥从 `platform.node() + ":" + getpass.getuser()` 经 PBKDF2-SHA256 派生（salt 固定，200k iterations），密钥从不存储。同一台机器同一用户可解密，换机器/用户则密钥失效。
2. **Env → DB 回退链**：`embedding_settings.get_dashscope_api_key()` 先查 `.env` 环境变量，再查 DB 加密存储，都无则返回 None。DB 读取使用延迟导入（`from app.infrastructure.database import SessionLocal`）避免循环依赖。
3. **Masked API 响应**：敏感值从不以明文返回。API 返回 `{"has_value": true, "masked": "****abcd"}`。解密失败时额外附加 `"decrypt_error": true`。
4. **测试连接端点**：`POST /api/app-config/test-dashscope` 发送一条文本到 DashScope 验证 Key 有效性，返回模型名和向量维度。
5. **前端按钮 vs RouterLink**："更多"菜单中原有项都是 `<RouterLink>`（渲染为 `<a>`），"应用设置"使用 `<button>` 因为它是弹窗触发器而非导航。CSS 扩展了 `.more-menu-list` 选择器覆盖 `<button>` 样式。
6. **app_config 表设计**：通用 key-value 表，未来可扩展存储其他应用级设置（如 UI 偏好、默认参数等），不限于 API Key。

## Deviations from Codex Plan

无 Codex Plan。本任务由 Claude Code plan mode 设计，用户批准后执行。

## Verification Commands Run

- `python -c "from app.main import app"` → ✅ OK
- `python -m pytest tests/ -v` → ✅ 244 passed in 15.79s
- `npm run type-check` → ✅ 无类型错误
- `npm run build` → ✅ 构建成功（444.60 kB gzip: 131.40 kB）

## Verification Results

全部验证通过。后端 244 测试全部通过，前端 type-check 和 build 均成功。

## Known Issues

1. **加密密钥绑定机器**：Fernet 密钥从机器名 + 用户名派生，打包分发给不同用户后，旧密钥不可解密（设计上如此）。弹窗会提示"密钥已失效，请重新输入"。
2. **`cryptography` 依赖**：需要确认 PyInstaller 打包时是否正确包含 `cryptography` 包（包含 C 扩展）。建议在打包脚本中添加 hidden import。
3. **未使用真实 Key 测试**：测试连接端点代码已就绪，但未使用真实 DashScope API Key 验证端到端流程。

## Suggested Next Review Points for Codex

1. `cryptography` 在 PyInstaller onedir 打包中的兼容性（hidden imports、C 扩展）
2. PBKDF2 salt 和迭代次数是否足够安全，或者是否需要更强的密钥保护（如 Windows DPAPI）
3. `app_config` 表未来扩展策略（是否需要 config_key namespace 或分组）
4. 测试连接端点的错误信息是否足够友好（中文用户场景）
