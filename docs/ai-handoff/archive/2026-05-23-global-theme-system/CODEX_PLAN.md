# Task Summary

本任务规划章枢前端 UI 主题与体验优化。重点是把“护眼模式 / 黑夜模式”从正文编辑器内的局部显示设置升级为全局应用主题；同时明确关系图、时间线等 canvas/画布区域的底色、网格、坐标轴、节点底色不应随全局主题改变，以保持视觉稳定和内容辨识度。

Codex 本轮只做规划，不修改业务代码。本计划应由 Claude Code 执行；Claude Code 执行前应再次检查当前代码与计划是否冲突，如冲突应停止并反馈。

# Current Codebase Findings

- 已阅读 Claude 上一轮 `project-book-profile` 执行报告。Claude 已完成书籍档案升级：新增 Project 元数据、封面 API、默认封面、标签输入、封面上传组件，并通过前端 type-check/test/build 和后端 compileall；pytest 因环境未安装无法运行。
- 旧交接文件已归档到 `docs/ai-handoff/archive/2026-05-23-project-book-profile/`。
- `frontend/src/style.css` 已经存在全局主题 token：
  - 默认 `:root`
  - `[data-theme="eye-care"]`
  - `[data-theme="dark"]`
  但当前没有应用级主题状态管理，也没有统一入口设置 `document.documentElement.dataset.theme`。
- 当前主题切换只存在于 `frontend/src/features/chapters/ChapterEditor.vue`：
  - `EditorTheme = 'plain' | 'eye' | 'dark'`
  - 存储 key 为 `zhangshu:editor:appearance`
  - 只通过 `getEditorThemeStyle()` 给正文 `textarea` 设置内联 `background / borderColor / color`
  - 这会导致编辑区变色，但页面背景、侧栏、资料面板、弹窗、列表仍保持原色。
- `frontend/src/App.vue` 当前只有 `<RouterView />`，没有全局布局或主题控制。
- `frontend/src/main.ts` 仅创建 Vue app、注册 Pinia/router、引入 `style.css`。如果做全局主题，适合在 mount 前先应用本地主题，减少首屏闪烁。
- 图谱画布：
  - `frontend/src/features/graph/GraphCanvas.vue` 的 `.graph-canvas` 使用 `var(--zs-color-surface)` 作为背景。
  - 网格线在 `gridStyle` 中写死为 `rgb(107 124 131 / 14%)`。
  - 画布状态浮层使用主题变量。
  - 如果全局主题直接切换，画布背景会跟着变暗/变黄，不符合本次要求。
- 时间线画布：
  - `frontend/src/pages/timeline/ProjectTimelinePage.vue` 的 `.timeline-canvas-panel`、`.timeline-canvas-body`、轨道轴线、事件节点大量使用主题变量。
  - 时间线虽然不是 `<canvas>` 元素，但在交互语义上是画布式工作区，应纳入“画布不随主题改变底色”的边界。
- 还有不少页面和章节辅助面板仍有硬编码浅色值，例如：
  - `frontend/src/pages/characters/ProjectCharactersPage.vue`
  - `frontend/src/pages/clues/ProjectCluesPage.vue`
  - `frontend/src/features/characters/ChapterCharacterPanel.vue`
  - `frontend/src/features/clues/ChapterCluePanel.vue`
  - `frontend/src/features/timeline/ChapterTimelinePanel.vue`
  - `frontend/src/features/graph/ChapterGraphCard.vue`
  这些区域在全局深色/护眼模式下可能出现浅色孤岛。
- 当前已有大量未提交改动，Claude Code 不得回退或格式化无关文件。

# Architecture Decision

采用“应用级主题偏好 + 全局 CSS token + 画布中性 token + 逐步清理硬编码颜色”的方案。

主题层级：

- 全局应用主题只负责应用外壳、页面、面板、弹窗、按钮、表单、列表、正文编辑器默认视觉。
- 正文编辑器继续保留字体、字号、行距、宽度、首行缩进、段间距等写作排版设置。
- 原正文编辑器里的“显示模式”应迁移为全局主题选择，或在编辑器中显示为同一个全局主题控制入口，不能继续只作用于 textarea。
- 画布类工作区保持中性视觉，不跟随 `eye-care` / `dark` 改变底色：
  - 关系图画布底色固定。
  - 关系图网格线固定。
  - 时间线画布底色、轨道轴线、事件节点底色建议固定。
  - 画布外部页面、工具栏、侧边栏、检查器、弹窗可以跟随全局主题。

建议新增主题模块：

- `frontend/src/shared/theme/appTheme.ts`
  - 定义 `AppTheme = 'default' | 'eye-care' | 'dark'`
  - 定义 storage key：`zhangshu:app:theme`
  - 提供：
    - `readAppTheme()`
    - `writeAppTheme(theme)`
    - `applyAppTheme(theme)`
    - `isAppTheme(value)`
    - `getInitialAppTheme()`
  - `applyAppTheme('default')` 应移除 `data-theme`，而不是写入 `data-theme="default"`。

建议新增主题控制组件：

- `frontend/src/shared/theme/ThemeSwitcher.vue`
  - 作为全局小型控件，可放在 `App.vue` 的 fixed 位置或页面 header 可复用位置。
  - UI 用三个选项：默认、护眼、黑夜。
  - 不引入图标库；可用文字按钮或 segmented control。
  - 所有文案为简体中文。

画布中性 token：

- 在 `frontend/src/style.css` 的 `:root` 增加不随主题变化的 token，例如：
  - `--zs-canvas-bg: #fbfcfe`
  - `--zs-canvas-grid: rgb(107 124 131 / 14%)`
  - `--zs-canvas-axis: #cbd5e1`
  - `--zs-canvas-node-bg: #ffffff`
  - `--zs-canvas-node-border: #d8dee9`
  - `--zs-canvas-text: #111827`
  - `--zs-canvas-text-muted: #64748b`
- 不要在 `[data-theme="eye-care"]` 或 `[data-theme="dark"]` 中覆盖这些 canvas token，除非是为了完全保持相同值。

其它 UI 优化建议一起纳入本计划，但应分优先级执行：

- P0：全局主题真正生效，且画布不变色。
- P1：把高频页面的硬编码浅色替换为 `--zs-*` token，减少深色模式白块。
- P1：统一主题控制入口、焦点样式、表单背景、弹窗遮罩和状态提示。
- P2：统一列表/卡片密度，避免新书籍卡片、设定、伏笔、人物页看起来像不同产品。
- P2：移动端 header/actions 换行和工具栏溢出优化。
- P2：空状态、加载态、错误态文案和视觉样式统一。

# Files to Create or Modify

建议新增：

- `frontend/src/shared/theme/appTheme.ts`
  - 应用级主题读写和 DOM 应用逻辑。
- `frontend/src/shared/theme/ThemeSwitcher.vue`
  - 全局主题切换 UI。
- `frontend/src/__tests__/app-theme.spec.ts`
  - 测试主题读写、非法值回退、`data-theme` 应用行为。

建议修改：

- `frontend/src/main.ts`
  - 在 `app.mount('#app')` 前调用 `applyAppTheme(getInitialAppTheme())`。
- `frontend/src/App.vue`
  - 最小化增加应用外壳和 `ThemeSwitcher`。
  - 不要重写 router 或页面结构。
- `frontend/src/style.css`
  - 补充 canvas 中性 token。
  - 补充表单、弹窗、状态提示等可复用 token 或基础样式。
  - 确保 `html/body` 在全局主题下生效。
- `frontend/src/features/chapters/ChapterEditor.vue`
  - 删除或迁移局部 `EditorTheme` 内联颜色逻辑。
  - 保留字体、字号、行距、宽度、首行缩进、段间距等排版设置。
  - 如果保留“显示模式”入口，应绑定全局主题，而不是只改 textarea。
- `frontend/src/features/graph/GraphCanvas.vue`
  - 使用 `--zs-canvas-*` token 固定画布底色、网格、节点画布提示底色。
- `frontend/src/pages/timeline/ProjectTimelinePage.vue`
  - 仅把中间时间线画布区域改用 `--zs-canvas-*` token。
  - 左右面板、toolbar、表单继续使用全局主题 token。
- `frontend/src/features/graph/GraphNode.vue`
  - 如节点底色随主题变化，应改为 canvas 中性 token 或节点自身颜色体系。
- `frontend/src/features/graph/GraphEdgeOverlay.vue`
  - 如线条在深色主题下被主题变量影响，应改为稳定 canvas token 或明确关系色。

建议按风险选择性修改：

- `frontend/src/pages/projects/ProjectsPage.vue`
- `frontend/src/pages/projects/ProjectDetailPage.vue`
- `frontend/src/pages/characters/ProjectCharactersPage.vue`
- `frontend/src/pages/clues/ProjectCluesPage.vue`
- `frontend/src/pages/settings/ProjectSettingsPage.vue`
- `frontend/src/features/characters/ChapterCharacterPanel.vue`
- `frontend/src/features/clues/ChapterCluePanel.vue`
- `frontend/src/features/timeline/ChapterTimelinePanel.vue`
- `frontend/src/features/graph/ChapterGraphCard.vue`
  - 将明显硬编码的浅色背景、边框、正文色替换为 `--zs-*` token。
  - 本轮不要为了颜色清理重写这些模块的业务逻辑和模板结构。

不应修改：

- 后端代码。
- API、数据库、schema、service、repository。
- 路由定义，除非发现主题入口必须依赖路由且没有其它方式；一般不需要。
- 图谱和时间线的数据逻辑、拖拽逻辑、保存逻辑。

# Implementation Steps for Claude Code

1. 执行前检查
   - 读取本计划。
   - 运行 `git status --short`，确认当前存在多轮未提交改动。
   - 不要回退、格式化或重写与主题无关的功能文件。
   - 先运行前端 type-check，若当前已失败，停止并报告：
     ```powershell
     cd F:\zhangshu\frontend
     npm run type-check
     ```

2. 新建应用级主题模块
   - 新建 `frontend/src/shared/theme/appTheme.ts`。
   - 定义：
     ```ts
     export type AppTheme = 'default' | 'eye-care' | 'dark'
     export const APP_THEME_STORAGE_KEY = 'zhangshu:app:theme'
     ```
   - `readAppTheme()` 从 localStorage 读取，非法值回退 `default`。
   - `writeAppTheme(theme)` 写入 localStorage。
   - `applyAppTheme(theme)`：
     - `default`：`document.documentElement.removeAttribute('data-theme')`
     - `eye-care` / `dark`：设置 `document.documentElement.dataset.theme = theme`
   - 处理 localStorage 不可用的异常，沿用 `safeReadJson` / `safeWriteJson` 或直接 try/catch。

3. 启动前应用主题
   - 修改 `frontend/src/main.ts`。
   - 在创建或 mount app 前调用：
     ```ts
     applyAppTheme(getInitialAppTheme())
     ```
   - 目标是减少页面先闪默认主题再切换的体验。

4. 新建主题切换组件
   - 新建 `frontend/src/shared/theme/ThemeSwitcher.vue`。
   - 组件内部维护当前 `theme`。
   - 点击选项后：
     - 更新本地状态。
     - 调用 `applyAppTheme(theme)`。
     - 调用 `writeAppTheme(theme)`。
   - UI 建议：
     - class 使用 `theme-switcher`。
     - 三个按钮文案：`默认`、`护眼`、`黑夜`。
     - `aria-label="全局主题"`。
     - 当前选项使用 `aria-pressed="true"` 和 active class。
   - 不要引入新依赖。

5. 在 App 中放置全局主题入口
   - 修改 `frontend/src/App.vue`。
   - 最小化结构：
     - `<ThemeSwitcher class="app-theme-switcher" />`
     - `<RouterView />`
   - 控件位置建议 fixed 在右下角或右上角，避免侵入各页面 header。
   - 不要把所有页面包进复杂布局，不要重写 router-view 逻辑。
   - 移动端确认不遮挡主要操作；如果 fixed 位置会挡住按钮，放右下角并留出安全间距。

6. 更新全局样式 token
   - 修改 `frontend/src/style.css`。
   - 在 `:root` 增加 canvas 中性 token。
   - 不在主题块里改变这些 canvas token。
   - 检查现有 `[data-theme="eye-care"]` 和 `[data-theme="dark"]` 是否能覆盖常规页面的 `--zs-color-*`。
   - 为 `ThemeSwitcher` 增加全局样式或在组件 scoped 样式内完成。
   - 确保按钮、input、textarea、select 的默认颜色使用变量，避免系统控件在黑夜模式下突兀。

7. 迁移 ChapterEditor 的局部主题
   - 修改 `frontend/src/features/chapters/ChapterEditor.vue`。
   - 将 `EditorTheme` 从 `EditorAppearanceSettings` 中移除，或保留兼容读取但不再作为局部 textarea 颜色来源。
   - `editorStyle` 中删除 `...getEditorThemeStyle(...)`。
   - 删除 `getEditorThemeStyle()`。
   - “更多设置”中的 `显示模式`：
     - 推荐移除，改由全局悬浮主题入口负责。
     - 如保留，则改为全局主题组件或调用 `appTheme` 模块，不能只改编辑器。
   - 保留其它写作排版设置及旧 storage 兼容：旧 `zhangshu:editor:appearance.theme` 读到时不要报错，但无需继续写入。

8. 固定关系图画布视觉
   - 修改 `frontend/src/features/graph/GraphCanvas.vue`。
   - `.graph-canvas` 背景改为 `var(--zs-canvas-bg)`。
   - `gridStyle.backgroundImage` 改为使用 `var(--zs-canvas-grid)` 或常量 token 字符串。
   - `.canvas-status span` / `.canvas-hints span` 如果属于浮层 UI，可继续使用主题变量；如果用户反馈画布内浮层也应稳定，可改为 canvas token。
   - 不改拖拽、缩放、节点创建、保存逻辑。

9. 固定图谱节点和边的画布内核心颜色
   - 检查 `frontend/src/features/graph/GraphNode.vue`、`GraphEdgeOverlay.vue`。
   - 节点卡片默认底色、边框、文本如果使用全局 `--zs-color-surface`，改为 canvas token。
   - 节点类型色、用户自定义颜色、选中态可保留现有语义色，但必须在默认/护眼/黑夜下可读。
   - 不改变节点数据字段或关系类型。

10. 固定时间线画布视觉
   - 修改 `frontend/src/pages/timeline/ProjectTimelinePage.vue`。
   - 仅对中间画布区域使用 canvas token：
     - `.timeline-canvas-panel`
     - `.timeline-canvas-body`
     - `.lane-axis`
     - `.track-row-label`
     - `.timeline-node`
     - `.timeline-edge .edge-line`
     - 画布内浮动标签
   - 左侧轨道列表、右侧详情面板、toolbar、表单继续跟随全局主题。
   - 不改事件拖拽、连接测量、保存逻辑。

11. 第一轮硬编码浅色清理
   - 优先处理用户高频可见区域：
     - `ProjectsPage`
     - `ProjectDetailPage` 的项目概览和 header 操作
     - `ProjectCharactersPage`
     - `ProjectCluesPage`
     - `ProjectSettingsPage`
   - 将明显的 `#ffffff`、`#f6f8fb`、`#111827`、`#64748b`、`#2563eb`、浅色状态背景等替换为已有 `--zs-color-*` token。
   - 不要改模板结构，除非为了主题入口最小必要。
   - 大型辅助面板可在执行报告里列为后续清理项，不要一次性重写所有 CSS。

12. 其它 UI 改进建议，由 Claude Code 酌情小范围采纳
   - 建议 A：统一 header actions 的按钮尺寸和视觉层级，主要操作用 primary，导航/辅助操作用 secondary。
   - 建议 B：统一状态提示，错误/成功/警告使用全局 `.zs-status` 或同一组 token，减少每页自定义红绿块。
   - 建议 C：统一空状态和加载态，优先复用 `.zs-empty` 或增加轻量 `.zs-state-message`。
   - 建议 D：列表页搜索与筛选区统一为“顶部搜索 + 筛选按钮/菜单”的模式，延续设定与伏笔模块方向；本轮只提出，不强制改所有页面。
   - 建议 E：为全局主题切换增加键盘可访问性和可见 focus 样式。
   - 建议 F：移动端工具栏避免横向溢出，必要时换行或折叠到“更多”菜单。
   - 建议 G：减少页面内重复 `.back-link`、`.primary-button`、`.secondary-button` 局部定义，逐步迁移到全局 utility class。
   - 这些建议不是强制项；若采纳，必须保持小范围修改，并在执行报告说明采纳了哪些。

13. 测试与验证
   - 新增 `frontend/src/__tests__/app-theme.spec.ts`：
     - 默认主题移除 `data-theme`。
     - 护眼主题设置 `data-theme="eye-care"`。
     - 黑夜主题设置 `data-theme="dark"`。
     - 非法 localStorage 值回退默认。
   - 如没有合适 DOM 测试环境，至少测试纯函数：`isAppTheme`、读写回退逻辑。
   - 手动检查关键页面。

14. 执行报告
   - Claude Code 完成后覆盖写入 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
   - 报告必须包括：
     - 实际修改文件。
     - 全局主题如何存储、如何应用。
     - 画布哪些区域保持固定颜色。
     - 哪些硬编码颜色已清理，哪些暂未清理。
     - 验证命令与结果。
     - 与本计划的偏离和风险。

# Constraints

- 不要修改后端代码。
- 不要修改数据库、API、schema、service、repository。
- 不要新增依赖。
- 不要重写路由。
- 不要重写 `ProjectDetailPage`、`ChapterTree`、`ChapterEditor`、`WritingAidPanel`；仅允许围绕主题做小范围定向修改。
- 不要改变图谱和时间线的数据结构、拖拽保存逻辑、API 调用逻辑。
- 不要让关系图/时间线画布底色随全局主题改变。
- 不要一次性大规模重构所有页面 CSS。
- 不要格式化整个 `frontend/src`。
- 所有用户可见文案必须是简体中文。
- 保持 UTF-8。
- 不要提交本地数据、日志、临时文件、构建产物。

# Verification Commands

前端基础验证：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit
npm run build
```

手动联调：

```powershell
cd F:\zhangshu\frontend
npm run dev
```

建议检查页面：

- `/projects`
- `/projects/{projectId}`
- `/projects/{projectId}/characters`
- `/projects/{projectId}/settings`
- `/projects/{projectId}/clues`
- `/projects/{projectId}/graph`
- `/projects/{projectId}/timeline`

手动验收点：

- 切换“默认 / 护眼 / 黑夜”后，全局页面背景、面板、表单、弹窗、按钮颜色随之变化。
- 刷新页面后主题保持。
- 正文编辑区跟随全局主题，但字体、字号、行距、宽度、缩进等设置仍保留。
- 关系图画布底色和网格在三个主题下保持一致。
- 时间线中间画布底色和轨道视觉在三个主题下保持一致。
- 图谱/时间线的侧栏、工具栏、详情面板可以跟随全局主题。
- 移动端主题切换控件不遮挡主要操作。
- 深色模式下没有明显白色孤岛，至少高频页面不应出现大片纯白卡片。

# Acceptance Criteria

- 全局主题入口可见且可操作。
- 主题选择持久化到 localStorage。
- `document.documentElement` 正确应用或移除 `data-theme`。
- 护眼模式和黑夜模式对全局应用生效，而不是只影响正文编辑 textarea。
- 关系图画布核心底色、网格、节点默认底色不随主题改变。
- 时间线画布核心底色、轨道轴线、事件节点默认底色不随主题改变。
- 正文编辑器原有排版设置不丢失。
- 不破坏章节编辑、自动保存、图谱拖拽、时间线拖拽等已有功能。
- 前端 type-check/test/build 通过。
- Claude 执行报告写入 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。

# Risks and Watchpoints

- 当前全局 theme token 已存在，但未被应用。只改 CSS 不改 `data-theme` 应用逻辑会无法生效。
- `ChapterEditor` 当前把主题作为编辑器局部设置保存。迁移时要兼容旧 storage，避免读取旧数据时报错。
- 全局黑夜模式会暴露大量硬编码浅色 CSS；本轮应优先处理关键页面，避免失控式 CSS 大重写。
- 画布使用全局 token 时会随主题改变，这与用户要求冲突。必须引入不随主题变化的 canvas token。
- 时间线不是 HTML canvas，但交互上是画布式工作区；需要纳入“画布不变色”的验收。
- `App.vue` 当前极简，修改时只加入主题入口，不要变成复杂布局壳。
- 固定画布颜色后，画布内浮层、节点文字、边线仍需可读；不要只固定背景而忽略对比度。
- 深色模式下浏览器原生 select/input 可能受 `color-scheme` 影响，必须检查表单可读性。
- 当前工作区未提交改动很多，Claude Code 不得回退或覆盖书籍档案、设定、伏笔、返回按钮等已有改动。

# Review Checklist

- 是否已读取 Claude 上一轮执行报告。
- 是否已归档旧 `CODEX_PLAN.md` 和 `CLAUDE_EXECUTION_REPORT.md`。
- 是否只修改前端主题/UI 相关文件。
- 是否没有修改后端/API/数据库。
- 是否新增应用级主题模块。
- 是否在 app mount 前应用了本地主题。
- 是否提供全局主题切换入口。
- 是否移除或迁移了正文编辑器的局部主题逻辑。
- 正文编辑器排版设置是否仍可用。
- `data-theme` 是否正确应用到 `document.documentElement`。
- 默认主题是否移除 `data-theme`。
- 关系图画布背景和网格是否在三个主题下保持一致。
- 时间线画布背景和轨道是否在三个主题下保持一致。
- 图谱和时间线的数据/拖拽/保存逻辑是否未被改动。
- 高频页面是否减少明显硬编码浅色。
- 深色模式下表单、弹窗、按钮、状态提示是否可读。
- 移动端主题入口是否不遮挡主要操作。
- 是否没有新增依赖。
- 前端 type-check/test/build 是否通过。
- 执行报告是否说明已采纳的额外 UI 建议和未处理项。
