<!-- Archived before planning writing-workspace-formatting on 2026-05-24. -->

# Task Summary

规划改进知识库导入方式：知识库应以“文件上传 / 文件夹批量导入”为主要使用路径，保留当前手动新建和 URL/来源字段作为补充。需要支持从文件夹内批量读取并上传多种文件格式，包括 `.docx`、`.doc`、`.pdf`、`.txt`、`.md`。Codex 本轮只写计划，不修改业务代码。本计划交由 Claude Code 执行。

# Current Codebase Findings

1. 已阅读 Claude Code 最新执行报告：
   - 上一任务为 `Knowledge UI Fix - 新建入口、布局收紧、主题修正`。
   - Claude 已修正知识库新建入口、布局空白和主题 token 问题。
   - 验证命令均通过，知识库相关文件无 `--zs-canvas-*` 和硬编码颜色匹配。
2. 旧交接文件已归档到：
   - `docs/ai-handoff/archive/2026-05-24-knowledge-ui-fix/CODEX_PLAN.md`
   - `docs/ai-handoff/archive/2026-05-24-knowledge-ui-fix/CLAUDE_EXECUTION_REPORT.md`
3. 当前知识库导入后端已存在：
   - `backend/app/api/knowledge.py`
   - `POST /api/projects/{project_id}/knowledge/import/preview`
   - `POST /api/projects/{project_id}/knowledge/import/confirm`
   - 两个接口均接收 `files: list[UploadFile]`
4. 当前知识库导入 service 已存在：
   - `backend/app/services/knowledge_import_service.py`
   - `preview_import()` 调用 `parse_knowledge_files()`
   - `confirm_import()` 将每个文档保存为一条 `KnowledgeSource`，并调用 `KnowledgeService.rebuild_chunks()`
5. 当前解析器在 `backend/app/utils/import_parsers.py`：
   - `SUPPORTED_TEXT_SUFFIXES = {".txt", ".md", ".docx"}`
   - `parse_knowledge_files()` 支持 `.txt`、`.md`、`.docx`
   - `.docx` 通过读取 `word/document.xml` 做基础段落提取
   - 不支持 `.doc`
   - 不支持 `.pdf`
   - 不支持 `.zip` 作为知识库文件夹导入
6. 当前前端导入弹窗：
   - `frontend/src/features/knowledge/KnowledgeImportDialog.vue`
   - 文件 input 已有 `multiple`
   - `ACCEPTED_TYPES = '.txt,.md,.docx'`
   - UI 文案是“选择文件”，没有突出“批量上传 / 文件夹导入”
   - 没有 `webkitdirectory` 文件夹选择入口
7. 当前知识库主页面：
   - `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`
   - Header 有“导入”和“新建资料”
   - 仍容易让用户理解成“单条手动资料 + URL 来源”为主流程，而不是“批量上传文件”为主流程。
8. 当前后端依赖：
   - `backend/requirements.txt` 中没有 PDF 或 `.doc` 解析库。
   - 已有 `python-multipart` 支持上传。
   - 新增文件解析库需要慎重，不能无理由引入大型依赖。

# Architecture Decision

1. 知识库的主入口应调整为“导入文件 / 文件夹”，手动新建资料保留为次要入口。
2. `source_uri` 只是“来源 / 原路径 / URL / 书名 / 出处”，不应让用户以为知识库资料必须是 URL。
3. 批量导入分两层支持：
   - 前端文件夹选择：通过浏览器 `webkitdirectory` 读取目录内文件，并保留 `webkitRelativePath`。
   - 后端 zip 导入：支持用户上传 `.zip`，后端解压并遍历内部文件，作为浏览器兼容 fallback。
4. 文件格式支持分阶段：
   - 必须支持：`.txt`、`.md`、`.docx`、`.pdf`
   - `.doc` 支持应采用“可识别但有限支持”的策略，因为旧 Word 二进制格式解析复杂。
   - 如果不新增依赖，`.doc` 只能标记为不支持并给出清晰提示。
   - 如果新增依赖，必须选择小而常用的解析方式，并在执行报告中说明理由。
5. PDF 解析建议使用独立 helper，不要把解析逻辑堆进 API 或 service。
6. 导入服务继续保持：
   - API 层只接收文件。
   - Service 层负责预览与确认导入。
   - Parser/helper 层负责格式识别和文本提取。
   - KnowledgeService 负责创建 source/chunk。
7. 本任务不改 RAG、向量、AI 问答和摘要逻辑。导入完成后是否自动生成向量索引应作为可选后续动作，不在本任务默认执行。

# Files to Create or Modify

后端建议修改：

- `backend/app/utils/import_parsers.py`
- `backend/app/services/knowledge_import_service.py`
- `backend/app/api/knowledge.py`
- `backend/app/schemas/knowledge.py`
- `backend/tests/test_knowledge_import.py`

如确实需要新增解析 helper，建议新增：

- `backend/app/utils/document_text_extractors.py`

如确实需要新增依赖，可能修改：

- `backend/requirements.txt`

前端建议修改：

- `frontend/src/features/knowledge/KnowledgeImportDialog.vue`
- `frontend/src/entities/knowledge/api.ts`
- `frontend/src/entities/knowledge/types.ts`
- `frontend/src/pages/knowledge/ProjectKnowledgePage.vue`

可选新增测试：

- `frontend/src/__tests__/knowledge-import.spec.ts`

执行完成后必须创建：

- `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`

# Implementation Steps for Claude Code

1. 执行前检查
   - 阅读本计划。
   - 执行 `git status --short`，记录工作区状态。
   - 不要修改 RAG、向量、AI 摘要、AI 问答逻辑。
   - 不要修改与知识库导入无关的业务模块。

2. 调整知识库主入口文案和信息架构
   - 在 `ProjectKnowledgePage.vue` 中将 header 主操作调整为：
     - 主按钮：`批量导入`
     - 次按钮：`新建空白资料`
   - `批量导入` 打开 `KnowledgeImportDialog`。
   - `新建空白资料` 调用现有 `handleNewSource()`。
   - 页面说明建议改为：
     - `知识库用于保存外部参考资料。推荐批量导入文件，也可以手动新建少量笔记。`
   - 空状态中优先展示：
     - `批量导入文件`
     - `新建空白资料`
   - 不要移除 `source_uri` 字段，只把前端 label 从“来源”调整为更清楚的 `来源 / 原路径 / URL`。

3. 升级导入弹窗入口
   - 修改 `KnowledgeImportDialog.vue`。
   - 将顶部说明改为：
     - `支持批量导入文件或选择文件夹。每个文件会生成一条知识资料，并自动分块。`
   - 提供两个主要选择入口：
     - `选择文件`
     - `选择文件夹`
   - `选择文件`：
     - `type="file"`
     - `multiple`
     - `accept=".txt,.md,.docx,.doc,.pdf,.zip"`
   - `选择文件夹`：
     - 使用浏览器支持的 `webkitdirectory` / `directory` 属性。
     - TypeScript 中可能需要为 input element 使用 `setAttribute('webkitdirectory', '')` 或类型断言，避免模板类型报错。
     - 读取文件时保留 `file.webkitRelativePath || file.name`。
   - 已选文件列表应显示：
     - 相对路径或文件名。
     - 文件大小。
     - 文件类型。
   - 文件列表较多时显示计数和可滚动列表：
     - `已选择 N 个文件，预计导入 M 个支持的文件`
   - 支持移除单个文件、清空全部。

4. 前端上传时保留文件夹相对路径
   - 修改 `frontend/src/entities/knowledge/api.ts`。
   - 在 `FormData.append('files', file, relativePathOrName)` 中传入第三个参数，确保后端 `UploadFile.filename` 能拿到相对路径。
   - 如果 `File` 上存在 `webkitRelativePath`，优先使用。
   - 需要定义 helper，例如：
     - `getUploadFilename(file: File): string`
   - 保证普通文件上传仍兼容。

5. 扩展前端类型
   - 修改 `frontend/src/entities/knowledge/types.ts`。
   - `KnowledgeImportDocument` 建议新增：
     - `relative_path?: string`
     - `extension?: string`
   - `KnowledgeImportPreview` 建议新增：
     - `supported_count`
     - `unsupported_count`
     - `total_size`
   - 如果后端暂不返回这些字段，前端不要强依赖；但建议本任务前后端同步。

6. 扩展后端支持格式列表
   - 修改 `backend/app/utils/import_parsers.py` 或新增 `document_text_extractors.py`。
   - 将知识库导入支持格式定义为独立常量，不要直接复用作品导入的 `SUPPORTED_TEXT_SUFFIXES`，例如：
     - `KNOWLEDGE_SUPPORTED_SUFFIXES = {".txt", ".md", ".docx", ".doc", ".pdf", ".zip"}`
   - 注意：作品导入和知识库导入场景不同，不要破坏作品导入。

7. 支持 PDF 文本提取
   - 推荐新增依赖：`pypdf`，理由：
     - 常见、轻量、纯 Python。
     - 用于基础 PDF 文本提取足够。
   - 修改 `backend/requirements.txt` 增加固定版本或合理范围，例如：
     - `pypdf>=5.0`
   - 在 parser helper 中实现：
     - `parse_pdf_text(content: bytes, filename: str, failed_files: list[str]) -> str | None`
   - PDF 解析失败时：
     - 加入 `failed_files`
     - warning 写清楚：`PDF 文本提取失败，可能是扫描版或加密文件。`
   - 不要支持 OCR；扫描版 PDF 本任务只提示无法提取。

8. 处理 `.doc` 旧 Word 格式
   - `.doc` 是旧二进制格式，不能像 `.docx` 一样直接 XML 解析。
   - 推荐本阶段策略：
     - 前端允许选择 `.doc`，让用户知道系统识别该格式。
     - 后端将 `.doc` 放入 `unsupported_files`，并给出明确 warning：
       - `暂不支持旧版 .doc，请先另存为 .docx 或 PDF 后导入。`
   - 如果 Claude Code 判断必须实现 `.doc` 解析，不要直接引入重型或平台依赖工具；需在执行报告中说明选型、依赖、Windows 可用性和失败模式。
   - 默认不要依赖 LibreOffice、antiword、COM 或系统 Word。

9. 支持 zip 文件夹导入
   - 在知识库导入 parser 中支持 `.zip`。
   - 上传 `.zip` 时：
     - 遍历内部文件。
     - 忽略目录、`.DS_Store`、`Thumbs.db`、隐藏系统文件。
     - 防止路径穿越：拒绝绝对路径和包含 `..` 的路径。
     - 保留 zip 内相对路径为 `source_uri`。
   - zip 内支持文件格式：
     - `.txt`
     - `.md`
     - `.docx`
     - `.pdf`
     - `.doc` 只记录 unsupported warning
   - zip 中每个支持文件生成一条 `KnowledgeSource`。
   - 如果 zip 内没有可导入文件，返回清楚 warning。

10. 后端 preview 结果增强
   - `parse_knowledge_files()` 返回更适合批量导入的 preview：
     - `documents`
     - `document_count`
     - `supported_count`
     - `unsupported_count`
     - `total_word_count`
     - `total_size`
     - `warnings`
     - `failed_files`
     - `empty_files`
     - `unsupported_files`
     - `can_import`
   - 每个 document 返回：
     - `title`
     - `content`
     - `source_type`
     - `source_uri`
     - `filename`
     - `relative_path`
     - `extension`
     - `word_count`
     - `size`
   - `source_uri` 对本地文件应保存相对路径或文件名，不应伪装成 URL。

11. 后端 confirm 导入增强
   - `KnowledgeImportService.confirm_import()` 使用 preview documents 创建 source。
   - 每个文件一条 source。
   - `source_uri` 写入相对路径。
   - `source_type` 默认应为 `file`，除非用户在导入选项中统一指定。
   - 继续自动 `rebuild_chunks()`。
   - 导入结果应显示：
     - 成功数。
     - 每条 source 的标题、路径、chunk 数。
     - unsupported/failed/empty 文件列表。

12. 文件大小和数量限制
   - 在 service 或 API 层加入基础限制，避免一次上传过大导致卡死。
   - 建议默认：
     - 单文件最大 25MB。
     - 单次最多 200 个文件。
     - 单次总大小最大 200MB。
   - 超过限制时返回 400，并给出中文错误。
   - 这些限制写成常量，便于未来调整。

13. 前端 preview UI 改进
   - 预览步骤中显示：
     - 可导入文件数。
     - 不支持文件数。
     - 空文件数。
     - 失败文件数。
     - 总字数。
   - 文件列表按相对路径展示，长路径省略但 hover/title 保留完整路径。
   - 对不支持格式单独展示，不要只藏在 warnings 中。
   - `.doc` 提示应清楚：
     - `旧版 .doc 暂不支持，请另存为 .docx 或 PDF。`
   - `.pdf` 提示：
     - `扫描版 PDF 可能无法提取文字。`

14. 知识库主页面减少“URL 资料”心智
   - `ProjectKnowledgePage.vue` 表单字段：
     - `来源` 改为 `来源 / 原路径 / URL`
     - placeholder 改为 `文件路径、网页链接、书名或出处`
   - 手动新建资料可以保留 `webpage` 类型，但不要把 URL 放在首要位置。
   - 资料类型排序建议：
     - `file`
     - `note`
     - `book`
     - `webpage`
     - `quote`
     - `custom`

15. 测试
   - 后端 `backend/tests/test_knowledge_import.py` 至少补充：
     - 批量 `.txt` + `.md` 导入。
     - `.docx` 导入。
     - `.pdf` 导入，如果引入 `pypdf`，可用最小 PDF fixture 或 mock extractor。
     - `.doc` 被归入 unsupported，并有 warning。
     - `.zip` 中多层目录批量导入。
     - zip 路径穿越被拒绝或记录 failed。
     - 文件夹相对路径能进入 `source_uri`。
     - 超过文件数量或大小限制返回错误。
   - 前端可选新增 `knowledge-import.spec.ts`，至少测试：
     - `getUploadFilename()` 使用 `webkitRelativePath`。
     - 文件选择后能显示多个文件。
     - 文件夹模式入口存在。

16. 执行报告
   - 创建新的 `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md`。
   - 报告必须说明：
     - 支持的格式。
     - `.doc` 最终策略。
     - 是否新增依赖及理由。
     - 文件夹导入实现方式。
     - zip 安全处理。
     - 文件大小/数量限制。
     - 验证命令结果。

# Constraints

1. 不要修改 RAG、向量检索、AI 问答、AI 摘要逻辑。
2. 不要把文件导入结果自动写入设定集或正文。
3. 不要让知识库导入影响作品导入流程。
4. 不要把解析逻辑写进 API router。
5. 不要依赖本机安装 Word、LibreOffice、antiword 或其他外部 GUI/系统程序。
6. 不要新增重型依赖；PDF 解析如需新增依赖，优先 `pypdf` 并说明理由。
7. `.doc` 如无法稳定支持，应明确提示用户另存为 `.docx` 或 PDF，不要假装支持。
8. 用户可见文案必须为简体中文。
9. 上传文件名和 zip 内路径必须防路径穿越。
10. 不要提交导入的测试文件、临时文件、数据库或日志。

# Verification Commands

后端：

```powershell
cd F:\zhangshu\backend
.\.venv\Scripts\Activate.ps1
pytest tests/test_knowledge_import.py
pytest
```

前端：

```powershell
cd F:\zhangshu\frontend
npm run type-check
npm run test:unit -- --run
npm run build
```

手动检查：

```text
/projects/:projectId/knowledge
点击“批量导入”
选择多个 txt/md/docx/pdf 文件
选择一个文件夹并保留相对路径
上传包含多层目录的 zip
上传 doc 文件，确认提示旧版 doc 暂不支持或按实际实现显示结果
上传扫描版 PDF，确认失败提示清楚
确认每个文件导入后生成独立知识资料
确认 source_uri 显示为文件路径/来源，而不是强制 URL 心智
```

# Acceptance Criteria

1. 知识库页面主操作以“批量导入”为主，“新建空白资料”为次。
2. 导入弹窗支持一次选择多个文件。
3. 导入弹窗支持选择文件夹，并保留文件夹相对路径。
4. 支持 `.txt`、`.md`、`.docx`、`.pdf` 导入。
5. `.doc` 有明确处理策略：稳定支持，或明确提示暂不支持并建议转换为 `.docx` / PDF。
6. 支持 `.zip` 文件夹导入，zip 内多层目录可批量解析。
7. 每个导入文件生成一条独立 `KnowledgeSource`。
8. 导入后自动生成 chunks。
9. 预览报告清楚显示成功、失败、空文件、不支持文件。
10. 文件数量和大小限制生效，并有中文错误提示。
11. 不破坏手动新建资料和当前 URL/来源字段。
12. 不影响作品导入功能。
13. 后端和前端验证命令通过。
14. `docs/ai-handoff/CLAUDE_EXECUTION_REPORT.md` 完整记录执行结果。

# Risks and Watchpoints

1. 用户提到“文件夹批量读取”，浏览器直接读取任意本地文件夹依赖 `webkitdirectory`，这是 Chromium 系浏览器常用能力但不是标准属性；需要保留 zip 导入 fallback。
2. `.doc` 旧格式解析稳定性差，不应为了“支持”引入平台依赖或脆弱实现。
3. PDF 文本提取不等于 OCR，扫描版 PDF 可能没有可提取文字。
4. 大量文件上传可能造成请求过大和前端卡顿，必须有数量/大小限制。
5. zip 解压必须防路径穿越。
6. `source_uri` 应保存来源路径，但不能被当作可访问 URL 使用。
7. 作品导入和知识库导入共用部分 parser helper，修改时要避免影响 `/imports`。
8. 如果新增 `pypdf`，需要确保安装、测试和打包流程都能接受。

# Review Checklist

Codex 复审时应检查：

1. 是否符合本计划，没有修改 RAG/AI/向量逻辑。
2. 是否将“批量导入文件/文件夹”作为知识库主入口。
3. 是否保留手动新建资料和 URL/来源字段作为补充。
4. 是否支持多文件上传。
5. 是否支持文件夹选择并保留相对路径。
6. 是否支持 `.txt`、`.md`、`.docx`、`.pdf`。
7. `.doc` 策略是否诚实、稳定、用户提示清楚。
8. zip 导入是否安全处理路径穿越和系统文件。
9. 是否每个文件生成独立知识资料并自动分块。
10. 是否没有破坏作品导入。
11. 是否新增不合理依赖。
12. 测试是否覆盖批量、文件夹、zip、pdf、doc、失败文件和限制。
13. 是否有不该提交的测试文件、上传文件、临时文件、数据库或日志。
14. 最终建议应明确为 Accept、Minor Revision 或 Rework。
