---
archived_for_next_task: knowledge-vector-provider-upgrade
date: 2026-05-24
task: 知识库 UI 细节修正
codex_plan: docs/ai-handoff/CODEX_PLAN.md (knowledge UI polish)
---

## Task Summary
修复刷新索引弹窗贴边、新增真实进度条、将资料编辑区改为正文优先布局（元信息折叠到二级菜单）、统一检索/问答/摘要子模块横向间距。

## Files Changed

### 修改
- `frontend/src/features/knowledge/KnowledgeIndexRefreshDialog.vue` — 修复 padding（移除不存在的 `--zs-space-md`/`--zs-space-sm`/`--zs-space-lg`/`--zs-space-xs` 改用有效 token）、新增进度条和进度状态、改为 source scope 循环实现真实进度、刷新完成后保留结果页不自动关闭
- `frontend/src/pages/knowledge/ProjectKnowledgePage.vue` — `handleRefreshed()` 不再关闭弹窗；表单重构为正文优先（标题 → 正文 → 资料信息 details → 操作按钮）；元信息移入 `<details>` 折叠菜单；正文 textarea 放大至 `rows="18"` + `min-height: clamp(360px, 52vh, 720px)`；三个子模块（检索/问答/摘要）包裹在 `.knowledge-mode-panel` 统一容器

### 未修改
- 后端代码全部未改动
- 三个子组件内部（KnowledgeSearchPanel、KnowledgeAskPanel、KnowledgeSummaryPanel）未修改
- RAG / AI 总结 / 向量检索核心逻辑未触碰

## Implementation Notes

### 1. 刷新弹窗贴边修复
- 原因：`.refresh-body` 的 `padding` 使用了项目未定义的 token `--zs-space-md`，fallback 为 `16px 0`，横向 padding 为 `0`
- 修复：`padding: var(--zs-space-4) var(--zs-space-5);`（16px 20px），所有无效 token 替换为项目已有的 `--zs-space-1` ~ `--zs-space-8`
- 新增移动端适配 `@media (max-width: 560px)` 减小横向 padding

### 2. 真实进度条
- 项目级刷新：先调用 `listKnowledgeSources(projectId)` 获取未筛选的完整资料列表，然后对每条资料顺序调用 `refreshKnowledgeIndex({ scope: 'source', source_id, chunk_size })`
- 每完成一条资料：`completed += 1`，累加 `chunk_count`、`indexed_count`，合并 `warnings`，更新 `currentTitle`
- 资料级刷新：单条资料，`total = 1`，一次调用完成
- 进度条使用 `role="progressbar"` 和 `aria-valuenow` 实现无障碍支持
- 进度条样式使用设计 token（`--zs-color-border` 背景，`--zs-color-primary` 填充），支持所有主题

### 3. 完成后保留结果页
- `emit('refreshed')` 仅通知父组件刷新数据（索引状态、片段列表、资料列表）
- 父组件 `handleRefreshed()` 不再执行 `isRefreshDialogOpen.value = false`
- 用户在结果页看到完成摘要和 warnings 后，点击"关闭"按钮关闭弹窗

### 4. 正文优先布局
- 字段顺序：标题 → 正文（放大） → 资料信息 details → 操作按钮
- 正文 textarea：`rows="18"` + `min-height: clamp(360px, 52vh, 720px)`，确保在常见分辨率下占主体
- 元信息 details：包含类型、状态、可信度、来源、作者、摘要、标签
- 新建资料时 details 默认展开（`:open="isCreating || undefined"`），编辑已有资料时默认收起
- 保存逻辑不变，所有字段仍在 form reactive 中

### 5. 子模块统一布局
- 新增 `.knowledge-mode-panel`：`max-width: 1480px; width: 100%; margin: 0 auto;`
- 三个子模块（search/ask/summary）和"返回资料列表"按钮统一在此容器内
- `.view-back` 移除独立 `max-width`，由父容器控制
- 不需要修改三个子组件内部样式（全局已有 `* { box-sizing: border-box }`）

## Deviations from Codex Plan
无。完全按照 Codex Plan 实现。

## Verification Commands Run
- `npm run type-check` → ✅
- `npm run test:unit -- --run` → ✅ 80 passed
- `npm run build` → ✅

## Verification Results
全部通过。后端无改动，不需要运行后端测试。

## Known Issues
无。

## Suggested Next Review Points for Codex
1. 进度条动画过渡时间（0.3s）是否合适
2. `knowledge-content-textarea` 的 `clamp(360px, 52vh, 720px)` 在不同分辨率下的表现
3. 新建资料时 details 默认展开 vs 编辑时默认收起的体验是否合理
4. `.knowledge-mode-panel` 是否需要额外的 padding 或 margin
