<!-- Archived before planning knowledge-index-refresh-ui on 2026-05-24. -->

# Task Summary

规划写作工作区正文编辑器的排版体验调整。本任务包括：

1. 将首行缩进改为“空格数”规则，并确保只作用于每个段落的第一行；该设置移入“更多设置”。
2. 将行间距改为 0.5 的整数倍，默认 1 倍行距；并将行间距移入“更多设置”。
3. 新增独立的段落间距规则，并移入“更多设置”。
4. 新增排版布局功能：左对齐、居中对齐、右对齐、两端对齐。
5. 新增“自动排版”功能：基于规则处理用户导入或编辑的纯文本内容；必须由用户点击触发，不自动触发，并支持撤销。

Codex 本轮未修改业务代码。本计划应由 Claude Code 执行。Claude Code 执行前应再次检查计划与实际代码是否冲突；如存在冲突，应停止并反馈，而不是强行实现。

# Current Codebase Findings

1. 已阅读 Claude Code 最新执行报告：
   - 上一任务为“知识库批量导入升级”。
   - Claude 已完成知识库批量文件/文件夹导入、PDF 解析、zip 导入、安全限制和 UI 热修。
   - 执行报告中还记录了一个写作工作区热修：`frontend/src/features/chapters/ChapterEditor.vue` 的 `.editor-textarea` 已补充 `background: var(--zs-color-surface)`，用于跟随护眼/黑夜主题。
2. 旧交接文件已归档到：
   - `docs/ai-handoff/archive/2026-05-24-knowledge-bulk-import/CODEX_PLAN.md`
   - `docs/ai-handoff/archive/2026-05-24-knowledge-bulk-import/CLAUDE_EXECUTION_REPORT.md`
3. 当前写作工作区核心文件：
   - 页面容器：`frontend/src/pages/projects/ProjectDetailPage.vue`
   - 正文编辑器：`frontend/src/features/chapters/ChapterEditor.vue`
   - 章节 API：`frontend/src/entities/chapter/api.ts`
   - 章节类型：`frontend/src/entities/chapter/types.ts`
   - 恢复草稿工具：`frontend/src/features/chapters/recoveryDraft.ts`
4. `ChapterEditor.vue` 当前使用纯文本 `<textarea>`：
   - `localContent` 保存编辑区正文。
   - `updateChapter()` 通过 `PATCH /api/chapters/{chapter_id}` 保存 `content`。
   - 本地恢复稿通过 `recoveryDraft.ts` 存入 localStorage。
   - 自动保存延迟约 2 秒触发。
5. 当前编辑器外观设置存储在 localStorage：
   - key：`zhangshu:editor:appearance`
   - 读取/写入工具：`safeReadJson`、`safeWriteJson`
   - 当前设置包含 `firstLineIndent`、`lineHeight`、`selectedFontPreset`、`customFontFamily`、`fontSize`、`editorWidth`、`paragraphSpacing`、`theme`
6. 当前首行缩进实现：
   - 类型：`FirstLineIndent = 'none' | '2em'`
   - 样式：`textIndent: '2em'`
   - 问题：`textarea` 的 `text-indent` 无法可靠表达“每个段落第一行缩进”，且单位是 `em`，不符合用户要求。
7. 当前行间距实现：
   - 类型：`EditorLineHeight = '1.4' | '1.6' | '1.8' | '2.0'`
   - 默认：`1.8`
   - 问题：不是 0.5 的整数倍，默认也不是 1 倍。
8. 当前段间距实现：
   - 类型：`ParagraphSpacing = 'normal' | 'comfortable'`
   - 实际只改变 `paddingBlock`，不是段落之间的独立间距。
9. 当前工具栏：
   - 顶部已有“字号、行距、首行缩进、宽度、更多设置、保存”。
   - `更多设置` 内已有字体、自定义字体名称、段间距。
10. 当前前端测试目录中没有 `ChapterEditor` 或排版规则相关测试。
11. 当前后端章节模型和 API 只存正文纯文本 `content`，没有段落样式、对齐方式或富文本结构字段。

# Architecture Decision

1. 本任务优先保持纯文本编辑器架构，不重写为富文本编辑器。
   - 不引入大型编辑器依赖。
   - 不改后端章节模型。
   - 不做数据库迁移。
   - 不改变现有章节保存、版本、恢复草稿机制。
2. 将排版能力分成两类：
   - 显示类设置：行间距、文字对齐、字体、字号、编辑区宽度。这些通过 CSS 影响编辑器显示，不直接修改正文内容。
   - 正文规则类设置：首行缩进空格数、段落间距空行数。这些必须通过用户点击“自动排版”后写入 `localContent`，因为纯文本 `textarea` 无法在不修改正文的情况下做到每个段落独立首行缩进和段间距。
3. 自动排版必须是显式操作：
   - 用户点击“自动排版”才执行。
   - 不在输入、粘贴、导入、切换章节或保存时自动触发。
   - 执行后只改变当前编辑框内容，不立即调用后端保存。
   - 需要提供“撤销排版”按钮，至少支持撤销最近一次自动排版。
4. 自动排版规则应拆到独立纯函数文件，避免把复杂文本处理堆进 `ChapterEditor.vue`。
5. `ChapterEditor.vue` 只负责：
   - 读取和保存外观/排版设置。
   - 调用排版纯函数。
   - 管理排版撤销快照。
   - 继续使用现有保存、自动保存、恢复草稿流程。
6. 本任务不新增后端 API。
7. 本任务不新增 AI、RAG、向量检索、知识图谱或外部模型调用。自动排版必须是规则驱动。

# Files to Create or Modify

建议新增：

- `frontend/src/features/chapters/chapterFormatting.ts`
- `frontend/src/__tests__/chapter-formatting.spec.ts`

建议修改：

- `frontend/src/features/chapters/ChapterEditor.vue`

不建议修改：

- `backend/app/models/chapter.py`
- `backend/app/schemas/chapter.py`
- `backend/app/services/chapter_service.py`
- `backend/app/api/chapters.py`
- `frontend/src/pages/projects/ProjectDetailPage.vue`
- `frontend/src/entities/chapter/api.ts`
- `frontend/src/entities/chapter/types.ts`
- `frontend/src/features/chapters/recoveryDraft.ts`

执行完成后必须创建：

- `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`

# Implementation Steps for Claude Code

1. 执行前检查
   - 阅读本计划。
   - 执行 `git status --short`，确认当前工作区中是否已有未提交的 `ChapterEditor.vue` 修改。
   - 当前已有的 `ChapterEditor.vue` 改动可能来自上一轮 Claude 热修，不要回滚。
   - 不要修改后端章节 API、模型、schema 或数据库。
   - 不要引入富文本编辑器、大型 UI 库或新的第三方依赖。

2. 新增排版纯函数模块
   - 新增 `frontend/src/features/chapters/chapterFormatting.ts`。
   - 建议定义类型：

```ts
export type FirstLineIndentSpaces = 0 | 2 | 4
export type ParagraphSpacingLines = 0 | 1 | 2

export interface ChapterFormatOptions {
  firstLineIndentSpaces: FirstLineIndentSpaces
  paragraphSpacingLines: ParagraphSpacingLines
}

export interface ChapterFormatResult {
  content: string
  changed: boolean
  paragraphCount: number
  changes: string[]
}
```

   - 建议导出：

```ts
export function formatChapterContent(content: string, options: ChapterFormatOptions): ChapterFormatResult
```

3. 自动排版规则
   - `formatChapterContent()` 必须只处理字符串，不访问 DOM、不调用 API、不读写 localStorage。
   - 基础规则：
     - 将 `\r\n`、`\r` 统一为 `\n`。
     - 移除每行行尾空白。
     - 将连续 3 个及以上空行收敛为用户设置的段落间距。
     - 每个非空段落只在第一行开头加入首行缩进空格。
     - 应先移除段落开头已有的半角空格、tab、全角空格，再按设置重新加入空格，避免重复缩进。
     - 空行不添加缩进。
     - 文件末尾保留最多一个换行，不制造多余空白。
   - 段落识别建议：
     - 当前阶段以“非空行”为段落单位，适合网络小说一行一段的正文习惯。
     - 不要默认把连续非空行合并为一个段落，避免误伤对话、诗歌、列表或特殊排版。
   - `paragraphSpacingLines` 含义：
     - `0`：段落之间不额外插入空行。
     - `1`：段落之间保留 1 个空行。
     - `2`：段落之间保留 2 个空行。
   - `firstLineIndentSpaces` 含义：
     - `0`：不缩进。
     - `2`：每个非空段落开头 2 个半角空格。
     - `4`：每个非空段落开头 4 个半角空格。

4. 调整编辑器设置类型
   - 修改 `ChapterEditor.vue` 中的类型：
     - `FirstLineIndent` 改为或替换为 `FirstLineIndentSpaces = 0 | 2 | 4`
     - `EditorLineHeight = '1.0' | '1.5' | '2.0' | '2.5' | '3.0'`
     - `ParagraphSpacing = 0 | 1 | 2`
     - 新增 `EditorTextAlign = 'left' | 'center' | 'right' | 'justify'`
   - `EditorAppearanceSettings` 建议字段：
     - `firstLineIndentSpaces`
     - `lineHeight`
     - `paragraphSpacingLines`
     - `textAlign`
     - 保留现有 `selectedFontPreset`、`customFontFamily`、`fontSize`、`editorWidth`、`theme`
   - 默认值：
     - `firstLineIndentSpaces: 0`
     - `lineHeight: '1.0'`
     - `paragraphSpacingLines: 0`
     - `textAlign: 'left'`

5. 兼容旧 localStorage 设置
   - 修改 `readEditorAppearanceSettings()`，兼容旧字段：
     - 旧 `firstLineIndent === '2em'` 可迁移为 `firstLineIndentSpaces: 2`。
     - 旧 `lineHeight`：
       - `1.4`、`1.6` 迁移为 `1.5`
       - `1.8`、`2.0` 迁移为 `2.0`
       - 缺失或非法值使用默认 `1.0`
     - 旧 `paragraphSpacing === 'comfortable'` 可迁移为 `paragraphSpacingLines: 1`。
     - 旧 `paragraphSpacing === 'normal'` 可迁移为 `paragraphSpacingLines: 0`。
   - 不要清空用户已有字体、字号、宽度设置。

6. 调整 editorStyle
   - 从 `editorStyle` 移除 `textIndent`。
   - 保留：
     - `fontFamily`
     - `fontSize`
     - `lineHeight`
   - 新增：
     - `textAlign: appearanceSettings.value.textAlign`
   - 不要通过 CSS 伪造每段首行缩进；首行缩进只能由自动排版规则写入正文。
   - 不要再用 `paragraphSpacing` 改 `paddingBlock` 来冒充段落间距。编辑器整体 padding 保持现有 `.editor-textarea { padding: 20px; }` 即可。

7. 调整工具栏信息架构
   - 顶部可保留常用项：
     - 字号
     - 宽度
     - 对齐方式
     - 自动排版
     - 保存
   - 将以下项移入 `更多设置`：
     - 行间距
     - 首行缩进
     - 段落间距
     - 字体
     - 自定义字体名称
   - `行间距` 选项：
     - `1`
     - `1.5`
     - `2`
     - `2.5`
     - `3`
   - `首行缩进` 选项：
     - `无`
     - `2 空格`
     - `4 空格`
   - `段落间距` 选项：
     - `无空行`
     - `1 空行`
     - `2 空行`

8. 新增排版布局控件
   - 在 `ChapterEditor.vue` 的 `writing-toolbar` 中新增对齐方式控件。
   - 对齐方式包括：
     - `左对齐` -> `textAlign: 'left'`
     - `居中` -> `textAlign: 'center'`
     - `右对齐` -> `textAlign: 'right'`
     - `两端对齐` -> `textAlign: 'justify'`
   - 建议使用一组小按钮或 segmented control，不新增图标依赖。
   - 当前纯文本架构下，对齐方式只作为编辑器显示偏好存入 localStorage，不写入章节正文，不改后端。
   - 如果 `textarea` 对 `justify` 表现有限，仍应保留该选项；执行报告中说明浏览器表现限制。

9. 新增自动排版按钮
   - 在 `writing-toolbar` 中新增按钮：
     - 文案：`自动排版`
   - 点击后调用 `formatChapterContent(localContent.value, options)`。
   - options 来自：
     - `appearanceSettings.firstLineIndentSpaces`
     - `appearanceSettings.paragraphSpacingLines`
   - 如果内容为空或没有变化，显示简短提示，不修改 `localContent`。
   - 如果内容有变化：
     - 先保存撤销快照。
     - 取消当前 pending autosave。
     - 将 `localContent` 更新为格式化结果。
     - 保存本地恢复稿，避免浏览器关闭造成丢失。
     - 标记为 dirty。
     - 显示提示：`已自动排版，可撤销或保存。`
   - 自动排版本身不得调用 `updateChapter()`，不得立即保存到后端。

10. 支持撤销自动排版
   - 在 `ChapterEditor.vue` 中新增撤销快照，例如：

```ts
interface FormatUndoSnapshot {
  content: string
  selectionStart: number
  selectionEnd: number
  createdAt: number
}
```

   - 新增 `editorTextareaRef`，用于读取和恢复光标位置。
   - 点击“自动排版”前保存：
     - 当前 `localContent`
     - 当前 `selectionStart`
     - 当前 `selectionEnd`
   - 自动排版后显示按钮：
     - `撤销排版`
   - 点击 `撤销排版`：
     - 取消 pending autosave。
     - 恢复快照内容。
     - 恢复光标位置。
     - 保存本地恢复稿。
     - 清空撤销快照。
     - 显示提示：`已撤销本次自动排版。`
   - 用户手动输入、切换章节、保存成功、恢复草稿、忽略草稿时，应清空自动排版撤销快照，避免撤销覆盖后续编辑。

11. 避免自动排版被自动保存抢跑
   - 当前 `localContent` watcher 会自动安排 autosave。
   - 为支持“用户确认后再保存”的排版体验，建议增加一个局部标记，例如 `skipNextAutosaveForAutoFormat`。
   - 当自动排版或撤销排版触发 `localContent` 变化时：
     - 仍应保存本地恢复稿。
     - 仍应设置 dirty 状态。
     - 但不要立即安排 2 秒自动保存。
   - 用户之后继续手动输入时，自动保存恢复原逻辑。
   - 用户点击“保存”时正常保存。
   - 如果 Claude Code 判断不应改变自动保存行为，必须在执行报告中说明理由，并确保“撤销排版”在 autosave 后仍不会造成数据丢失。

12. 清理旧段间距实现
   - 移除或停用 `paddingBlock: appearanceSettings.value.paragraphSpacing === 'comfortable' ? '22px' : '16px'` 这类实现。
   - 段落间距应只由自动排版规则控制正文中的空行数。
   - 编辑器外壳的视觉 padding 继续使用 CSS 固定值，不与段落间距设置绑定。

13. 样式调整
   - 在 `ChapterEditor.vue` scoped style 中为对齐按钮组、自动排版提示、撤销排版按钮补充样式。
   - 使用现有 CSS token：
     - `--zs-space-*`
     - `--zs-color-*`
     - `--zs-radius-*`
     - `--zs-shadow-*`
   - 不要新增硬编码主题色。
   - 移动到更多设置后的控件在窄屏下不能溢出；保持现有 `@media (max-width: 720px)` 下菜单静态布局。

14. 测试纯函数
   - 新增 `frontend/src/__tests__/chapter-formatting.spec.ts`。
   - 至少覆盖：
     - 统一换行符。
     - 移除行尾空白。
     - 非空段落添加 2 空格缩进。
     - 已有缩进不会重复叠加。
     - 空行不添加缩进。
     - 段落间距 0/1/2 空行。
     - 连续 3 个以上空行收敛。
     - 不合并连续非空行。
     - 空内容不报错。

15. 可选组件测试
   - 如测试环境适合，可以补充 `ChapterEditor` 组件测试：
     - 默认行距为 `1.0`。
     - “更多设置”中存在行间距、首行缩进、段落间距。
     - 点击自动排版后出现“撤销排版”。
   - 如果组件测试成本过高，本任务至少必须保留纯函数测试。

16. 执行报告
   - 创建新的 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
   - 报告必须说明：
     - 修改了哪些文件。
     - 是否新增了 `chapterFormatting.ts`。
     - 自动排版具体规则。
     - 首行缩进为何以正文规则实现而非 CSS。
     - 段落间距为何以空行规则实现而非 CSS。
     - 撤销排版的实现方式。
     - 是否调整了自动保存行为。
     - 验证命令结果。

# Constraints

1. 不要修改后端业务代码、数据库模型、schema、迁移或 API。
2. 不要引入富文本编辑器、Markdown 编辑器或大型 UI 依赖。
3. 不要重写 `ProjectDetailPage.vue`、`ChapterTree.vue`、`WritingAidPanel.vue`。
4. 不要破坏现有保存、自动保存、版本历史、恢复草稿功能。
5. 不要在用户输入时自动排版。
6. 不要在用户粘贴内容时自动排版。
7. 自动排版必须由用户点击触发。
8. 自动排版必须支持撤销最近一次排版。
9. 用户可见 UI 文案必须为简体中文。
10. 代码标识符、文件名保持英文。
11. 不要把复杂文本处理逻辑写进 `ChapterEditor.vue`。
12. 不要将显示偏好写入章节正文，除非用户点击“自动排版”。
13. 不要改动知识库、设定、伏笔、人物、关系图、RAG、AI 相关模块。
14. 不要提交本地数据库、日志、临时文件或构建产物。

# Verification Commands

前端验证：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit -- --run
npm run build
```

手动检查：

```text
/projects/:projectId
选择一个章节
打开写作工作区
确认行间距、首行缩进、段落间距已移入“更多设置”
确认行间距选项为 1、1.5、2、2.5、3，默认 1
确认首行缩进选项为无、2 空格、4 空格
确认段落间距选项为无空行、1 空行、2 空行
确认对齐方式包含左对齐、居中、右对齐、两端对齐
输入多段正文，点击“自动排版”
确认每个非空段落第一行按设置加入空格
确认空行不被加入空格
确认段落间距按设置产生空行
确认不会自动触发排版
确认点击“撤销排版”可恢复排版前内容
确认自动排版后未立即保存到后端，用户点击保存后才保存
确认切换护眼/黑夜主题后编辑器背景仍跟随全局主题
```

# Acceptance Criteria

1. `CODEX_PLAN.md` 已由 Codex 写入，业务代码未由 Codex 修改。
2. Claude Code 执行后，行间距、首行缩进、段落间距位于“更多设置”中。
3. 行间距选项为 0.5 的整数倍，默认 1 倍。
4. 首行缩进以空格数为单位，不再使用 `2em`。
5. 首行缩进只通过自动排版作用于每个非空段落的第一行，不通过 CSS `text-indent` 冒充。
6. 段落间距作为独立规则存在，不再用编辑器 padding 冒充。
7. 对齐方式包含左对齐、居中、右对齐、两端对齐。
8. 自动排版必须由用户点击触发。
9. 自动排版不会立即调用保存接口。
10. 自动排版后可以撤销最近一次排版。
11. 手动输入、保存、切换章节、恢复草稿等流程不被破坏。
12. 复杂排版规则位于独立纯函数文件，并有单元测试覆盖。
13. `npm run type-check` 通过。
14. `npm run test:unit -- --run` 通过。
15. `npm run build` 通过。
16. Claude Code 创建 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md` 并记录执行结果。

# Risks and Watchpoints

1. 纯文本 `textarea` 无法像 Word 一样存储段落级样式；本任务不应为了这个需求重写富文本编辑器。
2. CSS `text-indent` 不适合本需求，因为它不能稳定表达每个段落第一行缩进。
3. 段落间距在纯文本中只能通过空行规则落入正文；如果未来要做真正的视觉段前/段后间距，需要另行规划编辑器架构升级。
4. 自动排版会修改正文内容，必须有撤销入口，且不应自动保存抢跑。
5. 如果用户在自动排版后继续手动编辑，应避免“撤销排版”覆盖用户后续输入。
6. 两端对齐在 `textarea` 中的浏览器表现可能有限，执行报告需说明实际效果。
7. 旧 localStorage 设置需要兼容，不能导致编辑器加载失败。
8. 当前 `frontend/src/features/chapters/ChapterEditor.vue` 已有来自上一轮任务的改动，Claude Code 不得回滚。
9. 不要将自动排版做成 AI 功能，本任务只做规则处理。
10. 不要影响章节版本创建逻辑。排版后的正文只有在用户保存或后续自动保存策略允许时才进入现有版本链路。

# Review Checklist

Codex 复审时应检查：

1. Claude 是否遵守本计划，没有修改后端章节模型、API 或数据库。
2. 是否新增了独立的排版纯函数模块，而不是把复杂规则堆进 `ChapterEditor.vue`。
3. 首行缩进是否改为空格数，并移入更多设置。
4. 是否移除了 `textIndent: '2em'` 这类旧实现。
5. 行间距是否为 1、1.5、2、2.5、3，默认是否为 1。
6. 段落间距是否作为独立规则存在。
7. 对齐方式是否包含左、居中、右、两端对齐。
8. 自动排版是否只在用户点击后触发。
9. 自动排版是否不会立即保存到后端。
10. 撤销排版是否能恢复最近一次排版前内容。
11. 撤销排版是否不会覆盖用户后续手动输入。
12. 现有保存、自动保存、恢复草稿、版本历史是否仍可用。
13. 单元测试是否覆盖排版规则。
14. 是否存在硬编码主题色或不符合设计 token 的样式。
15. 是否有不该提交的密钥、本地配置、临时文件、数据库或日志。
16. 最终建议应明确为 Accept、Minor Revision 或 Rework。
