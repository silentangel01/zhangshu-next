<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { searchProjectChapters } from '@/entities/search/api'
import type { ChapterSearchResult } from '@/entities/search/types'
import { safeReadJson, safeWriteJson } from '@/shared/storage/localWorkspaceState'

const route = useRoute()
const router = useRouter()

const keyword = ref('')
const searchedKeyword = ref('')
const results = ref<ChapterSearchResult[]>([])
const isSearching = ref(false)
const hasSearched = ref(false)
const errorMessage = ref('')

const projectId = computed<string>(() => {
  const value = route.params.projectId
  return (Array.isArray(value) ? value[0] : value) ?? ''
})

const workspaceStorageKey = computed(() => `zhangshu:workspace:${projectId.value}`)

async function handleSearch() {
  const query = keyword.value.trim()
  if (!query) {
    results.value = []
    searchedKeyword.value = ''
    hasSearched.value = false
    errorMessage.value = ''
    return
  }

  isSearching.value = true
  errorMessage.value = ''

  try {
    const response = await searchProjectChapters(projectId.value, query)
    results.value = response.results
    searchedKeyword.value = response.query
    hasSearched.value = true
  } catch (error) {
    errorMessage.value = getErrorMessage(error, '搜索失败，请稍后重试')
  } finally {
    isSearching.value = false
  }
}

async function openChapter(result: ChapterSearchResult) {
  const currentState = safeReadJson<Record<string, unknown> | null>(workspaceStorageKey.value, null)
  safeWriteJson(workspaceStorageKey.value, {
    ...(currentState ?? {}),
    selectedChapterId: result.chapter_id,
  })
  await router.push(`/projects/${projectId.value}`)
}

function formatUpdatedAt(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function getMatchedFieldLabel(value: ChapterSearchResult['matched_field']): string {
  return value === 'title' ? '标题' : '正文'
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
        <p class="eyebrow">搜索</p>
        <h1>搜索</h1>
      </div>
      <RouterLink class="secondary-link" to="/projects">项目列表</RouterLink>
    </header>

    <section class="search-panel">
      <form class="search-form" @submit.prevent="handleSearch">
        <label class="field-group">
          <span>输入关键词</span>
          <input
            v-model="keyword"
            type="search"
            placeholder="搜索章节标题和正文"
            autocomplete="off"
          />
        </label>
        <button class="primary-button" type="submit" :disabled="isSearching || !keyword.trim()">
          {{ isSearching ? '正在搜索…' : '搜索' }}
        </button>
      </form>
    </section>

    <section v-if="errorMessage" class="error-banner" role="alert">
      {{ errorMessage }}
    </section>

    <section class="result-panel" aria-live="polite">
      <p v-if="hasSearched && results.length === 0" class="empty-state">未找到结果</p>

      <article v-for="result in results" :key="result.chapter_id" class="result-card">
        <header class="result-header">
          <div>
            <p class="volume-title">{{ result.volume_title || '未分卷章节' }}</p>
            <h2>{{ result.chapter_title }}</h2>
          </div>
          <span class="match-pill">{{ getMatchedFieldLabel(result.matched_field) }}</span>
        </header>

        <p class="snippet">{{ result.snippet }}</p>

        <footer class="result-footer">
          <span>更新于 {{ formatUpdatedAt(result.updated_at) }}</span>
          <button class="secondary-button" type="button" @click="openChapter(result)">打开章节</button>
        </footer>
      </article>

      <p v-if="!hasSearched" class="empty-state">输入关键词后搜索章节标题和正文</p>
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

.eyebrow {
  margin: 0 0 6px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0;
}

h1,
h2,
.volume-title,
.snippet,
.empty-state {
  margin: 0;
}

h1 {
  font-size: 1.8rem;
  line-height: 1.1;
  letter-spacing: 0;
}

h2 {
  margin-top: 4px;
  font-size: 1.18rem;
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

.search-panel,
.result-card {
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.search-panel {
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

.result-panel {
  display: grid;
  gap: var(--zs-space-3);
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

.volume-title,
.result-footer,
.snippet {
  color: var(--zs-color-text-muted);
}

.snippet {
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.match-pill {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 9px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.78rem;
  font-weight: 800;
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

  .primary-button,
  .secondary-button,
  .secondary-link {
    width: 100%;
  }
}
</style>
