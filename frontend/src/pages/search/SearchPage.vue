<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { rebuildProjectSearchIndex, searchProject } from '@/entities/search/api'
import type { ProjectSearchResult, SearchEntityType } from '@/entities/search/types'
import {
  SEARCH_ENTITY_TYPE_LABELS,
  SEARCH_FILTER_OPTIONS,
} from '@/entities/search/types'
import { safeReadJson, safeWriteJson } from '@/shared/storage/localWorkspaceState'

const route = useRoute()
const router = useRouter()

const keyword = ref('')
const searchedKeyword = ref('')
const results = ref<ProjectSearchResult[]>([])
const totalCount = ref(0)
const isSearching = ref(false)
const hasSearched = ref(false)
const errorMessage = ref('')
const activeFilter = ref<SearchEntityType | 'all'>('all')
const isRefreshing = ref(false)
const refreshMessage = ref('')

const projectId = computed<string>(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

const workspaceStorageKey = computed(() => `zhangshu:workspace:${projectId.value}`)

const filteredResults = computed(() => {
  if (activeFilter.value === 'all') return results.value
  return results.value.filter((r) => r.entity_type === activeFilter.value)
})

async function handleSearch() {
  const query = keyword.value.trim()
  if (!query) {
    results.value = []
    searchedKeyword.value = ''
    hasSearched.value = false
    totalCount.value = 0
    errorMessage.value = ''
    return
  }

  isSearching.value = true
  errorMessage.value = ''

  try {
    const types = activeFilter.value === 'all' ? undefined : [activeFilter.value]
    const response = await searchProject(projectId.value, query, { types, limit: 50 })
    results.value = response.results
    searchedKeyword.value = response.query
    hasSearched.value = true
    totalCount.value = response.total
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '搜索失败，请稍后重试')
  } finally {
    isSearching.value = false
  }
}

function handleFilterChange(filter: SearchEntityType | 'all') {
  activeFilter.value = filter
  if (hasSearched.value) {
    void handleSearch()
  }
}

async function openResult(result: ProjectSearchResult) {
  const pid = projectId.value
  switch (result.entity_type) {
    case 'chapter': {
      const currentState = safeReadJson<Record<string, unknown> | null>(
        workspaceStorageKey.value,
        null,
      )
      safeWriteJson(workspaceStorageKey.value, {
        ...(currentState ?? {}),
        selectedChapterId: result.entity_id,
      })
      await router.push(`/projects/${pid}`)
      break
    }
    case 'setting':
      await router.push(`/projects/${pid}/settings?settingId=${result.entity_id}`)
      break
    case 'character':
      await router.push(`/projects/${pid}/characters?characterId=${result.entity_id}`)
      break
    case 'clue':
      await router.push(`/projects/${pid}/clues?clueId=${result.entity_id}`)
      break
    case 'outline':
      await router.push(`/projects/${pid}/outlines?outlineId=${result.entity_id}`)
      break
    case 'knowledge': {
      const sourceId =
        result.metadata && typeof result.metadata.source_id === 'string'
          ? result.metadata.source_id
          : null
      const queryParam = sourceId ? `sourceId=${sourceId}` : `chunkId=${result.entity_id}`
      await router.push(`/projects/${pid}/knowledge?${queryParam}`)
      break
    }
    case 'timeline':
      await router.push(`/projects/${pid}/timeline`)
      break
    case 'graph':
      await router.push(`/projects/${pid}/graph`)
      break
  }
}

async function handleRefreshIndex() {
  isRefreshing.value = true
  refreshMessage.value = ''
  try {
    const resp = await rebuildProjectSearchIndex(projectId.value)
    refreshMessage.value = resp.message
  } catch {
    refreshMessage.value = '刷新搜索索引失败'
  } finally {
    isRefreshing.value = false
    setTimeout(() => {
      refreshMessage.value = ''
    }, 3000)
  }
}

function cleanSnippet(snippet: string): string {
  return snippet.replace(/>>>/g, '<mark>').replace(/<<</g, '</mark>')
}

function formatUpdatedAt(value: string | null): string {
  if (!value) return ''
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function getTypeLabel(type: SearchEntityType): string {
  return SEARCH_ENTITY_TYPE_LABELS[type] ?? type
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}
</script>

<template>
  <main class="search-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
        <p class="eyebrow">全文搜索</p>
        <h1>搜索</h1>
      </div>
      <div class="header-actions">
        <button
          class="ghost-button"
          type="button"
          :disabled="isRefreshing"
          @click="handleRefreshIndex"
        >
          {{ isRefreshing ? '正在刷新…' : '刷新搜索索引' }}
        </button>
        <RouterLink class="secondary-link" to="/projects">项目列表</RouterLink>
      </div>
    </header>

    <p v-if="refreshMessage" class="info-banner" role="status">{{ refreshMessage }}</p>

    <section class="search-panel">
      <form class="search-form" @submit.prevent="handleSearch">
        <label class="field-group">
          <span>输入关键词</span>
          <input
            v-model="keyword"
            type="search"
            placeholder="搜索正文、设定、人物、伏笔、大纲、知识库…"
            autocomplete="off"
          />
        </label>
        <button class="primary-button" type="submit" :disabled="isSearching || !keyword.trim()">
          {{ isSearching ? '正在搜索…' : '搜索' }}
        </button>
      </form>

      <div class="filter-bar" role="group" aria-label="搜索范围">
        <button
          v-for="opt in SEARCH_FILTER_OPTIONS"
          :key="opt.value"
          class="filter-chip"
          :class="{ active: activeFilter === opt.value }"
          type="button"
          @click="handleFilterChange(opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>
    </section>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>

    <section class="result-panel" aria-live="polite">
      <p v-if="hasSearched && filteredResults.length === 0" class="empty-state">
        未找到匹配「{{ searchedKeyword }}」的结果
      </p>

      <p v-if="hasSearched && totalCount > 0" class="result-count">
        共 {{ totalCount }} 条结果
      </p>

      <article
        v-for="result in filteredResults"
        :key="`${result.entity_type}:${result.entity_id}`"
        class="result-card"
      >
        <header class="result-header">
          <div class="result-title-group">
            <span class="type-pill">{{ getTypeLabel(result.entity_type) }}</span>
            <h2>{{ result.title || '(无标题)' }}</h2>
          </div>
          <span v-if="result.subtitle" class="subtitle">{{ result.subtitle }}</span>
        </header>

        <p v-if="result.snippet" class="snippet" v-html="cleanSnippet(result.snippet)"></p>

        <footer class="result-footer">
          <span v-if="result.updated_at" class="updated-at">
            更新于 {{ formatUpdatedAt(result.updated_at) }}
          </span>
          <button class="secondary-button" type="button" @click="openResult(result)">
            打开
          </button>
        </footer>
      </article>

      <p v-if="!hasSearched" class="empty-state">
        输入关键词搜索正文、设定、人物、伏笔、大纲、知识库等内容
      </p>
    </section>
  </main>
</template>

<style scoped>
.search-page {
  min-height: 100vh;
  box-sizing: border-box;
  overflow-x: hidden;
  padding: var(--zs-space-8) var(--zs-space-5);
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.page-header,
.search-panel,
.error-banner,
.info-banner,
.result-panel {
  max-width: 980px;
  margin-right: auto;
  margin-left: auto;
}

.page-header,
.search-form,
.result-header,
.result-footer {
  display: flex;
  gap: var(--zs-space-4);
}

.page-header {
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: var(--zs-space-6);
}

.header-actions {
  display: flex;
  gap: var(--zs-space-3);
  align-items: center;
}

.eyebrow {
  margin: 0 0 6px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0;
}

h1,
h2,
.snippet,
.empty-state,
.result-count {
  margin: 0;
}

h1 {
  font-size: 1.8rem;
  line-height: 1.1;
  letter-spacing: 0;
}

h2 {
  font-size: 1.1rem;
  line-height: 1.25;
}

.back-link {
  display: inline-flex;
  margin-bottom: var(--zs-space-2);
  color: var(--zs-color-primary);
  font-weight: 800;
  text-decoration: none;
}

.secondary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 14px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font-weight: 800;
  text-decoration: none;
}

.ghost-button {
  min-height: 38px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 14px;
  background: transparent;
  color: var(--zs-color-text-muted);
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.ghost-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.search-panel,
.result-card {
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.search-panel {
  display: grid;
  gap: var(--zs-space-4);
  margin-bottom: var(--zs-space-5);
  padding: var(--zs-space-5);
}

.search-form {
  align-items: end;
}

.field-group {
  flex: 1 1 auto;
  display: grid;
  gap: 8px;
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--zs-space-2);
}

.filter-chip {
  min-height: 32px;
  border: 1px solid var(--zs-color-border);
  border-radius: 999px;
  padding: 0 14px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font: inherit;
  font-size: 0.85rem;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.15s;
}

.filter-chip.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
}

.error-banner {
  box-sizing: border-box;
  margin-bottom: var(--zs-space-4);
  border: 1px solid var(--zs-color-danger);
  border-radius: var(--zs-radius-md);
  padding: 12px 14px;
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
  font-weight: 800;
}

.info-banner {
  box-sizing: border-box;
  margin-bottom: var(--zs-space-4);
  border: 1px solid var(--zs-color-success);
  border-radius: var(--zs-radius-md);
  padding: 10px 14px;
  background: var(--zs-color-success-soft, rgba(34, 197, 94, 0.08));
  color: var(--zs-color-success);
  font-weight: 800;
  max-width: 980px;
  margin-right: auto;
  margin-left: auto;
}

.result-panel {
  display: grid;
  gap: var(--zs-space-3);
}

.result-count {
  color: var(--zs-color-text-muted);
  font-size: 0.88rem;
  font-weight: 800;
}

.result-card {
  display: grid;
  gap: var(--zs-space-3);
  padding: var(--zs-space-4);
}

.result-header,
.result-footer {
  align-items: center;
  justify-content: space-between;
}

.result-title-group {
  display: flex;
  gap: var(--zs-space-2);
  align-items: center;
}

.type-pill {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 3px 10px;
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
  font-size: 0.75rem;
  font-weight: 800;
}

.subtitle {
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
}

.snippet {
  color: var(--zs-color-text-muted);
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.snippet :deep(mark) {
  border-radius: 2px;
  background: var(--zs-color-warning-soft, rgba(245, 158, 11, 0.15));
  color: var(--zs-color-text);
  padding: 0 2px;
  font-weight: 800;
}

.updated-at {
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 180px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

button {
  min-height: 38px;
  border-radius: var(--zs-radius-sm);
  border: 1px solid transparent;
  padding: 0 14px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.primary-button {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.secondary-button {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-primary);
}

@media (max-width: 720px) {
  .search-page {
    padding: var(--zs-space-6) var(--zs-space-4);
  }

  .page-header,
  .search-form,
  .result-header,
  .result-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .header-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .primary-button,
  .secondary-button,
  .secondary-link,
  .ghost-button {
    width: 100%;
  }
}
</style>
