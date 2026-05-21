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
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回项目</RouterLink>
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
  padding: 40px;
  background: #f6f8fb;
  color: #111827;
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
  gap: 16px;
}

.page-header {
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 24px;
}

.eyebrow {
  margin: 0 0 6px;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

h1,
h2,
.volume-title,
.snippet,
.empty-state {
  margin: 0;
}

h1 {
  font-size: 2rem;
  line-height: 1.1;
}

h2 {
  margin-top: 4px;
  font-size: 1.18rem;
  line-height: 1.25;
}

.back-link {
  display: inline-flex;
  margin-bottom: 14px;
  color: #2563eb;
  font-weight: 800;
  text-decoration: none;
}

.secondary-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  box-sizing: border-box;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 0 14px;
  background: #ffffff;
  color: #374151;
  font-weight: 800;
  text-decoration: none;
}

.search-panel,
.result-card {
  box-sizing: border-box;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 10px 28px rgb(20 24 31 / 6%);
}

.search-panel {
  margin-bottom: 18px;
  padding: 18px;
}

.search-form {
  align-items: end;
}

.field-group {
  flex: 1 1 auto;
  display: grid;
  gap: 8px;
  color: #4b5563;
  font-weight: 800;
}

input {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 12px;
  background: #fbfcfe;
  color: #111827;
  font: inherit;
}

.error-banner {
  box-sizing: border-box;
  margin-bottom: 16px;
  border: 1px solid #f4b4ad;
  border-radius: 8px;
  padding: 12px 14px;
  background: #fff1f0;
  color: #9f1c12;
  font-weight: 800;
}

.result-panel {
  display: grid;
  gap: 14px;
}

.result-card {
  display: grid;
  gap: 14px;
  padding: 18px;
}

.result-header,
.result-footer {
  align-items: center;
  justify-content: space-between;
}

.volume-title,
.result-footer,
.snippet {
  color: #64748b;
}

.snippet {
  line-height: 1.7;
  overflow-wrap: anywhere;
}

.match-pill {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 9px;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.78rem;
  font-weight: 800;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 180px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #ffffff;
  color: #64748b;
  font-weight: 800;
}

button {
  min-height: 38px;
  border-radius: 6px;
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
  background: #2563eb;
  color: #ffffff;
}

.secondary-button {
  border-color: #cfd7e3;
  background: #ffffff;
  color: #2563eb;
}

@media (max-width: 720px) {
  .search-page {
    padding: 24px 16px;
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
