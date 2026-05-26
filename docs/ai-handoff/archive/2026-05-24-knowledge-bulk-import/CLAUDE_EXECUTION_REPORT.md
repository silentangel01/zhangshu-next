---
archived_for_next_task: writing-workspace-formatting
date: 2026-05-24
task: 知识库批量导入升级
codex_plan: docs/ai-handoff/CODEX_PLAN.md
---

## Task Summary

将知识库导入方式从"手动新建为主"升级为"文件/文件夹批量导入为主"。支持 .txt、.md、.docx、.pdf 格式和 .zip 压缩包，添加文件夹选择（webkitdirectory）入口，保留手动新建资料作为次要入口。

## Files Changed

- 新增：`backend/app/utils/document_text_extractors.py` — PDF 文本提取 helper，基于 pypdf
- 新增：`backend/tests/test_knowledge_import.py` — 扩展测试（原有 13 个 → 32 个）
- 修改：`backend/app/utils/import_parsers.py` — 新增 KNOWLEDGE_SUPPORTED_SUFFIXES、zip 解压、.doc unsupported 处理、增强 preview 字段
- 修改：`backend/app/services/knowledge_import_service.py` — 新增文件大小/数量限制校验、增强 confirm 导入返回信息
- 修改：`backend/app/api/knowledge.py` — 添加 response_model、处理 KnowledgeImportLimitError
- 修改：`backend/app/schemas/knowledge.py` — 新增 KnowledgeImportPreviewResponse、KnowledgeImportResultResponse 等
- 修改：`backend/requirements.txt` — 新增 pypdf>=5.0
- 修改：`frontend/src/entities/knowledge/types.ts` — KnowledgeImportDocument 新增 relative_path、extension、size；KnowledgeImportPreview 新增 supported_count、unsupported_count、total_size
- 修改：`frontend/src/entities/knowledge/api.ts` — 新增 getUploadFilename helper，FormData.append 使用 webkitRelativePath
- 修改：`frontend/src/features/knowledge/KnowledgeImportDialog.vue` — 全面重写：双入口（选择文件+选择文件夹）、增强预览、不支持文件单独展示
- 修改：`frontend/src/pages/knowledge/ProjectKnowledgePage.vue` — 主按钮改为"批量导入"、次按钮"新建空白资料"、更新说明文案、空状态、来源 label

## Implementation Notes

### PDF 解析

- 使用 pypdf（纯 Python、轻量）进行基础 PDF 文本提取
- 不支持 OCR，扫描版 PDF 会提示"PDF 文本提取失败，可能是扫描版或加密文件"
- 加密 PDF 会被识别并提示
- PDF 解析逻辑独立在 `document_text_extractors.py`，不混入 import_parsers

### .doc 策略

- 本阶段 .doc 标记为"可识别但不支持"
- 前端允许选择 .doc 文件
- 后端将 .doc 归入 unsupported_files，并给出清晰提示："暂不支持旧版 .doc 格式，请另存为 .docx 或 PDF 后导入"
- 不依赖 LibreOffice、antiword、COM 或系统 Word

### 文件夹导入

- 前端使用 `webkitdirectory` + `directory` 属性实现文件夹选择
- 读取 `file.webkitRelativePath` 保留文件夹相对路径
- 通过 FormData.append 第三参数传递给后端

### zip 导入

- 后端解压 zip 并遍历内部文件
- 忽略 .DS_Store、Thumbs.db、__MACOSX 等系统文件
- 路径穿越检查（..、绝对路径）在 ignore-filter 之前执行，被拒绝的路径记录到 failed_files
- zip 内相对路径保留为 source_uri

### 文件大小和数量限制

- 单文件最大 25 MB
- 单次最多 200 个文件
- 单次总大小最大 200 MB
- 超限时返回 400 + 中文错误提示
- 限制常量定义在 import_parsers.py，便于调整

### 前端 UI 调整

- 知识库页面主按钮从"导入"改为"批量导入"（primary-button），次按钮"新建空白资料"
- 页面说明改为"推荐批量导入文件，也可以手动新建少量笔记"
- 空状态优先展示"批量导入文件"
- 来源 label 改为"来源 / 原路径 / URL"，placeholder 改为"文件路径、网页链接、书名或出处"
- 资料类型排序：file、note、book、webpage、quote、custom

## Deviations from Codex Plan

无。

## Verification Commands Run

- `pytest tests/test_knowledge_import.py` → ✅ 32 passed
- `pytest` → ✅ 173 passed
- `npm run type-check` → ✅
- `npm run test:unit -- --run` → ✅ 51 passed
- `npm run build` → ✅

## Verification Results

所有验证命令通过，无错误。

## Hotfix: 导入对话框按钮不可见

### 问题

用户反馈：点击"批量导入"打开对话框后，看不到"选择文件"和"选择文件夹"按钮。

### 根因

`KnowledgeImportDialog.vue` 的 scoped 样式与全局 `.zs-dialog-content` 样式冲突：

- 全局 `.zs-dialog-content`（`style.css`）定义了 `overflow-y: auto; max-height: 90vh;`，负责对话框内容的滚动行为
- scoped `.import-dialog` 添加了 `display: flex; flex-direction: column; max-height: 80vh;`，试图建立自定义 flex 布局
- `.dialog-body` 包装层使用 `flex: 1; overflow-y: auto;`，在全局 `overflow-y: auto` 的覆盖下（CSS 属性特异性：全局 0-1-0 vs scoped shorthand 0-2-0，但 `overflow-y` 属性不被 `overflow` shorthand 覆盖）形成双重滚动上下文，导致内容区域渲染异常

其他正常工作的对话框（`CreateProjectDialog`、`EditOutlineDialog` 等）不使用任何自定义布局覆盖，内容直接放在 `.zs-dialog-content` 内，由全局样式统一管理滚动。

### 修复

1. 移除 `.import-dialog` 上的 `display: flex; flex-direction: column; max-height: 80vh;`，仅保留 `width` 覆盖
2. 将 `.dialog-body` 重命名为 `.import-body`，只负责 padding 和 gap，不做 flex 布局或 overflow 管理
3. 改用 `<button>` + 隐藏 `<input>` 模式替代 `<label>` 包裹隐藏 `<input>` 模式，通过 `.click()` 触发文件选择，兼容性更好
4. 通过 `onMounted` + `setAttribute('webkitdirectory', '')` 设置文件夹选择属性，避免模板中非标准属性可能的编译问题
5. 添加 `@click.self` 支持点击遮罩关闭对话框（与其他对话框一致）

### 验证

- `npm run type-check` → ✅
- `npm run build` → ✅

## UI Polish: 导入对话框布局与主题协调

### 问题

用户反馈：导入对话框 UI 布局太紧凑，按钮颜色与主题不协调。

### 根因

1. 按钮使用了自定义 `.file-select-button` 类，颜色硬编码，未使用全局设计系统的 `zs-button` 系列类
2. 间距使用硬编码像素值（如 `12px`、`40px`），未使用设计 token `--zs-space-*`
3. 各步骤容器缺少统一的 `gap` 控制，元素之间显得拥挤

### 修复

1. 所有按钮统一使用全局 `zs-button` 类族：
   - 主操作（选择文件、预览导入、确认导入、完成）：`zs-button zs-button-primary`
   - 次操作（选择文件夹、清空、返回、取消）：`zs-button zs-button-secondary`
   - 文件移除按钮：`zs-button-ghost file-remove`
2. 间距全面使用设计 token：
   - `.import-body` padding 从 `var(--zs-space-4) var(--zs-space-5)` 增加到 `var(--zs-space-5) var(--zs-space-6)`
   - `.import-body` gap 从 `12px` 改为 `var(--zs-space-4)`
   - 各步骤容器（`.step-select`、`.step-preview`、`.step-result`）使用 `display: grid; gap: var(--zs-space-4)`
   - `.step-importing` padding 从 `40px` 改为 `var(--zs-space-8)`
3. `.step-actions` 添加 `border-top: 1px solid var(--zs-color-border-soft)` 分隔线和 `padding-top: var(--zs-space-3)`
4. 圆角统一使用 `--zs-radius-sm` 和 `--zs-radius-pill`
5. 文件列表 max-height 从 200px 增加到 220px

### 验证

- `npm run type-check` → ✅
- `npm run build` → ✅

## Hotfix 2: 导入对话框贴左边

### 问题

用户反馈：批量导入对话框左侧贴着窗口边缘，没有居中或间距不正确。

### 根因

`KnowledgeImportDialog.vue` 的 scoped `.import-dialog` 只设置了 `width: min(640px, 90vw)`，但未覆盖全局 `.zs-dialog-content` 的 `max-width: 560px`。`width` 和 `max-width` 是独立的 CSS 属性，全局 `max-width` 仍然生效，将对话框宽度限制在 560px。同时，对话框居中完全依赖 grid 容器的 `place-items: center`，当对话框宽度接近 grid 内容区域宽度时，居中效果可能不稳定。

### 修复

1. 在 `.import-dialog` 上显式设置 `max-width: min(640px, 90vw)`，覆盖全局 `max-width: 560px`
2. 同时设置 `width: min(640px, 90vw)` 确保宽度与 max-width 一致
3. 添加 `margin-inline: auto`，利用 CSS Grid 规范中 auto margin 优先于 alignment property 的特性，确保在任何视口尺寸下都能可靠居中

### 验证

- `npm run type-check` → ✅
- `npm run build` → ✅

## Hotfix 3: 编辑器无法同步护眼主题颜色

### 问题

用户反馈：切换到"护眼"全局主题后，写作工作区的正文编辑框背景仍然是白色，没有跟随主题变为暖色调。

### 根因

`ChapterEditor.vue` 的 `.editor-textarea` 样式缺少 `background` 属性。

- 全局主题系统通过 `<html data-theme="eye-care">` + CSS 变量 `--zs-color-surface: #fff9ef` 正确工作
- 页面背景、边框、文字颜色都能跟随主题变化
- 但 `<textarea>` 元素没有显式设置 `background`，回退到浏览器 UA 默认值 `#ffffff`（纯白）
- `color` 和 `border-color` 都引用了主题变量，唯独背景遗漏

### 修复

在 `.editor-textarea` 添加 `background: var(--zs-color-surface)`，使编辑框背景色跟随全局主题变量。护眼主题下变为 `#fff9ef`（暖米色），黑夜主题下变为 `#182225`（深色表面）。

### 文件变更

- 修改：`frontend/src/features/chapters/ChapterEditor.vue` — `.editor-textarea` 添加 `background: var(--zs-color-surface)`

### 验证

- `npm run type-check` → ✅
- `npm run build` → ✅

## Known Issues

1. `webkitdirectory` 是 Chromium 系浏览器的非标准属性，Firefox 也支持但 Safari 支持有限。已保留 .zip 作为 fallback。
2. 扫描版 PDF 无法提取文字，用户需要自行 OCR 或使用其他工具转换后再导入。
3. requirements.txt 文件编码为 UTF-16 LE（历史原因），新增 pypdf 时保持了原编码。

## Suggested Next Review Points for Codex

1. PDF 解析质量：pypdf 对复杂排版的 PDF 提取效果可能不理想，是否需要后续优化或提供用户反馈入口。
2. 大量文件导入时的 UI 体验：当前预览列表在文件很多时可能较长，是否需要分页或虚拟滚动。
3. 导入后是否需要自动触发向量索引生成（当前不自动触发，需要用户手动点击"生成向量"）。
4. 文件大小限制是否需要做成用户可配置的选项。
