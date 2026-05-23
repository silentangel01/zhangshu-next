<script setup lang="ts">
import { ref } from 'vue'

import { summarizeKnowledge } from '@/entities/knowledge/api'
import type {
  KnowledgeSearchMode,
  KnowledgeSummaryResponse,
} from '@/entities/knowledge/types'

const props = defineProps<{
  projectId: string
}>()

const emit = defineEmits<{
  selectSource: [sourceId: string]
}>()

const topic = ref('')
const isSummarizing = ref(false)
const errorMessage = ref('')
const summaryResult = ref<KnowledgeSummaryResponse | null>(null)
const searchMode = ref<KnowledgeSearchMode>('hybrid')

async function handleSummarize() {
  isSummarizing.value = true
  errorMessage.value = ''
  summaryResult.value = null

  try {
    summaryResult.value = await summarizeKnowledge(props.projectId, {
      topic: topic.value.trim() || undefined,
      mode: searchMode.value,
    })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '摘要生成失败，请稍后重试。'
  } finally {
    isSummarizing.value = false
  }
}
</script>

<template>
  <section class="search-panel">
    <header class="search-header">
      <h2>知识库摘要</h2>
      <p class="search-description">
        对知识库内容进行 AI 摘要。可指定主题方向聚焦摘要范围。
      </p>
    </header>

    <form class="search-form" @submit.prevent="handleSummarize">
      <div class="search-mode-toggle">
        <button
          type="button"
          class="mode-button"
          :class="{ active: searchMode === 'keyword' }"
          @click="searchMode = 'keyword'"
        >
          关键词
        </button>
        <button
          type="button"
          class="mode-button"
          :class="{ active: searchMode === 'semantic' }"
          @click="searchMode = 'semantic'"
        >
          语义
        </button>
        <button
          type="button"
          class="mode-button"
          :class="{ active: searchMode === 'hybrid' }"
          @click="searchMode = 'hybrid'"
        >
          混合
        </button>
      </div>

      <div class="search-input-group">
        <input
          v-model="topic"
          type="text"
          placeholder="可选：聚焦主题，例如：魔法体系的限制条件"
          :disabled="isSummarizing"
          @keyup.enter="handleSummarize"
        />
        <button type="submit" class="search-button" :disabled="isSummarizing">
          {{ isSummarizing ? '生成中...' : '生成摘要' }}
        </button>
      </div>
    </form>

    <div v-if="errorMessage" class="error-message" role="alert">
      {{ errorMessage }}
    </div>

    <div v-if="summaryResult" class="summary-results">
      <div class="ai-warning">
        ⚠ AI 摘要为草稿建议，不会自动写入设定或正文。
      </div>

      <div class="summary-section">
        <div class="summary-header">
          <h3 class="summary-title">摘要</h3>
          <span v-if="summaryResult.is_draft" class="draft-badge">草稿</span>
        </div>
        <div class="summary-content">
          <pre class="summary-text">{{ summaryResult.summary }}</pre>
        </div>
        <div class="summary-meta">
          <span class="model-badge">{{ summaryResult.model }}</span>
          <span class="sources-count">使用了 {{ summaryResult.sources_used }} 段内容</span>
        </div>
      </div>

      <div v-if="summaryResult.source_titles.length > 0" class="sources-section">
        <h3 class="sources-title">
          引用资料（{{ summaryResult.source_titles.length }} 篇）
        </h3>
        <ul class="sources-list">
          <li v-for="title in summaryResult.source_titles" :key="title" class="source-item">
            {{ title }}
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.search-panel {
  display: grid;
  gap: 16px;
  padding: 20px;
  background: var(--zs-color-surface);
  border-radius: 8px;
  border: 1px solid var(--zs-color-border);
}

.search-header h2 {
  margin: 0;
  font-size: 1.1rem;
  color: var(--zs-color-text);
}

.search-description {
  margin: 4px 0 0;
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
}

.search-form {
  display: grid;
  gap: 12px;
}

.search-mode-toggle {
  display: flex;
  gap: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  overflow: hidden;
  width: fit-content;
}

.mode-button {
  border: none;
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  font-weight: 600;
  padding: 5px 14px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.mode-button + .mode-button {
  border-left: 1px solid var(--zs-color-border);
}

.mode-button.active {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.mode-button:hover:not(.active) {
  background: var(--zs-color-bg);
}

.search-input-group {
  display: flex;
  gap: 8px;
}

.search-input-group input {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  font-size: 0.9rem;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.search-button {
  padding: 8px 20px;
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
}

.search-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.search-button:hover:not(:disabled) {
  background: var(--zs-color-primary-hover);
}

.error-message {
  padding: 10px 14px;
  background: var(--zs-color-danger-soft);
  border: 1px solid var(--zs-color-danger);
  border-radius: 6px;
  color: var(--zs-color-danger);
  font-size: 0.85rem;
}

.summary-results {
  display: grid;
  gap: 16px;
}

.ai-warning {
  padding: 10px 14px;
  background: var(--zs-color-warning-soft);
  border: 1px solid var(--zs-color-warning);
  border-radius: 6px;
  color: var(--zs-color-warning);
  font-size: 0.85rem;
  font-weight: 500;
}

.summary-section {
  padding: 16px;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  background: var(--zs-color-bg);
  display: grid;
  gap: 10px;
}

.summary-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.summary-title {
  margin: 0;
  font-size: 0.95rem;
  color: var(--zs-color-text);
}

.draft-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  background: var(--zs-color-warning-soft);
  color: var(--zs-color-warning);
}

.summary-content {
  padding: 12px 14px;
  background: var(--zs-color-surface);
  border-radius: 4px;
  border-left: 3px solid var(--zs-color-primary);
}

.summary-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 0.88rem;
  line-height: 1.7;
  color: var(--zs-color-text);
}

.summary-meta {
  display: flex;
  gap: 12px;
  align-items: center;
}

.model-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

.sources-count {
  font-size: 0.82rem;
  color: var(--zs-color-text-muted);
}

.sources-section {
  display: grid;
  gap: 10px;
}

.sources-title {
  margin: 0;
  font-size: 0.95rem;
  color: var(--zs-color-text);
}

.sources-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}

.source-item {
  padding: 8px 12px;
  background: var(--zs-color-bg);
  border: 1px solid var(--zs-color-border);
  border-radius: 4px;
  font-size: 0.85rem;
  color: var(--zs-color-text);
}
</style>
