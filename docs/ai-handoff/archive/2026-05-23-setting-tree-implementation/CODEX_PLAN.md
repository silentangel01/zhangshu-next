# Task Summary

为“设定”模块规划树状目录能力：根目录为“全书设定”，默认子目录包含“人物”“战力”“世界观”“历史”等，用户可创建新的子目录；设定页必须放在目录下，放入特定目录后自动继承类型，用户不再需要单独选择设定类型。

本计划只规划实现方案。Codex 未修改业务代码。本计划应由 Claude Code 执行；Claude Code 执行前应再次检查计划与当前代码是否冲突，如有冲突应停止并反馈。

关于“设定的存储是否需要一起升级改造”：建议需要，但采用最小兼容升级。不要拆分新表；继续复用现有 `setting_items` 表，增加节点语义字段来区分目录和设定页，以保留现有章节关联、资料关联、关系图绑定、搜索和软删除能力。

# Current Codebase Findings

- 后端当前设定主表是 `backend/app/models/setting_item.py` 的 `SettingItem`，表名 `setting_items`，已有 `parent_id`、`item_type`、`order_index`、`deleted_at`、`version` 等字段。
- 当前 `parent_id` 已可表达树形父子关系，但没有区分“目录节点”和“设定页节点”。
- 当前 `item_type` 是每个设定项必填字段，定义在 `backend/app/schemas/setting.py` 和 `frontend/src/entities/setting/types.ts`，现有类型不包含 `character`。
- 当前后端 API 在 `backend/app/api/settings.py`，已有：
  - `GET /api/projects/{project_id}/settings`
  - `POST /api/projects/{project_id}/settings`
  - `GET /api/settings/{setting_id}`
  - `PATCH /api/settings/{setting_id}`
  - `DELETE /api/settings/{setting_id}`
- 当前业务逻辑在 `backend/app/services/setting_service.py`，当前只校验父节点存在、项目一致，以及不能把自己设为父级；还没有校验循环父子关系，也没有校验父级必须是目录。
- 当前数据访问在 `backend/app/repositories/setting_repo.py`，列表按 `order_index`、`updated_at`、`created_at` 排序，并支持按 `item_type`、`canon_status`、`importance`、`keyword` 过滤。
- 当前数据库初始化在 `backend/app/infrastructure/database.py`，使用 `Base.metadata.create_all`，并已有通过 `ALTER TABLE` 做兼容升级的先例。
- 前端设定页是 `frontend/src/pages/settings/ProjectSettingsPage.vue`，已经在页面内用 `buildTree(settings.value)` 根据 `parent_id` 展示缩进树，但表单仍要求用户选择“类型”和“父级设定”。
- 前端设定 API 和类型在：
  - `frontend/src/entities/setting/api.ts`
  - `frontend/src/entities/setting/types.ts`
- 章节写作面板里的设定绑定在 `frontend/src/features/settings/ChapterSettingPanel.vue`，当前从 `listProjectSettings(projectId)` 获取全部设定项。树状目录上线后，这里必须只展示可绑定的设定页，不展示目录。
- 当前 `backend/tests/` 没有可见测试文件；前端仅有 `frontend/src/__tests__/App.spec.ts`。本任务需要补充聚焦测试。

# Architecture Decision

采用“同表节点化”的最小升级方案：

- 继续使用 `setting_items` 表，不新建 `setting_folders` 表。
- 在 `setting_items` 中新增字段：
  - `node_kind`: `folder` 或 `page`，默认 `page`。
  - `folder_key`: 可空字符串，用于识别系统目录，如 `root`、`characters`、`power`、`world`、`history`；用户目录为空。
  - `folder_default_item_type`: 可空字符串，目录下新建设定页时使用的默认类型。
  - `is_system`: 布尔值，标记系统目录，防止误删根目录和默认目录。
- 保留 `item_type` 字段，设定页仍然存储最终类型，方便现有筛选、章节绑定、关系图、后续 RAG 索引使用。
- 目录节点也保留 `item_type` 以兼容非空约束，可设置为 `folder_default_item_type`，根目录用 `custom`。
- 新增 `character` 到 `SettingItemType`，用于“人物”目录下的设定页。
- “全书设定”根目录和默认目录由后端在项目设定列表加载或项目初始化相关流程中幂等补齐；不要由前端硬编码伪节点。
- 前端 UI 只负责展示和提交用户操作，不在组件中写目录补齐、类型继承、循环校验等业务规则。
- AI / RAG 扩展边界：目录只作为结构和元数据；后续向量索引应默认索引 `node_kind='page'` 的设定页，目录作为 metadata path，不直接作为知识正文。

# Files to Create or Modify

后端需要修改：

- `backend/app/models/setting_item.py`
  - 新增 `node_kind`、`folder_key`、`folder_default_item_type`、`is_system` 字段。
- `backend/app/schemas/setting.py`
  - 新增 `SettingNodeKind`。
  - 扩展 `SettingItemType`，加入 `character`。
  - 调整 `SettingCreate` / `SettingUpdate` / `SettingRead`，支持目录字段。
- `backend/app/repositories/setting_repo.py`
  - 支持按 `node_kind` 过滤。
  - 增加按 `folder_key` 查询系统目录的方法。
  - 增加获取子孙节点或按父级查询的方法，用于防循环、删除校验、目录展示。
- `backend/app/services/setting_service.py`
  - 增加系统目录幂等补齐逻辑。
  - 增加目录/设定页创建和更新规则。
  - 增加父子关系、循环、删除系统目录等校验。
- `backend/app/api/settings.py`
  - `GET /api/projects/{project_id}/settings` 增加 `node_kind` 查询参数。
  - 其它接口保持路径不变，避免破坏现有调用。
- `backend/app/infrastructure/database.py`
  - 新增 `_ensure_setting_tree_columns()`，用 `ALTER TABLE` 为旧数据库补列。
  - 在 `init_database()` 中调用。
  - 可在初始化后调用系统目录补齐函数，或在 `SettingService.list_project_settings()` 中补齐。
- `backend/tests/`
  - 新增设定树相关后端测试文件，例如 `backend/tests/test_settings_tree.py`。

前端需要修改：

- `frontend/src/entities/setting/types.ts`
  - 新增 `SettingNodeKind`。
  - `SettingItemType` 加入 `character`。
  - `SettingItem`、payload、filters 增加目录字段。
  - 修正/确认中文 label：人物、世界观、地点、组织/势力、战力、历史等。
- `frontend/src/entities/setting/api.ts`
  - `SettingFilters` 支持 `node_kind`。
  - 继续复用现有 API 路径。
- `frontend/src/pages/settings/ProjectSettingsPage.vue`
  - 把左侧从“设定项列表”升级为目录树。
  - 区分目录节点和设定页节点。
  - 在目录选中状态下显示目录操作和目录下设定列表。
  - 在设定页编辑状态下隐藏类型选择，显示继承来源目录和只读类型。
  - 新增创建目录、创建设定页、移动设定页到目录等交互。
- `frontend/src/features/settings/ChapterSettingPanel.vue`
  - 绑定下拉只加载 `node_kind='page'` 的设定页。
  - 展示时不要显示目录节点。
- 视现有测试框架情况，新增或调整前端测试：
  - `frontend/src/__tests__/settings-tree.spec.ts`，或按现有项目测试习惯命名。

不建议修改：

- `backend/app/main.py`，除非只是已有路由包含方式的必要维护；本任务不需要。
- `frontend/src/router/index.ts`，本任务不需要新增路由。
- `frontend/src/App.vue`，本任务不需要。
- Project / Volume / Chapter / Editor / Autosave / Version / Import / Outline / Character / Clue 现有 API。

# Implementation Steps for Claude Code

1. 执行前检查
   - 读取本计划。
   - 运行 `git status --short`，确认是否存在与设定模块相关的未提交改动。
   - 如发现 `backend/app/models/setting_item.py`、`backend/app/services/setting_service.py`、`frontend/src/pages/settings/ProjectSettingsPage.vue` 等文件已有非本任务改动，先停止并反馈。

2. 后端模型升级
   - 修改 `backend/app/models/setting_item.py`。
   - 为 `SettingItem` 增加：
     - `node_kind: String(16), nullable=False, default='page', index=True`
     - `folder_key: String(64), nullable=True, index=True`
     - `folder_default_item_type: String(32), nullable=True, index=True`
     - `is_system: Boolean, nullable=False, default=False, index=True`
   - 需要从 SQLAlchemy 引入 `Boolean`。
   - 保留 `item_type` 非空，避免旧数据和旧查询破裂。

3. 数据库兼容升级
   - 修改 `backend/app/infrastructure/database.py`。
   - 新增 `_ensure_setting_tree_columns()`：
     - 如果 `setting_items` 表不存在则直接返回。
     - 如果缺少 `node_kind`，执行 `ALTER TABLE setting_items ADD COLUMN node_kind VARCHAR(16) NOT NULL DEFAULT 'page'`。
     - 如果缺少 `folder_key`，执行 `ALTER TABLE setting_items ADD COLUMN folder_key VARCHAR(64)`。
     - 如果缺少 `folder_default_item_type`，执行 `ALTER TABLE setting_items ADD COLUMN folder_default_item_type VARCHAR(32)`。
     - 如果缺少 `is_system`，执行 `ALTER TABLE setting_items ADD COLUMN is_system BOOLEAN NOT NULL DEFAULT 0`。
     - 将旧数据保持为 `node_kind='page'`，不改变现有 `item_type`、`parent_id`、`detail`。
   - 在 `init_database()` 的 `Base.metadata.create_all(bind=engine)` 后调用该函数。

4. Schema 升级
   - 修改 `backend/app/schemas/setting.py`。
   - `SettingItemType` 增加 `"character"`。
   - 新增 `SettingNodeKind = Literal["folder", "page"]`。
   - `SettingBase` 增加：
     - `node_kind: SettingNodeKind = "page"`
     - `folder_key: str | None = None`
     - `folder_default_item_type: SettingItemType | None = None`
   - 将 `SettingCreate.item_type` 调整为可选：`SettingItemType | None = None`。
   - `SettingUpdate` 增加 `node_kind`、`folder_default_item_type`，但不允许客户端更新 `folder_key` 和 `is_system`。
   - `SettingRead` 增加 `node_kind`、`folder_key`、`folder_default_item_type`、`is_system`。
   - 保持 `SettingRead.item_type: str`，兼容当前返回。

5. Repository 升级
   - 修改 `backend/app/repositories/setting_repo.py`。
   - `list_active_by_project()` 增加参数 `node_kind: str | None = None`，并加入过滤。
   - 新增方法：
     - `get_active_by_project_and_folder_key(project_id: str, folder_key: str) -> SettingItem | None`
     - `list_active_children(parent_id: str) -> list[SettingItem]`
     - `list_active_descendants(project_id: str, root_id: str) -> list[SettingItem]`，可在 service 中用广度或深度遍历实现；如 repo 只提供 children，遍历放 service。
   - 查询排序保持 `order_index asc`、`title zh-Hans-CN` 前端排序可保留，后端排序至少保持稳定。

6. Service 业务规则
   - 修改 `backend/app/services/setting_service.py`。
   - 新增常量：
     - 根目录：`folder_key='root'`，title `全书设定`，`folder_default_item_type=None`，`item_type='custom'`，`is_system=True`。
     - 默认目录：
       - `characters` / `人物` / `character`
       - `power` / `战力` / `power_system`
       - `world` / `世界观` / `world`
       - `history` / `历史` / `history`
   - 在 `list_project_settings()` 前调用 `_ensure_default_setting_folders(project_id)`。
   - `_ensure_default_setting_folders(project_id)` 必须幂等：
     - 如果 root 不存在，创建 root。
     - 如果默认目录不存在，创建到 root 下。
     - 如果已存在，不重复创建，不覆盖用户内容。
   - `create_setting()` 规则：
     - `node_kind='folder'`：
       - 父级必须为空或为 folder；用户目录建议默认挂到 root 下，如果没有传 parent_id，则 service 自动设置为 root id。
       - `folder_default_item_type` 为空时使用 `custom`。
       - `item_type` 设置为 `folder_default_item_type` 或 `custom`。
       - 用户创建目录的 `is_system=False`，`folder_key=None`。
     - `node_kind='page'`：
       - 父级必须是 folder；如果没有传 parent_id，返回 400 级业务错误，不允许页直接挂根空父级。
       - 如果 payload 未传 `item_type`，从父目录最近的 `folder_default_item_type` 继承；如果仍为空，使用 `custom`。
       - 即使前端隐藏类型，也必须由后端最终写入 `item_type`。
   - `update_setting()` 规则：
     - 不允许把系统目录改成 page。
     - 不允许 page 作为任何节点的父级。
     - 移动节点时必须校验同项目、父级存在、父级是 folder、不会形成循环。
     - page 移动到新目录时，如请求未显式传 `item_type`，应更新为新目录默认类型。
     - folder 修改 `folder_default_item_type` 后，不要自动批量改写已有子页面类型，除非用户明确要求；本任务先只影响后续新建页面，避免大规模隐式数据变更。
   - `delete_setting()` 规则：
     - 不允许删除 `is_system=True` 的 root 和默认目录。
     - 删除用户目录时，如果有活跃子节点，建议返回 400，提示先移动或删除子节点；不要级联软删除，避免误删大量设定页。
     - 删除 page 保持当前软删除逻辑。
   - 新增异常类：
     - `SettingInvalidNodeKindError`
     - `SettingInvalidParentError`
     - `SettingParentCycleError`
     - `SettingSystemFolderProtectedError`
     - `SettingFolderNotEmptyError`

7. API 层更新
   - 修改 `backend/app/api/settings.py`。
   - 导入 `SettingNodeKind`。
   - `list_project_settings()` 增加 `node_kind: SettingNodeKind | None = Query(default=None)`，传给 service。
   - 对新增 service 异常映射：
     - invalid parent / cycle / protected / folder not empty -> 400。
     - not found -> 保持 404。
   - API 路径保持不变。

8. 前端类型和 API 更新
   - 修改 `frontend/src/entities/setting/types.ts`。
   - 增加：
     - `export type SettingNodeKind = 'folder' | 'page'`
     - `SettingItemType` 加入 `'character'`
     - `SettingItem.node_kind`
     - `SettingItem.folder_key`
     - `SettingItem.folder_default_item_type`
     - `SettingItem.is_system`
   - `SettingPayload` 支持 `node_kind`、`folder_default_item_type`，并让 `item_type` 可选。
   - `SettingFilters` 支持 `node_kind?: SettingNodeKind`。
   - 更新 `settingItemTypeLabels`，确保用户可见中文为简体中文：
     - `character: '人物'`
     - `power_system: '战力'` 或 `力量体系`，建议 UI 中目录名用 `战力`，类型标签可用 `战力/力量体系`。
   - 修改 `frontend/src/entities/setting/api.ts` 的 query 构造无需大改，确保新 filter 会被透传。

9. 前端设定页重构，控制改动范围
   - 修改 `frontend/src/pages/settings/ProjectSettingsPage.vue`，不要重写整个页面，围绕现有状态和 `buildTree()` 做定向升级。
   - 数据加载：
     - `allSettings` 包含 folder + page。
     - `settings` 可继续作为过滤结果，但树视图应能展示目录；当筛选关键字时，保留匹配页及其祖先目录，避免树断裂。
   - 计算属性：
     - `folders = allSettings.filter(node_kind==='folder')`
     - `pages = allSettings.filter(node_kind==='page')`
     - `selectedFolder`
     - `selectedPage`
   - 左侧树：
     - 用图标或文本区分目录和设定页。
     - 默认选中 root 或第一个目录。
     - 系统目录显示为固定目录，不展示删除按钮。
   - 操作：
     - “新建目录”：创建 `node_kind='folder'`，父级为当前目录或 root。
     - “新建设定”：创建 `node_kind='page'`，`parent_id` 为当前目录。
     - 设定页表单不再展示可编辑类型 select；改为展示“类型：由「人物/战力/世界观/历史/自定义目录」继承”。
     - 用户自建目录表单允许选择默认类型，默认 `custom`。
     - 移动设定页到其它目录时，提示类型将随目录变更。
   - 保留现有关系图打开和 `MaterialLinkPanel` 行为，只对 `node_kind='page'` 显示。
   - 不在前端实现系统目录补齐；只消费后端返回。

10. 章节设定绑定面板更新
    - 修改 `frontend/src/features/settings/ChapterSettingPanel.vue`。
    - `loadProjectSettings()` 改为 `listProjectSettings(props.projectId, { node_kind: 'page' })`。
    - 下拉选项只展示设定页。
    - 可选增强：选项文本显示目录路径，例如 `人物 / 张三`，但路径计算应使用前端已拿到的列表；如只加载 page 不够算路径，可先不做路径显示，避免扩大范围。

11. 测试
    - 后端新增 `backend/tests/test_settings_tree.py`。
    - 覆盖：
      - 列表时自动补齐 root 和默认目录。
      - 创建 page 不传 `item_type` 时继承父目录默认类型。
      - 创建 folder 时写入 `node_kind='folder'` 和 `folder_default_item_type`。
      - 禁止 page 作为父级。
      - 禁止循环父子关系。
      - 禁止删除系统目录。
      - 删除非空用户目录返回错误。
      - `GET /api/projects/{project_id}/settings?node_kind=page` 不返回目录。
    - 前端可新增聚焦测试，最低要求：
      - `SettingItemType` 包含 `character`。
      - `ChapterSettingPanel` 调用 `listProjectSettings` 时带 `node_kind: 'page'`。
      - 如测试成本过高，执行报告中说明未覆盖原因，并至少完成 type-check。

12. 执行报告
    - Claude Code 完成后写入 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
    - 报告必须包含：
      - 实际修改文件列表。
      - 与本计划的偏差。
      - 数据库兼容升级说明。
      - 验证命令与结果。
      - 未完成项或风险。

# Constraints

- 不要修改 `backend/app/main.py` 中的业务逻辑。
- 不要新增大型依赖。
- 不要引入 Alembic 或迁移框架，除非用户另行明确要求；本任务使用当前项目已有的启动时兼容升级风格。
- 不要拆分 `setting_items` 为多个表，避免破坏现有章节设定关联、资料关联、关系图绑定。
- 不要把目录补齐、类型继承、父子循环校验写进前端组件。
- 不要让目录节点参与章节绑定。
- 不要自动批量改写已有设定页类型，除非用户明确授权。
- 不要删除或重建已有设定数据。
- 用户可见 UI 文案必须是简体中文。
- 代码标识符、API 路径、数据库表名保持英文。
- 必须保留软删除使用 `deleted_at`。
- 必须考虑未来 RAG / 向量检索 / 知识图谱边界：设定页是知识正文，目录是结构 metadata。

# Verification Commands

后端：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
pytest
python -m compileall app
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

前端：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit
npm run build
```

手动验证建议：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
cd F:\zhangshu\frontend
npm run dev
```

浏览器验证：

- 打开项目的“设定”页面。
- 确认左侧出现“全书设定”根目录。
- 确认默认目录存在：人物、战力、世界观、历史。
- 在“人物”目录下新建设定页，确认表单不要求选择类型，保存后类型为人物。
- 自建一个目录，选择默认类型为 custom 或其它类型，在目录下新建设定页。
- 尝试删除系统目录，应被阻止。
- 尝试在章节编辑器绑定设定，确认下拉列表不出现目录。

# Acceptance Criteria

- 设定页展示为树状结构，根节点为“全书设定”。
- 每个项目都会幂等拥有默认目录：人物、战力、世界观、历史。
- 用户可以创建新的子目录。
- 用户在目录下创建设定页时，不需要单独设置设定类型。
- 设定页的 `item_type` 由父目录默认类型决定并持久化。
- 旧设定数据不会丢失，旧数据默认作为 `node_kind='page'` 保留。
- 章节设定绑定、资料关联、关系图绑定仍能使用设定页 id。
- 目录节点不会出现在章节设定绑定候选列表中。
- 系统目录不能被删除。
- 非空目录不会被直接删除。
- 父子循环会被后端拒绝。
- 后端测试、前端 type-check、前端构建通过；如某项无法运行，Claude 报告必须说明原因。

# Risks and Watchpoints

- 当前 `AGENTS.md` 和部分现有文件在 PowerShell 输出中显示为乱码，Claude Code 修改中文文案时必须确保文件实际以 UTF-8 保存。
- 当前 `SettingItemType` 没有 `character`，新增后需同步后端 schema、前端 type、label、测试。
- 当前 `item_type` 非空；目录节点必须给兼容值，否则旧数据库和 Pydantic 返回可能出错。
- 当前只检查不能把自己设为父级，不检查深层循环；树状目录上线前必须补上循环校验。
- 如果系统目录补齐放在列表接口中，首次访问会产生写入；这是可接受的，但必须幂等。
- 如果默认目录 title 被用户手动修改，`folder_key` 仍应保持系统识别能力。
- 如果用户把旧设定移动到默认目录，是否改写类型需要明确：本计划建议移动 page 且未显式传 `item_type` 时继承新目录；前端应提示。
- 不要让前端筛选后丢失祖先目录，否则树会断裂。
- 目录删除策略要保守，避免误删子设定页。
- 未来 RAG 索引时必须过滤 `node_kind='page'`，目录路径作为 metadata。

# Review Checklist

- 是否只修改了本计划列出的文件。
- 是否保留现有 API 路径，避免破坏旧调用。
- 是否在 `setting_items` 上完成最小兼容升级，而不是拆表。
- 是否新增并正确使用 `node_kind`。
- 是否新增并同步 `character` 类型。
- 是否由后端负责默认目录补齐和类型继承。
- 是否禁止 page 作为父级。
- 是否禁止父子循环。
- 是否保护系统目录。
- 是否禁止直接删除非空目录。
- 是否确保章节设定绑定只展示 page。
- 是否没有把 UI、业务逻辑、数据访问混在同一文件。
- 是否没有引入无理由依赖。
- 是否没有修改无关模块。
- 是否没有提交本地数据库、日志、密钥、临时文件或构建产物。
- 是否运行并记录了后端测试、前端 type-check、前端测试和构建结果。
