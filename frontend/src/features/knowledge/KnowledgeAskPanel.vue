<script setup lang="ts">
import { reactive, ref } from 'vue'

import { askKnowledgeBase } from '@/entities/knowledge/api'
import type {
  KnowledgeAskResponse,
  KnowledgeCredibility,
  KnowledgeSearchMode,
  KnowledgeSourceType,
  RagCitation,
} from '@/entities/knowledge/types'
import { knowledgeCredibilityLabels, knowledgeSourceTypeLabels } from '@/entities/knowledge/types'

const props = defineProps<{
  projectId: string
}>()

const emit = defineEmits<{
  selectSource: [sourceId: string]
}>()

const question = ref('')
const isAsking = ref(false)
const errorMessage = ref('')
const askResult = ref<KnowledgeAskResponse | null>(null)
const searchMode = ref<KnowledgeSearchMode>('hybrid')

const filters = reactive({
  source_type: '' as KnowledgeSourceType | '',
  credibility: '' as KnowledgeCredibility | '',
  top_k: 10,
})

const sourceTypes: KnowledgeSourceType[] = ['note', 'file', 'webpage', 'book', 'quote', 'custom']
const credibilities: KnowledgeCredibility[] = ['low', 'normal', 'high']

async function handleAsk() {
  if (!question.value.trim()) {
    errorMessage.value = '请输入问题'
    return
  }

  isAsking.value = true
  errorMessage.value = ''
  askResult.value = null

  try {
    askResult.value = await askKnowledgeBase(props.projectId, {
      question: question.value.trim(),
      mode: searchMode.value,
      source_type: filters.source_type || undefined,
      credibility: filters.credibility || undefined,
      top_k: filters.top_k,
    })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '问答请求失败，请稍后重试。'
  } finally {
    isAsking.value = false
  }
}

function handleClearFilters() {
  filters.source_type = ''
  filters.credibility = ''
  filters.top_k = 10
}

function handleSelectCitation(citation: RagCitation) {
  emit('selectSource', citation.source_id)
}

function formatScore(score: number | null | undefined): string {
  if (score == null) return ''
  return `${(score * 100).toFixed(0)}%`
}

function truncateContent(content: string, maxLength: number = 200): string {
  if (content.length <= maxLength) return content
  return `${content.slice(0, maxLength)}...`
}
</script>

<template>
  <section class="search-panel">
    <header class="search-header">
      <h2>知识库问答</h2>
      <p class="search-description">
        基于知识库内容回答问题。系统会检索相关分块并生成回答（含引用来源）。
      </p>
    </header>

    <form class="search-form" @submit.prevent="handleAsk">
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
          v-model="question"
          type="search"
          placeholder="输入你的问题，例如：魔法体系的构成要素有哪些？"
          :disabled="isAsking"
          @keyup.enter="handleAsk"
        />
        <button type="submit" class="search-button" :disabled="isAsking">
          {{ isAsking ? '生成中...' : '提问' }}
        </button>
      </div>

      <div class="search-filters">
        <label>
          <span>资料类型</span>
          <select v-model="filters.source_type">
            <option value="">全部类型</option>
            <option v-for="st in sourceTypes" :key="st" :value="st">
              {{ knowledgeSourceTypeLabels[st] }}
            </option>
          </select>
        </label>

        <label>
          <span>可信度</span>
          <select v-model="filters.credibility">
            <option value="">全部可信度</option>
            <option v-for="c in credibilities" :key="c" :value="c">
              {{ knowledgeCredibilityLabels[c] }}
            </option>
          </select>
        </label>

        <label>
          <span>引用数量</span>
          <select v-model.number="filters.top_k">
            <option :value="5">最多 5 条</option>
            <option :value="10">最多 10 条</option>
            <option :value="20">最多 20 条</option>
          </select>
        </label>

        <button type="button" class="clear-filters" @click="handleClearFilters">
          重置
        </button>
      </div>
    </form>

    <div v-if="errorMessage" class="error-message" role="alert">
      {{ errorMessage }}
    </div>

    <div v-if="askResult" class="ask-results">
      <div class="ai-warning">
        ⚠ AI 回答仅供参考，不会自动修改任何内容。
      </div>

      <div class="answer-section">
        <h3 class="answer-title">回答</h3>
        <div class="answer-content">
          <pre class="answer-text">{{ askResult.answer }}</pre>
        </div>
        <div class="answer-meta">
          <span class="model-badge">{{ askResult.model }}</span>
          <span class="mode-badge">{{ askResult.retrieval_mode }}</span>
        </div>
      </div>

      <div v-if="askResult.citations.length > 0" class="citations-section">
        <h3 class="citations-title">
          引用来源（{{ askResult.citations.length }} 条）
        </h3>
        <ul class="citations-list">
          <li
            v-for="citation in askResult.citations"
            :key="citation.chunk_id"
            class="citation-item"
          >
            <div class="citation-source">
              <span class="source-title">{{ citation.source_title }}</span>
              <span v-if="citation.relevance_score != null" class="score-badge">
                {{ formatScore(citation.relevance_score) }}
              </span>
            </div>

            <div class="citation-chunk">
              <span v-if="citation.chunk_heading" class="chunk-heading">
                {{ citation.chunk_heading }}
              </span>
              <p class="chunk-content">
                {{ truncateContent(citation.chunk_content) }}
              </p>
            </div>

            <div class="citation-actions">
              <button
                type="button"
                class="action-button"
                @click="handleSelectCitation(citation)"
              >
                打开资料
              </button>
            </div>
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

.search-filters {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: end;
}

.search-filters label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 0.8rem;
  color: var(--zs-color-text-muted);
}

.search-filters select,
.search-filters input {
  padding: 6px 10px;
  border: 1px solid var(--zs-color-border);
  border-radius: 4px;
  font-size: 0.85rem;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.clear-filters {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid var(--zs-color-border);
  border-radius: 4px;
  font-size: 0.85rem;
  color: var(--zs-color-text-muted);
  cursor: pointer;
}

.clear-filters:hover {
  background: var(--zs-color-bg);
}

.error-message {
  padding: 10px 14px;
  background: var(--zs-color-danger-soft);
  border: 1px solid var(--zs-color-danger);
  border-radius: 6px;
  color: var(--zs-color-danger);
  font-size: 0.85rem;
}

.ask-results {
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

.answer-section {
  padding: 16px;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  background: var(--zs-color-bg);
  display: grid;
  gap: 10px;
}

.answer-title {
  margin: 0;
  font-size: 0.95rem;
  color: var(--zs-color-text);
}

.answer-content {
  padding: 12px 14px;
  background: var(--zs-color-surface);
  border-radius: 4px;
  border-left: 3px solid var(--zs-color-primary);
}

.answer-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  font-size: 0.88rem;
  line-height: 1.7;
  color: var(--zs-color-text);
}

.answer-meta {
  display: flex;
  gap: 8px;
}

.model-badge,
.mode-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

.citations-section {
  display: grid;
  gap: 10px;
}

.citations-title {
  margin: 0;
  font-size: 0.95rem;
  color: var(--zs-color-text);
}

.citations-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.citation-item {
  padding: 12px 14px;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  background: var(--zs-color-bg);
  display: grid;
  gap: 8px;
}

.citation-source {
  display: flex;
  align-items: center;
  gap: 8px;
}

.source-title {
  font-weight: 600;
  color: var(--zs-color-text);
  font-size: 0.88rem;
}

.score-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
}

.citation-chunk {
  display: grid;
  gap: 4px;
}

.chunk-heading {
  font-weight: 600;
  color: var(--zs-color-text);
  font-size: 0.82rem;
}

.chunk-content {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.6;
  color: var(--zs-color-text-muted);
  padding: 8px 10px;
  background: var(--zs-color-surface);
  border-radius: 4px;
  border-left: 3px solid var(--zs-color-primary);
}

.citation-actions {
  display: flex;
  gap: 8px;
}

.action-button {
  padding: 5px 12px;
  background: transparent;
  border: 1px solid var(--zs-color-border);
  border-radius: 4px;
  font-size: 0.8rem;
  color: var(--zs-color-text);
  cursor: pointer;
}

.action-button:hover {
  background: var(--zs-color-bg);
  border-color: var(--zs-color-primary);
  color: var(--zs-color-primary);
}
</style>
