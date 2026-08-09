<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import {
  createKnowledgeLink,
  createKnowledgeSource,
  deleteKnowledgeLink,
  deleteKnowledgeSource,
  getKnowledgeIndexProfile,
  getKnowledgeIndexStatus,
  getKnowledgeSource,
  listKnowledgeChunks,
  listKnowledgeLinks,
  listKnowledgeSources,
  updateKnowledgeSource,
} from '@/entities/knowledge/api'
import type {
  CreateKnowledgeLinkPayload,
  CreateKnowledgeSourcePayload,
  KnowledgeChunk,
  KnowledgeCredibility,
  IndexProfile,
  KnowledgeIndexStatus,
  KnowledgeLink,
  KnowledgeLinkRelationType,
  KnowledgeLinkTargetType,
  KnowledgeSource,
  KnowledgeSourceStatus,
  KnowledgeSourceType,
} from '@/entities/knowledge/types'
import {
  knowledgeCredibilityLabels,
  knowledgeLinkRelationTypeLabels,
  knowledgeLinkTargetTypeLabels,
  knowledgeSourceStatusLabels,
  knowledgeSourceTypeLabels,
} from '@/entities/knowledge/types'
import KnowledgeAskPanel from '@/features/knowledge/KnowledgeAskPanel.vue'
import KnowledgeGraphPanel from '@/features/knowledge/KnowledgeGraphPanel.vue'
import KnowledgeImportDialog from '@/features/knowledge/KnowledgeImportDialog.vue'
import KnowledgeIndexRefreshDialog from '@/features/knowledge/KnowledgeIndexRefreshDialog.vue'
import KnowledgeSearchPanel from '@/features/knowledge/KnowledgeSearchPanel.vue'
import KnowledgeSummaryPanel from '@/features/knowledge/KnowledgeSummaryPanel.vue'

const route = useRoute()
const router = useRouter()

const projectId = computed(() => route.params.projectId as string)

const sources = ref<KnowledgeSource[]>([])
const selectedSource = ref<KnowledgeSource | null>(null)
const chunks = ref<KnowledgeChunk[]>([])
const links = ref<KnowledgeLink[]>([])

const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const isCreating = ref(false)

const filters = reactive({
  keyword: '',
  source_type: '' as KnowledgeSourceType | '',
  status: '' as KnowledgeSourceStatus | '',
  tag: '',
  credibility: '' as KnowledgeCredibility | '',
})

const form = reactive({
  title: '',
  source_type: 'note' as KnowledgeSourceType,
  source_uri: '',
  author: '',
  summary: '',
  content: '',
  tags: '',
  status: 'active' as KnowledgeSourceStatus,
  credibility: 'normal' as KnowledgeCredibility,
})

const linkForm = reactive({
  target_type: 'chapter' as KnowledgeLinkTargetType,
  target_id: '',
  relation_type: 'reference' as KnowledgeLinkRelationType,
  note: '',
})

const isLinkFormOpen = ref(false)
const isFilterPanelOpen = ref(false)
const isImportDialogOpen = ref(false)
const rightTab = ref<'chunks' | 'links'>('chunks')
const viewMode = ref<'browse' | 'search' | 'ask' | 'summary' | 'graph'>('browse')
const indexStatus = ref<KnowledgeIndexStatus | null>(null)
const indexProfile = ref<IndexProfile | null>(null)
const isRefreshDialogOpen = ref(false)
const showMoreMenu = ref(false)

function closeMoreMenu() {
  showMoreMenu.value = false
}

const sourceTypes: KnowledgeSourceType[] = ['file', 'note', 'book', 'webpage', 'quote', 'custom']
const statuses: KnowledgeSourceStatus[] = ['active', 'archived']
const credibilities: KnowledgeCredibility[] = ['low', 'normal', 'high']
const targetTypes: KnowledgeLinkTargetType[] = [
  'project',
  'chapter',
  'character',
  'setting',
  'clue',
  'timeline_event',
  'graph_node',
]
const relationTypes: KnowledgeLinkRelationType[] = [
  'reference',
  'inspiration',
  'evidence',
  'background',
  'related',
]

const hasActiveFilter = computed(() => {
  return !!(filters.source_type || filters.status || filters.tag || filters.credibility)
})

const activeFilterCount = computed(() => {
  let count = 0
  if (filters.source_type) count++
  if (filters.status) count++
  if (filters.tag) count++
  if (filters.credibility) count++
  return count
})

const hasSourceFormDirty = computed(() => {
  const source = selectedSource.value
  if (!source || isCreating.value) return false
  return (
    form.title !== source.title ||
    form.source_type !== source.source_type ||
    form.source_uri !== source.source_uri ||
    form.author !== (source.author || '') ||
    form.summary !== source.summary ||
    form.content !== source.content ||
    form.tags !== source.tags ||
    form.status !== source.status ||
    form.credibility !== source.credibility
  )
})

watch(
  () => projectId.value,
  () => {
    void loadSources()
  },
  { immediate: true },
)

async function loadSources() {
  if (!projectId.value) return
  isLoading.value = true
  errorMessage.value = ''
  try {
    const result = await listKnowledgeSources(projectId.value, {
      keyword: filters.keyword || undefined,
      source_type: filters.source_type || undefined,
      status: filters.status || undefined,
      tag: filters.tag || undefined,
      credibility: filters.credibility || undefined,
    })
    sources.value = result.items
    if (selectedSource.value) {
      const still = sources.value.find((item) => item.id === selectedSource.value?.id)
      if (still) {
        selectedSource.value = still
      } else {
        selectedSource.value = null
        chunks.value = []
        links.value = []
      }
    }
  } catch {
    errorMessage.value = '知识库加载失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

function handleApplyFilters() {
  void loadSources()
}

function handleClearFilters() {
  filters.source_type = ''
  filters.status = ''
  filters.tag = ''
  filters.credibility = ''
  void loadSources()
}

function handleNewSource() {
  isCreating.value = true
  selectedSource.value = null
  chunks.value = []
  links.value = []
  form.title = ''
  form.source_type = 'note'
  form.source_uri = ''
  form.author = ''
  form.summary = ''
  form.content = ''
  form.tags = ''
  form.status = 'active'
  form.credibility = 'normal'
}

function handleSelectSource(source: KnowledgeSource) {
  isCreating.value = false
  selectedSource.value = source
  form.title = source.title
  form.source_type = source.source_type
  form.source_uri = source.source_uri
  form.author = source.author || ''
  form.summary = source.summary
  form.content = source.content
  form.tags = source.tags
  form.status = source.status
  form.credibility = source.credibility
  void loadChunks()
  void loadLinks()
}

async function handleSearchSelectSource(sourceId: string) {
  viewMode.value = 'browse'
  try {
    const source = await getKnowledgeSource(sourceId)
    handleSelectSource(source)
  } catch {
    errorMessage.value = '加载资料失败，请稍后重试。'
  }
}

async function loadChunks() {
  if (!selectedSource.value) return
  try {
    chunks.value = await listKnowledgeChunks(selectedSource.value.id)
  } catch {
    chunks.value = []
  }
}

async function loadLinks() {
  if (!selectedSource.value) return
  try {
    links.value = await listKnowledgeLinks(selectedSource.value.id)
  } catch {
    links.value = []
  }
}

async function handleSave() {
  if (!form.title.trim()) {
    errorMessage.value = '标题不能为空'
    return
  }
  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  try {
    if (isCreating.value) {
      const payload: CreateKnowledgeSourcePayload = {
        title: form.title.trim(),
        source_type: form.source_type,
        source_uri: form.source_uri,
        author: form.author || null,
        summary: form.summary,
        content: form.content,
        tags: form.tags,
        status: form.status,
        credibility: form.credibility,
      }
      const created = await createKnowledgeSource(projectId.value, payload)
      successMessage.value = '知识资料已创建'
      isCreating.value = false
      selectedSource.value = created
      await loadSources()
      await loadChunks()
      await loadLinks()
    } else if (selectedSource.value) {
      const updated = await updateKnowledgeSource(selectedSource.value.id, {
        title: form.title.trim(),
        source_type: form.source_type,
        source_uri: form.source_uri,
        author: form.author || null,
        summary: form.summary,
        content: form.content,
        tags: form.tags,
        status: form.status,
        credibility: form.credibility,
      })
      successMessage.value = '知识资料已更新'
      selectedSource.value = updated
      await loadSources()
      await loadChunks()
    }
  } catch {
    errorMessage.value = '保存失败，请稍后重试。'
  } finally {
    isSaving.value = false
  }
}

async function handleDelete() {
  if (!selectedSource.value) return
  if (!confirm(`确认删除资料"${selectedSource.value.title}"？此操作不可撤销。`)) return
  isSaving.value = true
  errorMessage.value = ''
  try {
    await deleteKnowledgeSource(selectedSource.value.id)
    successMessage.value = '知识资料已删除'
    selectedSource.value = null
    chunks.value = []
    links.value = []
    await loadSources()
  } catch {
    errorMessage.value = '删除失败，请稍后重试。'
  } finally {
    isSaving.value = false
  }
}

async function handleRefreshed() {
  await loadIndexStatus()
  if (selectedSource.value) {
    await loadChunks()
  }
  void loadSources()
}

async function handleCreateLink() {
  if (!selectedSource.value) return
  if (!linkForm.target_id.trim()) {
    errorMessage.value = '请填写目标 ID'
    return
  }
  isSaving.value = true
  errorMessage.value = ''
  try {
    const payload: CreateKnowledgeLinkPayload = {
      target_type: linkForm.target_type,
      target_id: linkForm.target_id.trim(),
      relation_type: linkForm.relation_type,
      note: linkForm.note,
    }
    await createKnowledgeLink(selectedSource.value.id, payload)
    successMessage.value = '关联已创建'
    isLinkFormOpen.value = false
    linkForm.target_id = ''
    linkForm.note = ''
    await loadLinks()
  } catch {
    errorMessage.value = '创建关联失败，请稍后重试。'
  } finally {
    isSaving.value = false
  }
}

async function handleDeleteLink(link: KnowledgeLink) {
  if (!confirm('确认删除此关联？')) return
  isSaving.value = true
  errorMessage.value = ''
  try {
    await deleteKnowledgeLink(link.id)
    successMessage.value = '关联已删除'
    await loadLinks()
  } catch {
    errorMessage.value = '删除关联失败，请稍后重试。'
  } finally {
    isSaving.value = false
  }
}

async function loadIndexStatus() {
  if (!projectId.value) return
  try {
    const [status, profile] = await Promise.all([
      getKnowledgeIndexStatus(projectId.value),
      getKnowledgeIndexProfile(projectId.value),
    ])
    indexStatus.value = status
    indexProfile.value = profile
  } catch {
    // Silently fail - index status is optional display
  }
}

function handleImported() {
  isImportDialogOpen.value = false
  void loadSources()
}

onMounted(() => {
  void loadSources()
  void loadIndexStatus()
  document.addEventListener('click', closeMoreMenu)
  document.addEventListener('keydown', handleKeyDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeMoreMenu)
  document.removeEventListener('keydown', handleKeyDown)
})

function handleKeyDown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    showMoreMenu.value = false
  }
}
</script>

<template>
  <main class="knowledge-page material-page">
    <header class="page-header">
      <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
      <p class="eyebrow">外部参考资料</p>

      <div class="actions-row">
        <div class="view-mode-toggle">
          <button type="button" class="mode-button" :class="{ active: viewMode === 'browse' }" @click="viewMode = 'browse'">浏览</button>
          <button type="button" class="mode-button" :class="{ active: viewMode === 'search' }" @click="viewMode = 'search'">检索</button>
          <button type="button" class="mode-button" :class="{ active: viewMode === 'ask' }" @click="viewMode = 'ask'">问答</button>
          <button type="button" class="mode-button" :class="{ active: viewMode === 'summary' }" @click="viewMode = 'summary'">摘要</button>
          <button type="button" class="mode-button" :class="{ active: viewMode === 'graph' }" @click="viewMode = 'graph'">图谱</button>
        </div>
        <div class="header-right-actions">
          <button class="primary-button" type="button" :disabled="isSaving" @click="isImportDialogOpen = true">批量导入</button>
          <div class="overflow-menu" @click.stop>
            <button class="secondary-button more-button" type="button" @click="showMoreMenu = !showMoreMenu">更多 &#x25BE;</button>
            <div v-if="showMoreMenu" class="dropdown-menu">
              <button type="button" class="dropdown-item" @click="showMoreMenu = false; handleNewSource()">新建空白资料</button>
              <button type="button" class="dropdown-item" @click="showMoreMenu = false; isRefreshDialogOpen = true">刷新知识索引</button>
            </div>
          </div>
        </div>
      </div>

      <p class="page-note">
        知识库用于保存外部参考资料。推荐批量导入文件，也可以手动新建少量笔记。
      </p>
    </header>

    <div v-if="viewMode === 'browse'" class="knowledge-toolbar">
      <div class="search-group">
        <input
          v-model="filters.keyword"
          type="search"
          placeholder="搜索标题、正文、标签、摘要"
          @keyup.enter="handleApplyFilters"
        />
        <button
          class="secondary-button"
          type="button"
          :disabled="isSaving"
          @click="handleApplyFilters"
        >
          搜索
        </button>
      </div>
      <div class="filter-menu">
        <button
          class="secondary-button"
          type="button"
          :class="{ active: isFilterPanelOpen || hasActiveFilter }"
          @click="isFilterPanelOpen = !isFilterPanelOpen"
        >
          筛选{{ activeFilterCount > 0 ? `（${activeFilterCount}）` : '' }}
        </button>
        <div v-if="isFilterPanelOpen" class="filter-panel">
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
            <span>状态</span>
            <select v-model="filters.status">
              <option value="">全部状态</option>
              <option v-for="s in statuses" :key="s" :value="s">
                {{ knowledgeSourceStatusLabels[s] }}
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
            <input v-model="filters.tag" type="text" placeholder="输入标签关键词" />
          </label>
          <div class="filter-actions">
            <button class="secondary-button" type="button" @click="handleClearFilters">
              清空筛选
            </button>
            <button
              class="primary-button"
              type="button"
              @click="isFilterPanelOpen = false; handleApplyFilters()"
            >
              应用筛选
            </button>
          </div>
        </div>
      </div>
    </div>

    <section v-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</section>
    <section v-if="successMessage" class="success-banner" role="status">{{ successMessage }}</section>

    <section v-if="viewMode !== 'browse'" class="knowledge-mode-panel">
      <KnowledgeSearchPanel
        v-if="viewMode === 'search'"
        :project-id="projectId"
        @select-source="handleSearchSelectSource"
      />

      <KnowledgeAskPanel
        v-else-if="viewMode === 'ask'"
        :project-id="projectId"
        @select-source="handleSearchSelectSource"
      />

      <KnowledgeSummaryPanel
        v-else-if="viewMode === 'summary'"
        :project-id="projectId"
        @select-source="handleSearchSelectSource"
      />

      <KnowledgeGraphPanel
        v-else-if="viewMode === 'graph'"
        :project-id="projectId"
        :selected-source-id="selectedSource?.id ?? null"
        :selected-source-title="selectedSource?.title ?? null"
        @select-source="handleSearchSelectSource"
      />
    </section>

    <template v-else>
      <section v-if="isLoading" class="state-message">正在加载知识库…</section>

    <section v-else class="knowledge-layout material-layout" :class="{ 'no-right-panel': !selectedSource }">
      <aside class="list-panel material-list-panel">
        <div class="list-header">
          <span class="list-title">资料</span>
          <button class="secondary-button" type="button" :disabled="isSaving" @click="handleNewSource">
            新建
          </button>
        </div>
        <div v-if="sources.length === 0" class="empty-state">
          <p>暂无知识资料</p>
          <div class="empty-state-actions">
            <button class="primary-button" type="button" @click="isImportDialogOpen = true">批量导入文件</button>
            <button class="secondary-button" type="button" @click="handleNewSource">新建空白资料</button>
          </div>
        </div>
        <ul v-else class="source-list">
          <li
            v-for="source in sources"
            :key="source.id"
            class="source-item"
            :class="{ selected: selectedSource?.id === source.id }"
          >
            <button type="button" @click="handleSelectSource(source)">
              <span class="source-title">{{ source.title }}</span>
              <span class="source-meta">
                <span class="type-badge">{{ knowledgeSourceTypeLabels[source.source_type] || source.source_type }}</span>
                <span class="status-badge" :class="source.status">
                  {{ knowledgeSourceStatusLabels[source.status] || source.status }}
                </span>
                <span class="credibility-badge" :class="source.credibility">
                  {{ knowledgeCredibilityLabels[source.credibility] || source.credibility }}
                </span>
              </span>
              <span v-if="source.tags" class="source-tags">{{ source.tags }}</span>
            </button>
          </li>
        </ul>
      </aside>

      <section class="detail-panel material-detail-panel">
        <div v-if="!selectedSource && !isCreating" class="empty-detail">
          <p>选择左侧资料查看详情</p>
          <div class="empty-state-actions">
            <button class="secondary-button" type="button" @click="isImportDialogOpen = true">批量导入文件</button>
            <button class="secondary-button" type="button" @click="handleNewSource">或新建资料</button>
          </div>
        </div>

        <form
          v-else
          class="detail-form"
          @submit.prevent="handleSave"
        >
          <div class="form-head">
            <h2>{{ isCreating ? '新建知识资料' : '编辑知识资料' }}</h2>
          </div>

          <label class="zs-field">
            <span class="zs-field-label">标题</span>
            <input v-model="form.title" type="text" required placeholder="资料标题" />
          </label>

          <label class="zs-field">
            <span class="zs-field-label">正文</span>
            <textarea
              v-model="form.content"
              rows="18"
              class="knowledge-content-textarea"
              placeholder="资料正文内容"
            />
          </label>

          <details class="source-extra-fields" :open="isCreating || undefined">
            <summary>资料信息</summary>
            <div class="source-extra-grid">
              <label class="zs-field">
                <span class="zs-field-label">类型</span>
                <select v-model="form.source_type">
                  <option v-for="st in sourceTypes" :key="st" :value="st">
                    {{ knowledgeSourceTypeLabels[st] }}
                  </option>
                </select>
              </label>
              <label class="zs-field">
                <span class="zs-field-label">状态</span>
                <select v-model="form.status">
                  <option v-for="s in statuses" :key="s" :value="s">
                    {{ knowledgeSourceStatusLabels[s] }}
                  </option>
                </select>
              </label>
              <label class="zs-field">
                <span class="zs-field-label">可信度</span>
                <select v-model="form.credibility">
                  <option v-for="c in credibilities" :key="c" :value="c">
                    {{ knowledgeCredibilityLabels[c] }}
                  </option>
                </select>
              </label>
              <label class="zs-field">
                <span class="zs-field-label">来源 / 原路径 / URL</span>
                <input v-model="form.source_uri" type="text" placeholder="文件路径、网页链接、书名或出处" />
              </label>
              <label class="zs-field">
                <span class="zs-field-label">作者</span>
                <input v-model="form.author" type="text" placeholder="作者或出处" />
              </label>
              <label class="zs-field">
                <span class="zs-field-label">摘要</span>
                <textarea v-model="form.summary" rows="3" placeholder="资料概要" />
              </label>
              <label class="zs-field">
                <span class="zs-field-label">标签</span>
                <input v-model="form.tags" type="text" placeholder="多个标签用逗号分隔" />
              </label>
            </div>
          </details>

          <div class="form-actions">
            <button class="primary-button" type="submit" :disabled="isSaving">
              {{ isCreating ? '创建' : '保存' }}
            </button>
            <button
              v-if="!isCreating && selectedSource"
              class="secondary-button danger-button"
              type="button"
              :disabled="isSaving"
              @click="handleDelete"
            >
              删除
            </button>
          </div>
        </form>
      </section>

      <aside v-if="selectedSource" class="right-panel material-side-panel">
        <div class="tab-bar">
            <button
              type="button"
              :class="{ active: rightTab === 'chunks' }"
              @click="rightTab = 'chunks'"
            >
              索引片段（{{ chunks.length }}）
            </button>
            <button
              type="button"
              :class="{ active: rightTab === 'links' }"
              @click="rightTab = 'links'"
            >
              关联（{{ links.length }}）
            </button>
          </div>

          <div v-if="rightTab === 'chunks'" class="tab-content">
            <p v-if="indexStatus" class="index-status">
              索引状态：已准备 {{ indexStatus.indexed_chunks }} / {{ indexStatus.total_chunks }} 个片段
              <span v-if="indexProfile?.model_name" class="index-model-badge">
                {{ indexProfile.model_name }}
              </span>
              <span
                v-if="indexStatus.profile_status === 'error'"
                class="index-status-badge error"
              >
                错误
              </span>
              <span
                v-else-if="indexStatus.profile_status === 'stale'"
                class="index-status-badge stale"
              >
                需刷新
              </span>
              <span
                v-else-if="indexStatus.profile_status === 'not_configured'"
                class="index-status-badge not-configured"
              >
                未配置
              </span>
            </p>
            <p v-if="indexStatus?.last_error" class="index-error-hint">
              {{ indexStatus.last_error }}
            </p>
            <p v-if="chunks.length === 0" class="empty-hint">
              暂无索引片段。保存或导入资料后系统会自动整理；如果搜索不到新内容，可以刷新知识索引。
            </p>
            <ul v-else class="chunk-list">
              <li v-for="chunk in chunks" :key="chunk.id" class="chunk-item">
                <div class="chunk-head">
                  <span class="chunk-index">#{{ chunk.chunk_index + 1 }}</span>
                  <span v-if="chunk.heading" class="chunk-heading">{{ chunk.heading }}</span>
                  <span class="chunk-size">约 {{ chunk.token_count }} 字</span>
                </div>
                <p class="chunk-content">{{ chunk.content }}</p>
              </li>
            </ul>
          </div>

          <div v-if="rightTab === 'links'" class="tab-content">
            <div class="tab-actions">
              <button
                class="secondary-button"
                type="button"
                @click="isLinkFormOpen = !isLinkFormOpen"
              >
                {{ isLinkFormOpen ? '取消' : '新建关联' }}
              </button>
            </div>

            <div v-if="isLinkFormOpen" class="link-form">
              <label class="zs-field">
                <span class="zs-field-label">目标类型</span>
                <select v-model="linkForm.target_type">
                  <option v-for="tt in targetTypes" :key="tt" :value="tt">
                    {{ knowledgeLinkTargetTypeLabels[tt] }}
                  </option>
                </select>
              </label>
              <label class="zs-field">
                <span class="zs-field-label">目标 ID</span>
                <input v-model="linkForm.target_id" type="text" placeholder="目标对象的 ID" />
              </label>
              <label class="zs-field">
                <span class="zs-field-label">关系类型</span>
                <select v-model="linkForm.relation_type">
                  <option v-for="rt in relationTypes" :key="rt" :value="rt">
                    {{ knowledgeLinkRelationTypeLabels[rt] }}
                  </option>
                </select>
              </label>
              <label class="zs-field">
                <span class="zs-field-label">备注</span>
                <input v-model="linkForm.note" type="text" placeholder="关联备注（可选）" />
              </label>
              <button
                class="primary-button"
                type="button"
                :disabled="isSaving"
                @click="handleCreateLink"
              >
                创建关联
              </button>
            </div>

            <p v-if="links.length === 0 && !isLinkFormOpen" class="empty-hint">
              暂无关联。点击"新建关联"将资料与章节、人物、设定等建立连接。
            </p>
            <ul v-else class="link-list">
              <li v-for="link in links" :key="link.id" class="link-item">
                <div class="link-info">
                  <span class="link-type">
                    {{ knowledgeLinkTargetTypeLabels[link.target_type] || link.target_type }}
                  </span>
                  <span class="link-relation">
                    {{ knowledgeLinkRelationTypeLabels[link.relation_type] || link.relation_type }}
                  </span>
                  <span class="link-target-id">{{ link.target_id }}</span>
                </div>
                <p v-if="link.note" class="link-note">{{ link.note }}</p>
                <button
                  class="link-delete"
                  type="button"
                  :disabled="isSaving"
                  @click="handleDeleteLink(link)"
                >
                  删除
                </button>
              </li>
            </ul>
          </div>
      </aside>
    </section>
    </template>

    <KnowledgeImportDialog
      v-if="isImportDialogOpen"
      :project-id="projectId"
      @close="isImportDialogOpen = false"
      @imported="handleImported"
    />

    <KnowledgeIndexRefreshDialog
      v-if="isRefreshDialogOpen"
      :project-id="projectId"
      :selected-source-id="selectedSource?.id ?? null"
      :selected-source-title="selectedSource?.title ?? null"
      :has-unsaved-changes="hasSourceFormDirty"
      :current-provider-id="indexProfile?.provider_id ?? null"
      @close="isRefreshDialogOpen = false"
      @refreshed="handleRefreshed"
    />
  </main>
</template>

<style scoped>
.knowledge-page {
  min-height: 100vh;
  box-sizing: border-box;
  overflow-x: hidden;
  padding: var(--zs-space-6);
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.page-header,
.error-banner,
.success-banner,
.state-message,
.knowledge-toolbar,
.knowledge-layout {
  max-width: 1480px;
  margin-right: auto;
  margin-left: auto;
}

.page-header {
  display: grid;
  gap: var(--zs-space-1);
  margin-bottom: var(--zs-space-4);
}

.actions-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-3);
  margin-top: var(--zs-space-2);
}

.header-right-actions {
  display: flex;
  gap: var(--zs-space-2);
  align-items: center;
}

.overflow-menu {
  position: relative;
}

.more-button {
  white-space: nowrap;
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  z-index: 30;
  display: grid;
  gap: 2px;
  min-width: 160px;
  padding: var(--zs-space-1);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-md);
}

.dropdown-item {
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--zs-color-text);
  font-size: 0.82rem;
  padding: var(--zs-space-2) var(--zs-space-3);
  text-align: left;
  cursor: pointer;
  white-space: nowrap;
}

.dropdown-item:hover {
  background: var(--zs-color-bg);
  color: var(--zs-color-primary);
}

.back-link {
  display: inline-flex;
  margin-bottom: var(--zs-space-2);
  color: var(--zs-color-primary);
  font-weight: 800;
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.eyebrow {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
  margin: 0 0 var(--zs-space-1);
}

.page-note {
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
  line-height: 1.6;
  margin: 0;
}

.primary-button {
  background: var(--zs-color-primary);
  border: 1px solid var(--zs-color-primary);
  border-radius: var(--zs-radius-sm);
  color: var(--zs-color-on-primary);
  cursor: pointer;
  font-size: 0.84rem;
  font-weight: 700;
  min-height: 36px;
  padding: 0 var(--zs-space-4);
}

.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-button {
  background: var(--zs-color-surface);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  color: var(--zs-color-text);
  cursor: pointer;
  font-size: 0.82rem;
  min-height: 36px;
  padding: 0 var(--zs-space-3);
}

.secondary-button:hover {
  border-color: var(--zs-color-primary);
}

.secondary-button.active {
  border-color: var(--zs-color-primary);
  color: var(--zs-color-primary);
}

.danger-button {
  border-color: var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.danger-button:hover {
  background: var(--zs-color-danger-soft);
}

.knowledge-toolbar {
  display: flex;
  gap: var(--zs-space-2);
  flex-wrap: wrap;
  align-items: flex-start;
  margin-bottom: var(--zs-space-4);
}

.knowledge-mode-panel {
  max-width: 1480px;
  width: 100%;
  margin-right: auto;
  margin-left: auto;
  box-sizing: border-box;
}

.view-mode-toggle {
  display: flex;
  gap: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  overflow: hidden;
}

.mode-button {
  border: none;
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  font-weight: 600;
  padding: 5px 14px;
  cursor: pointer;
  transition: background var(--zs-duration-fast), color var(--zs-duration-fast);
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

.search-group {
  display: flex;
  gap: var(--zs-space-1);
  flex: 1;
  min-width: 200px;
}

.search-group input {
  flex: 1;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-1) var(--zs-space-3);
  font-size: 0.84rem;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.filter-menu {
  position: relative;
}

.filter-panel {
  position: absolute;
  top: 100%;
  right: 0;
  z-index: 20;
  display: grid;
  gap: var(--zs-space-2);
  padding: var(--zs-space-3);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  min-width: 220px;
  margin-top: var(--zs-space-1);
  box-shadow: var(--zs-shadow-md);
}

.filter-panel label {
  display: grid;
  gap: 3px;
}

.filter-panel label span {
  font-size: 0.76rem;
  color: var(--zs-color-text-muted);
  font-weight: 700;
}

.filter-panel select,
.filter-panel input {
  border: 1px solid var(--zs-color-border);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 0.82rem;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.filter-actions {
  display: flex;
  gap: var(--zs-space-1);
  justify-content: flex-end;
  padding-top: var(--zs-space-1);
}

.error-banner,
.success-banner {
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-2) var(--zs-space-3);
  font-size: 0.82rem;
  margin-bottom: var(--zs-space-4);
}

.error-banner {
  background: var(--zs-color-danger-soft);
  border: 1px solid var(--zs-color-danger);
  color: var(--zs-color-danger);
}

.success-banner {
  background: var(--zs-color-success-soft);
  border: 1px solid var(--zs-color-success);
  color: var(--zs-color-success);
}

.state-message {
  text-align: center;
  color: var(--zs-color-text-muted);
  padding: 40px var(--zs-space-5);
}

.knowledge-layout {
  display: grid;
  grid-template-columns: minmax(240px, 280px) minmax(480px, 1fr);
  gap: var(--zs-space-4);
  align-items: start;
}

.knowledge-layout:not(.no-right-panel) {
  grid-template-columns: minmax(240px, 280px) minmax(480px, 1fr) minmax(240px, 280px);
}

.list-panel,
.detail-panel,
.right-panel {
  min-width: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-4);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--zs-space-3);
}

.list-title {
  font-size: 0.82rem;
  font-weight: 800;
  color: var(--zs-color-text-muted);
}

.empty-state {
  display: grid;
  place-items: center;
  gap: var(--zs-space-3);
  min-height: 160px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  text-align: center;
  padding: var(--zs-space-4);
}

.empty-state p {
  margin: 0;
  font-size: 0.84rem;
}

.empty-state-actions {
  display: flex;
  gap: var(--zs-space-2);
  align-items: center;
}

.empty-hint {
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  text-align: center;
  padding: var(--zs-space-4) var(--zs-space-2);
}

.source-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--zs-space-1);
}

.source-item button {
  display: grid;
  gap: 3px;
  width: 100%;
  border: 1px solid transparent;
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-2);
  background: transparent;
  color: var(--zs-color-text);
  cursor: pointer;
  text-align: left;
}

.source-item button:hover {
  background: var(--zs-color-bg);
}

.source-item.selected button {
  background: var(--zs-color-primary-soft);
  border-color: var(--zs-color-primary);
}

.source-title {
  font-size: 0.84rem;
  font-weight: 700;
}

.source-meta {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.type-badge,
.status-badge,
.credibility-badge {
  border-radius: var(--zs-radius-pill);
  padding: 1px 6px;
  font-size: 0.68rem;
  font-weight: 700;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

.status-badge.archived {
  background: var(--zs-color-surface-muted);
  color: var(--zs-color-text-muted);
}

.credibility-badge.high {
  background: var(--zs-color-success-soft);
  color: var(--zs-color-success);
}

.credibility-badge.low {
  background: var(--zs-color-warning-soft);
  color: var(--zs-color-warning);
}

.source-tags {
  color: var(--zs-color-text-faint);
  font-size: 0.72rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-detail {
  display: grid;
  place-items: center;
  gap: var(--zs-space-3);
  min-height: 200px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
  text-align: center;
}

.empty-detail p {
  margin: 0;
}

.detail-form {
  display: grid;
  gap: var(--zs-space-3);
}

.form-head h2 {
  margin: 0;
  font-size: 1rem;
  color: var(--zs-color-text);
}

.knowledge-content-textarea {
  min-height: clamp(360px, 52vh, 720px);
}

.source-extra-fields {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-2) var(--zs-space-3);
}

.source-extra-fields > summary {
  cursor: pointer;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--zs-color-text-muted);
  padding: var(--zs-space-1) 0;
  user-select: none;
}

.source-extra-fields > summary:hover {
  color: var(--zs-color-text);
}

.source-extra-fields[open] > summary {
  margin-bottom: var(--zs-space-2);
  border-bottom: 1px solid var(--zs-color-border-soft);
  padding-bottom: var(--zs-space-2);
}

.source-extra-grid {
  display: grid;
  gap: var(--zs-space-3);
}

.zs-field {
  display: grid;
  gap: 3px;
}

.zs-field-label {
  font-size: 0.76rem;
  color: var(--zs-color-text-muted);
  font-weight: 700;
}

.zs-field input,
.zs-field select,
.zs-field textarea {
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-1) var(--zs-space-3);
  font-size: 0.84rem;
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
  font-family: inherit;
  resize: vertical;
}

.zs-field textarea {
  line-height: 1.7;
}

.form-actions {
  display: flex;
  gap: var(--zs-space-2);
  padding-top: var(--zs-space-2);
}

.right-panel {
  display: grid;
  gap: var(--zs-space-2);
  align-content: start;
}

.tab-bar {
  display: flex;
  gap: var(--zs-space-1);
  border-bottom: 1px solid var(--zs-color-border-soft);
  padding-bottom: var(--zs-space-2);
}

.tab-bar button {
  border: none;
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  padding: var(--zs-space-1) var(--zs-space-2);
  border-radius: 4px;
}

.tab-bar button.active {
  color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
}

.tab-content {
  display: grid;
  gap: var(--zs-space-2);
}

.tab-actions {
  display: flex;
  gap: var(--zs-space-2);
}

.index-status {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  margin: 0;
  display: flex;
  align-items: center;
  gap: var(--zs-space-2);
}

.index-model-badge {
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
  background: color-mix(in srgb, var(--zs-color-primary) 12%, transparent);
  color: var(--zs-color-primary);
}

.index-status-badge {
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 600;
}

.index-status-badge.error {
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.index-status-badge.stale {
  background: var(--zs-color-warning-soft, #fff8e1);
  color: var(--zs-color-warning, #f59e0b);
}

.index-status-badge.not-configured {
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-text-muted);
}

.index-error-hint {
  margin: 0;
  font-size: 0.72rem;
  color: var(--zs-color-danger, #ef4444);
  line-height: 1.4;
}

.chunk-list,
.link-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: var(--zs-space-2);
}

.chunk-item {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-2);
  display: grid;
  gap: var(--zs-space-1);
}

.chunk-head {
  display: flex;
  gap: var(--zs-space-2);
  align-items: center;
  flex-wrap: wrap;
}

.chunk-index {
  color: var(--zs-color-text-faint);
  font-size: 0.72rem;
  font-weight: 800;
}

.chunk-heading {
  color: var(--zs-color-text);
  font-size: 0.8rem;
  font-weight: 700;
}

.chunk-size {
  color: var(--zs-color-text-muted);
  font-size: 0.7rem;
  margin-left: auto;
}

.chunk-content {
  color: var(--zs-color-text);
  font-size: 0.78rem;
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 4;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.link-form {
  display: grid;
  gap: var(--zs-space-2);
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-3);
}

.link-item {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-2);
  display: grid;
  gap: 3px;
}

.link-info {
  display: flex;
  gap: var(--zs-space-1);
  align-items: center;
  flex-wrap: wrap;
}

.link-type {
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  border-radius: var(--zs-radius-pill);
  padding: 1px 6px;
  font-size: 0.68rem;
  font-weight: 700;
}

.link-relation {
  color: var(--zs-color-text-muted);
  font-size: 0.72rem;
  font-weight: 700;
}

.link-target-id {
  color: var(--zs-color-text-faint);
  font-size: 0.7rem;
  font-family: monospace;
}

.link-note {
  color: var(--zs-color-text);
  font-size: 0.78rem;
  margin: 0;
}

.link-delete {
  justify-self: start;
  border: none;
  background: transparent;
  color: var(--zs-color-danger);
  font-size: 0.72rem;
  cursor: pointer;
  padding: 0;
}

.link-delete:hover {
  text-decoration: underline;
}

@media (max-width: 1366px) {
  .knowledge-page {
    padding: var(--zs-space-4);
  }

  .knowledge-layout {
    grid-template-columns: minmax(220px, 260px) minmax(400px, 1fr);
  }

  .right-panel {
    grid-column: 1 / -1;
  }
}

@media (max-width: 900px) {
  .knowledge-layout {
    grid-template-columns: 1fr;
  }

  .list-panel {
    max-height: 280px;
    overflow-y: auto;
  }

  .source-extra-grid {
    grid-template-columns: 1fr;
  }
}
</style>
