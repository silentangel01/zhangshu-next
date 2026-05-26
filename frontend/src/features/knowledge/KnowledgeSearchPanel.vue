<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

import { searchKnowledgeChunks } from '@/entities/knowledge/api'
import type {
  KnowledgeCredibility,
  KnowledgeRetrievalChunkResult,
  KnowledgeRetrievalResponse,
  KnowledgeRetrievalStrictness,
  KnowledgeSearchMode,
  KnowledgeSourceType,
} from '@/entities/knowledge/types'
import {
  knowledgeCredibilityLabels,
  knowledgeRetrievalStrictnessLabels,
  knowledgeSourceTypeLabels,
} from '@/entities/knowledge/types'

const props = defineProps<{
  projectId: string
}>()

const emit = defineEmits<{
  selectSource: [sourceId: string]
}>()

const keyword = ref('')
const isSearching = ref(false)
const errorMessage = ref('')
const searchResult = ref<KnowledgeRetrievalResponse | null>(null)
const searchMode = ref<KnowledgeSearchMode>('keyword')
const strictness = ref<KnowledgeRetrievalStrictness>('balanced')

const strictnessOptions: KnowledgeRetrievalStrictness[] = ['strict', 'balanced', 'broad']

const filters = reactive({
  source_type: '' as KnowledgeSourceType | '',
  credibility: '' as KnowledgeCredibility | '',
  tag: '',
})

const sourceTypes: KnowledgeSourceType[] = ['note', 'file', 'webpage', 'book', 'quote', 'custom']
const credibilities: KnowledgeCredibility[] = ['low', 'normal', 'high']

const hasResults = computed(() => (searchResult.value?.results.length ?? 0) > 0)
const totalResults = computed(() => searchResult.value?.total ?? 0)
const isSemanticMode = computed(() => searchMode.value === 'semantic' || searchMode.value === 'hybrid')

async function handleSearch() {
  if (!keyword.value.trim()) {
    errorMessage.value = '请输入搜索关键词'
    return
  }

  isSearching.value = true
  errorMessage.value = ''
  searchResult.value = null

  try {
    searchResult.value = await searchKnowledgeChunks(props.projectId, keyword.value.trim(), {
      source_type: filters.source_type || undefined,
      credibility: filters.credibility || undefined,
      tag: filters.tag || undefined,
      mode: searchMode.value,
      strictness: strictness.value,
    })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '搜索失败，请稍后重试。'
  } finally {
    isSearching.value = false
  }
}

function handleClearFilters() {
  filters.source_type = ''
  filters.credibility = ''
  filters.tag = ''
}

function handleSelectResult(result: KnowledgeRetrievalChunkResult) {
  emit('selectSource', result.source_id)
}

function handleCopyCitation(result: KnowledgeRetrievalChunkResult) {
  const citation = `${result.source_title} · ${result.chunk_heading || `片段 #${result.chunk_index + 1}`}`
  navigator.clipboard.writeText(citation).catch(() => {
    // Fallback: ignore if clipboard not available
  })
}

function formatScore(score: number | null | undefined): string {
  if (score == null) return ''
  return `${(score * 100).toFixed(0)}%`
}

const matchQualityLabels: Record<string, string> = {
  high: '高相关',
  medium: '中相关',
  low: '弱相关',
}

const matchQualityClass: Record<string, string> = {
  high: 'quality-high',
  medium: 'quality-medium',
  low: 'quality-low',
}
</script>

<template>
  <section class="search-panel">
    <header class="search-header">
      <h2>知识库检索</h2>
      <p class="search-description">
        在知识库中搜索关键词或语义检索，查看命中片段和上下文，复制引用。
      </p>
    </header>

    <form class="search-form" @submit.prevent="handleSearch">
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

      <div class="strictness-control">
        <span class="strictness-label">匹配范围</span>
        <div class="strictness-segments">
          <button
            v-for="opt in strictnessOptions"
            :key="opt"
            type="button"
            class="strictness-button"
            :class="{ active: strictness === opt }"
            @click="strictness = opt"
          >
            {{ knowledgeRetrievalStrictnessLabels[opt] }}
          </button>
        </div>
      </div>

      <div class="search-input-group">
        <input
          v-model="keyword"
          type="search"
          :placeholder="searchMode === 'keyword' ? '搜索关键词（标题、正文、标签）' : '输入查询内容（语义匹配）'"
          :disabled="isSearching"
          @keyup.enter="handleSearch"
        />
        <button type="submit" class="search-button" :disabled="isSearching">
          {{ isSearching ? '搜索中...' : '搜索' }}
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
          <span>标签</span>
          <input v-model="filters.tag" type="text" placeholder="标签关键词" />
        </label>

        <button type="button" class="clear-filters" @click="handleClearFilters">
          清空筛选
        </button>
      </div>
    </form>

    <div v-if="errorMessage" class="error-message" role="alert">
      {{ errorMessage }}
    </div>

    <div v-if="searchResult" class="search-results">
      <p class="results-summary">
        找到 <strong>{{ totalResults }}</strong> 个匹配结果
        <span v-if="isSemanticMode" class="mode-indicator">（{{ searchMode === 'semantic' ? '语义' : '混合' }}模式）</span>
      </p>

      <div
        v-if="searchResult.filtered_count && searchResult.filtered_count > 0"
        class="filtered-notice"
      >
        已隐藏 {{ searchResult.filtered_count }} 个低相关片段
      </div>

      <div v-if="searchResult.warnings && searchResult.warnings.length > 0" class="retrieval-warnings">
        <p v-for="(warning, idx) in searchResult.warnings" :key="idx">{{ warning }}</p>
      </div>

      <div v-if="!hasResults" class="empty-results">
        <p v-if="searchMode === 'semantic'">
          未找到匹配结果。请确保已刷新知识索引。
        </p>
        <p v-else>未找到匹配的知识片段。</p>
      </div>

      <ul v-else class="results-list">
        <li
          v-for="result in searchResult.results"
          :key="result.chunk_id"
          class="result-item"
        >
          <div class="result-source">
            <span class="source-title">{{ result.source_title }}</span>
            <span class="source-meta">
              <span class="type-badge">{{ knowledgeSourceTypeLabels[result.source_type] }}</span>
              <span class="credibility-badge" :class="result.source_credibility">
                {{ knowledgeCredibilityLabels[result.source_credibility] }}
              </span>
              <span
                v-if="result.match_quality"
                class="quality-badge"
                :class="matchQualityClass[result.match_quality] || ''"
              >
                {{ matchQualityLabels[result.match_quality] || result.match_quality }}
              </span>
              <span v-if="result.final_score != null" class="score-badge">
                {{ formatScore(result.final_score) }}
              </span>
            </span>
          </div>

          <div class="result-chunk">
            <div class="chunk-head">
              <span v-if="result.chunk_heading" class="chunk-heading">
                {{ result.chunk_heading }}
              </span>
              <span class="chunk-index">片段 #{{ result.chunk_index + 1 }}</span>
            </div>

            <div v-if="searchMode === 'keyword'" class="chunk-context">
              <span class="context-before">{{ result.context_before }}</span>
              <mark class="matched-snippet">{{ result.matched_snippet }}</mark>
              <span class="context-after">{{ result.context_after }}</span>
            </div>
            <p v-else class="chunk-preview">
              {{ result.matched_snippet }}{{ result.context_after ? '...' : '' }}
            </p>
            <p v-if="result.match_reason" class="match-reason">
              {{ result.match_reason }}
            </p>
          </div>

          <div class="result-actions">
            <button
              type="button"
              class="action-button"
              @click="handleSelectResult(result)"
            >
              打开资料
            </button>
            <button
              type="button"
              class="action-button citation-button"
              @click="handleCopyCitation(result)"
            >
              复制引用
            </button>
          </div>
        </li>
      </ul>
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

.results-summary {
  margin: 0;
  font-size: 0.9rem;
  color: var(--zs-color-text-muted);
}

.results-summary strong {
  color: var(--zs-color-text);
}

.empty-results {
  text-align: center;
  padding: 32px 20px;
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
}

.results-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 12px;
}

.result-item {
  padding: 14px;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  background: var(--zs-color-bg);
  display: grid;
  gap: 10px;
}

.result-source {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.source-title {
  font-weight: 600;
  color: var(--zs-color-text);
  font-size: 0.9rem;
}

.source-meta {
  display: flex;
  gap: 6px;
}

.type-badge,
.credibility-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

.credibility-badge.high {
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
}

.credibility-badge.low {
  background: var(--zs-color-warning-soft);
  color: var(--zs-color-warning);
}

.score-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
}

.mode-indicator {
  color: var(--zs-color-primary);
  font-size: 0.82rem;
}

.chunk-preview {
  color: var(--zs-color-text);
  font-size: 0.85rem;
  line-height: 1.6;
  margin: 0;
  padding: 8px 12px;
  background: var(--zs-color-surface);
  border-radius: 4px;
  border-left: 3px solid var(--zs-color-primary);
}

.result-chunk {
  display: grid;
  gap: 6px;
}

.chunk-head {
  display: flex;
  gap: 8px;
  align-items: center;
}

.chunk-heading {
  font-weight: 600;
  color: var(--zs-color-text);
  font-size: 0.85rem;
}

.chunk-index {
  color: var(--zs-color-text-faint);
  font-size: 0.75rem;
}

.chunk-context {
  font-size: 0.85rem;
  line-height: 1.6;
  color: var(--zs-color-text);
  padding: 8px 12px;
  background: var(--zs-color-surface);
  border-radius: 4px;
  border-left: 3px solid var(--zs-color-primary);
}

.context-before,
.context-after {
  color: var(--zs-color-text-muted);
}

.matched-snippet {
  background: var(--zs-color-warning-soft);
  color: var(--zs-color-text);
  padding: 1px 3px;
  border-radius: 2px;
  font-weight: 600;
}

.result-actions {
  display: flex;
  gap: 8px;
}

.action-button {
  padding: 6px 14px;
  background: transparent;
  border: 1px solid var(--zs-color-border);
  border-radius: 4px;
  font-size: 0.82rem;
  color: var(--zs-color-text);
  cursor: pointer;
}

.action-button:hover {
  background: var(--zs-color-bg);
  border-color: var(--zs-color-primary);
  color: var(--zs-color-primary);
}

.citation-button {
  color: var(--zs-color-primary);
  border-color: var(--zs-color-primary);
}

.strictness-control {
  display: flex;
  align-items: center;
  gap: 10px;
}

.strictness-label {
  font-size: 0.8rem;
  color: var(--zs-color-text-muted);
  white-space: nowrap;
}

.strictness-segments {
  display: flex;
  gap: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  overflow: hidden;
  width: fit-content;
}

.strictness-button {
  border: none;
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 600;
  padding: 4px 12px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}

.strictness-button + .strictness-button {
  border-left: 1px solid var(--zs-color-border);
}

.strictness-button.active {
  background: var(--zs-color-info);
  color: #fff;
}

.strictness-button:hover:not(.active) {
  background: var(--zs-color-bg);
}

.quality-badge {
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
}

.quality-high {
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
}

.quality-medium {
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

.quality-low {
  background: var(--zs-color-warning-soft);
  color: var(--zs-color-warning);
}

.filtered-notice {
  padding: 6px 12px;
  background: var(--zs-color-info-soft);
  border-radius: 4px;
  font-size: 0.82rem;
  color: var(--zs-color-info);
}

.retrieval-warnings {
  padding: 8px 12px;
  background: var(--zs-color-warning-soft);
  border: 1px solid var(--zs-color-warning);
  border-radius: 6px;
}

.retrieval-warnings p {
  margin: 0;
  font-size: 0.82rem;
  color: var(--zs-color-warning);
}

.match-reason {
  margin: 4px 0 0;
  font-size: 0.78rem;
  color: var(--zs-color-text-faint);
  font-style: italic;
}
</style>
