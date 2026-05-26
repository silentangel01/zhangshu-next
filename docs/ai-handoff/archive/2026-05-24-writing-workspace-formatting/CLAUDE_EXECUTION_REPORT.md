---
archived_for_next_task: knowledge-index-refresh-ui
date: 2026-05-24
task: 写作工作区排版体验升级
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

将写作工作区正文编辑器的排版体验进行全面升级：首行缩进改为空格数规则（0/2/4 空格），行间距改为 0.5 的整数倍（1/1.5/2/2.5/3），新增独立的段落间距规则（0/1/2 空行），新增排版布局对齐方式（左/居中/右/两端对齐），新增用户点击触发的"自动排版"功能及撤销支持。行间距、首行缩进、段落间距移入"更多设置"。

## Files Changed

- 新增：`frontend/src/features/chapters/chapterFormatting.ts` — 排版纯函数模块
- 新增：`frontend/src/__tests__/chapter-formatting.spec.ts` — 29 个排版规则单元测试
- 修改：`frontend/src/features/chapters/ChapterEditor.vue` — 类型重构、工具栏重组、对齐控件、自动排版+撤销、CSS

## Implementation Notes

### 排版纯函数（chapterFormatting.ts）

独立纯函数模块，导出 `formatChapterContent(content, options)` 和类型定义。

规则：
1. 统一 `\r\n`、`\r` 为 `\n`
2. 移除每行行尾空白
3. 移除文档首尾空行
4. 每个非空段落移除已有前导空白（半角空格、tab、全角空格 `　`），再按设置重新加入缩进
5. 空行不添加缩进
6. 段落间距：在相邻非空行之间插入 0/1/2 个空行
7. 连续多个空行收敛为用户设置的段落间距
8. 不合并连续非空行（保留网络小说一行一段的正文习惯）
9. 文件末尾不保留多余空白

### 首行缩进为何以正文规则实现而非 CSS

`<textarea>` 的 CSS `text-indent` 无法可靠表达"每个段落第一行缩进"：
- `text-indent` 在 `<textarea>` 中只作用于整个文本块的开头，不逐段生效
- 即使 `text-indent` 配合 `white-space: pre-wrap` 在某些浏览器中表现不同，也无法稳定保证每段首行缩进

因此，首行缩进只能通过"自动排版"将空格写入正文内容实现。

### 段落间距为何以空行规则实现而非 CSS

纯文本 `<textarea>` 没有段落级 DOM 结构，无法应用 CSS `margin-top`、`padding-top` 等段落级样式。唯一的实现方式是通过自动排版在正文中插入空行来产生视觉段落间距。

旧的 `paragraphSpacing: 'comfortable'` 实现用 `paddingBlock` 改变编辑器整体内边距，不是真正的段落间距，已移除。

### 编辑器设置类型变更

| 旧字段 | 新字段 | 旧类型/默认 | 新类型/默认 |
|---|---|---|---|
| `firstLineIndent` | `firstLineIndentSpaces` | `'none' \| '2em'` / `'none'` | `0 \| 2 \| 4` / `0` |
| `lineHeight` | `lineHeight` | `'1.4' \| '1.6' \| '1.8' \| '2.0'` / `'1.8'` | `1.0 \| 1.5 \| 2.0 \| 2.5 \| 3.0` / `1.0` |
| `paragraphSpacing` | `paragraphSpacingLines` | `'normal' \| 'comfortable'` / `'normal'` | `0 \| 1 \| 2` / `0` |
| （无） | `textAlign` | — | `'left' \| 'center' \| 'right' \| 'justify'` / `'left'` |

保留字段：`selectedFontPreset`、`customFontFamily`、`fontSize`、`editorWidth`、`theme`

### 旧 localStorage 兼容

`readEditorAppearanceSettings()` 处理旧字段迁移：
- 旧 `firstLineIndent === '2em'` → `firstLineIndentSpaces: 2`
- 旧 `lineHeight` 为 `'1.4'` 或 `'1.6'` → `1.5`
- 旧 `lineHeight` 为 `'1.8'` 或 `'2.0'` → `2.0`
- 旧 `paragraphSpacing === 'comfortable'` → `paragraphSpacingLines: 1`
- 旧 `paragraphSpacing === 'normal'` → `paragraphSpacingLines: 0`
- 不覆盖用户已有的字体、字号、宽度设置

### editorStyle 变更

移除：
- `textIndent`（不再通过 CSS 伪缩进）
- `paddingBlock`（不再用编辑器 padding 冒充段落间距）

保留：
- `fontFamily`、`fontSize`、`lineHeight`

新增：
- `textAlign`（对齐方式为显示偏好，不写入正文）

### 工具栏信息架构

顶部保留/新增：
- 字号、宽度、对齐方式（按钮组：左/中/右/齐）、自动排版、撤销排版（条件显示）、更多设置、保存

移入"更多设置"：
- 行间距（1/1.5/2/2.5/3）
- 首行缩进（无/2 空格/4 空格）
- 段落间距（无空行/1 空行/2 空行）
- 字体
- 自定义字体名称

### 自动排版实现

- 点击"自动排版"按钮调用 `formatChapterContent(localContent, options)`
- 排版前保存撤销快照（`FormatUndoSnapshot`：content + selectionStart + selectionEnd + createdAt）
- 排版后：取消 pending autosave、设置 `skipNextAutosaveForAutoFormat` 标记、更新 `localContent`、保存本地恢复稿、标记 dirty
- 自动排版不调用 `updateChapter()`，不立即保存到后端
- 如果内容无需变化，显示"内容无需排版，未做更改"

### 撤销排版实现

- 排版后显示"撤销排版"按钮（`formatUndoSnapshot` 非 null 时）
- 点击撤销：取消 pending autosave、恢复快照内容和光标位置、保存恢复稿、清空快照
- 撤销后内容变为排版前状态，2 秒后自动保存恢复

### 自动保存行为调整

新增 `skipNextAutosaveForAutoFormat` 标记：
- 自动排版触发 `localContent` 变化时，watcher 仍然执行（保存恢复稿、设 dirty），但 `scheduleAutosave()` 检测到标记后跳过本次调度
- 标记在使用后自动清除
- 用户后续手动输入时，自动保存恢复原逻辑
- 撤销排版时标记已为 false，所以撤销后的内容变化会正常触发 2 秒自动保存

### 撤销快照清除时机

`clearFormattingUndo()` 在以下场景调用，避免撤销覆盖后续编辑：
- 切换章节（`applyLoadedChapter`）
- 保存成功（`saveCurrentContent`）
- 恢复草稿（`restorePendingDraftToEditor`）
- 用户手动输入（`handleEditorInput`，通过 `@input` 事件触发）

注意：`@input` 事件只在用户实际输入时触发，v-model 的程序化更新不触发 `@input`，因此自动排版和撤销排版的 `localContent` 变更不会意外清除撤销快照。

### 两端对齐浏览器限制

`<textarea>` 的 `text-align: justify` 在主流浏览器中表现有限：
- Chrome/Edge：justify 对 `<textarea>` 基本无效，渲染为左对齐
- Firefox：同上

保留 `justify` 选项以保持设置完整性，用户可在其他编辑器中使用 justify 对齐。执行报告中如实记录此限制。

### 对齐方式实现

使用按钮组（`.align-group`）而非 `<select>`，四个按钮分别为"左""中""右""齐"。当前选中按钮高亮（`.active` 类）。对齐方式作为编辑器显示偏好存入 localStorage，通过 `editorStyle.textAlign` 应用到 textarea，不写入章节正文。

### 样式

新增 CSS：
- `.align-group`：inline-flex 按钮组，使用 `--zs-color-border-soft` 分隔、`--zs-color-primary-soft` + `--zs-color-primary` 高亮
- `.format-message`：`--zs-color-info` 颜色，用于自动排版提示

所有样式使用设计 token，无硬编码主题色。

## Deviations from Codex Plan

无。

## Verification Commands Run

- `npm run type-check` → ✅
- `npm run test:unit -- --run` → ✅ 80 passed（原 51 + 新增 29）
- `npm run build` → ✅

## Verification Results

所有验证命令通过，无错误。新增 29 个排版纯函数测试全部通过。

## UI Polish: 对齐方式按钮改用 Word 风格图标

### 问题

用户反馈：对齐方式按钮组使用文字标签"左""中""右""齐"，不够直观，希望改为 Word 风格的图标。

### 修复

将四个文字按钮替换为内联 SVG 图标，模拟 Word 的对齐图标风格：

- **左对齐**：四行水平线，左端对齐，长度不等（全宽、短、中、更短）
- **居中**：四行水平线，居中对齐，长度不等
- **右对齐**：四行水平线，右端对齐，长度不等
- **两端对齐**：前三行等宽（满宽），末行较短

SVG 图标使用 `fill="currentColor"`，自动跟随按钮的 `color` 属性，与主题颜色协调。

### CSS 调整

`.align-group button` 新增 `display: inline-flex; align-items: center; justify-content: center`，移除文字专用的 `font-size` 和 `font-weight`，`min-width` 从 28px 调整为 30px 以容纳图标。

### 验证

- `npm run type-check` → ✅
- `npm run build` → ✅

## Feature: 知识库导入支持 .doc 格式

### 背景

用户反馈：大量素材文档仍为旧版 .doc 格式（Word 97-2003 二进制格式），不可能强制用户转换格式。需要将 .doc 从"可识别但不支持"升级为正式支持。

### 实现方案

新增 `extract_doc_text()` 函数到 `document_text_extractors.py`，使用 `olefile` 库（纯 Python、轻量）解析 OLE2 复合文档结构：

1. 验证 OLE2 签名（`D0CF11E0A1B11AE1`）
2. 使用 `olefile.OleFileIO` 读取 OLE2 容器
3. 提取 `WordDocument` 流
4. 解析 FIB（File Information Block）获取 `fcClx`/`lcbClx`
5. 从 `0Table` 或 `1Table` 流中读取 CLX，定位 piece table
6. 遍历 piece table，根据 PCD 中的 `fCompressed` 标志判断编码：
   - `fCompressed=1`：CP1252（单字节）
   - `fCompressed=0`：UTF-16LE（双字节，中文文档常用）
7. 解码文本并清理 Word 专用控制字符
8. 如果 FIB/piece table 解析失败，回退到流扫描启发式方法

### 文件变更

- 修改：`backend/app/utils/document_text_extractors.py` — 新增 `extract_doc_text()` 及辅助函数
- 修改：`backend/app/utils/import_parsers.py` — `.doc` 加入 `KNOWLEDGE_SUPPORTED_SUFFIXES`，移除 unsupported 分支，新增 .doc 解析调用
- 修改：`backend/requirements.txt` — 新增 `olefile>=0.47`
- 修改：`backend/tests/test_knowledge_import.py` — 重写 `TestDocFormat` 测试（3 个新测试），更新 zip 中 .doc 测试
- 修改：`frontend/src/features/knowledge/KnowledgeImportDialog.vue` — `supportedFileCount` 加入 `.doc`，更新帮助文案，移除 .doc unsupported 提示

### 依赖

新增 `olefile>=0.47`（纯 Python OLE2 解析库，约 100KB，无 C 扩展依赖）。

### 限制

- 仅支持标准 Word 97-2003 二进制格式（.doc）
- 加密或密码保护的 .doc 文件无法提取
- 复杂排版（表格、嵌入图片等）仅提取纯文本
- 极端损坏的文件可能触发回退扫描，结果不完整

### 验证

- `pytest tests/test_knowledge_import.py` → ✅ 33 passed（含 3 个 .doc 测试）
- `pytest` → ✅ 174 passed
- `npm run type-check` → ✅
- `npm run build` → ✅

## Known Issues

1. `<textarea>` 的 `text-align: justify` 在主流浏览器中基本无效（Chrome/Edge/Firefox 均渲染为左对齐）。这是 `<textarea>` 元素的原生限制，非代码 bug。保留选项供未来编辑器架构升级时使用。
2. 自动排版以"非空行"为段落单位。如果用户在一行内写了多个段落（用特殊分隔符），自动排版无法识别。当前阶段适合网络小说一行一段的写作习惯。
3. 自动排版后的撤销快照只保存最近一次。多次排版只保留最后一次快照。
4. .doc 解析依赖 FIB + piece table 结构。对于极少数非标准或严重损坏的 .doc 文件，会回退到流扫描启发式方法，提取结果可能不完整。加密 .doc 文件无法提取文本。

## Suggested Next Review Points for Codex

1. 自动排版的段落识别规则是否需要扩展（如识别 Markdown 标题、列表等）。
2. 是否需要将排版规则做成用户可配置（如自定义缩进字符：全角空格 vs 半角空格）。
3. 两端对齐在 textarea 中无效，是否需要移除该选项或添加说明。
4. 撤销快照是否需要支持多次（栈式撤销）。
