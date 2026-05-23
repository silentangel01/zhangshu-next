<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import {
  buildSourceEmbeddings,
  createKnowledgeLink,
  createKnowledgeSource,
  deleteKnowledgeLink,
  deleteKnowledgeSource,
  getKnowledgeIndexStatus,
  getKnowledgeSource,
  listKnowledgeChunks,
  listKnowledgeLinks,
  listKnowledgeSources,
  rebuildKnowledgeChunks,
  rebuildKnowledgeIndex,
  updateKnowledgeSource,
} from '@/entities/knowledge/api'
import type {
  CreateKnowledgeLinkPayload,
  CreateKnowledgeSourcePayload,
  KnowledgeChunk,
  KnowledgeCredibility,
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
import KnowledgeImportDialog from '@/features/knowledge/KnowledgeImportDialog.vue'
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
const viewMode = ref<'browse' | 'search' | 'ask' | 'summary'>('browse')
const indexStatus = ref<KnowledgeIndexStatus | null>(null)
const isIndexing = ref(false)

const sourceTypes: KnowledgeSourceType[] = ['note', 'file', 'webpage', 'book', 'quote', 'custom']
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

async function handleRebuildChunks() {
  if (!selectedSource.value) return
  isSaving.value = true
  errorMessage.value = ''
  try {
    chunks.value = await rebuildKnowledgeChunks(selectedSource.value.id)
    successMessage.value = `已重新生成 ${chunks.value.length} 个分块`
  } catch {
    errorMessage.value = '重建分块失败，请稍后重试。'
  } finally {
    isSaving.value = false
  }
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
    indexStatus.value = await getKnowledgeIndexStatus(projectId.value)
  } catch {
    // Silently fail - index status is optional display
  }
}

async function handleRebuildIndex() {
  isIndexing.value = true
  errorMessage.value = ''
  try {
    const result = await rebuildKnowledgeIndex(projectId.value)
    successMessage.value = `已重建 ${result.indexed_count} 个向量索引（${result.model_name}）`
    await loadIndexStatus()
  } catch {
    errorMessage.value = '重建向量索引失败，请稍后重试。'
  } finally {
    isIndexing.value = false
  }
}

async function handleBuildSourceEmbeddings() {
  if (!selectedSource.value) return
  isIndexing.value = true
  errorMessage.value = ''
  try {
    const result = await buildSourceEmbeddings(selectedSource.value.id)
    successMessage.value = `已为当前资料生成 ${result.indexed_count} 个向量索引`
    await loadIndexStatus()
  } catch {
    errorMessage.value = '生成向量索引失败，请稍后重试。'
  } finally {
    isIndexing.value = false
  }
}

function handleImported() {
  isImportDialogOpen.value = false
  void loadSources()
}

onMounted(() => {
  void loadSources()
  void loadIndexStatus()
})
</script>

<template>
  <main class="knowledge-page material-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
        <p class="eyebrow">外部参考资料</p>
        <h1>知识库</h1>
        <p class="page-note">
          知识库用于保存外部参考资料，不会自动写入本书设定。
        </p>
      </div>
      <div class="header-actions">
        <button
          class="secondary-button"
          type="button"
          :disabled="isSaving"
          @click="isImportDialogOpen = true"
        >
          导入
        </button>
        <button class="primary-button" type="button" :disabled="isSaving" @click="handleNewSource">
          新建资料
        </button>
      </div>
    </header>

    <div class="knowledge-toolbar">
      <div class="view-mode-toggle">
        <button
          type="button"
          class="mode-button"
          :class="{ active: viewMode === 'browse' }"
          @click="viewMode = 'browse'"
        >
          浏览
        </button>
        <button
          type="button"
          class="mode-button"
          :class="{ active: viewMode === 'search' }"
          @click="viewMode = 'search'"
        >
          检索
        </button>
        <button
          type="button"
          class="mode-button"
          :class="{ active: viewMode === 'ask' }"
          @click="viewMode = 'ask'"
        >
          问答
        </button>
        <button
          type="button"
          class="mode-button"
          :class="{ active: viewMode === 'summary' }"
          @click="viewMode = 'summary'"
        >
          摘要
        </button>
      </div>

      <template v-if="viewMode === 'browse'">
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
      </template>
    </div>

    <section v-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</section>
    <section v-if="successMessage" class="success-banner" role="status">{{ successMessage }}</section>

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

    <template v-else>
      <section v-if="isLoading" class="state-message">正在加载知识库…</section>

    <section v-else class="knowledge-layout material-layout">
      <aside class="list-panel material-list-panel">
        <p v-if="sources.length === 0" class="empty-state">
          暂无知识资料，点击"新建资料"开始收集。
        </p>
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
          <p>选择左侧资料查看详情，或点击"新建资料"创建。</p>
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

          <div class="form-row">
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
          </div>

          <label class="zs-field">
            <span class="zs-field-label">来源</span>
            <input v-model="form.source_uri" type="text" placeholder="URL / 书名 / 出处" />
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
            <span class="zs-field-label">正文</span>
            <textarea v-model="form.content" rows="12" placeholder="资料正文内容" />
          </label>

          <label class="zs-field">
            <span class="zs-field-label">标签</span>
            <input v-model="form.tags" type="text" placeholder="多个标签用逗号分隔" />
          </label>

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

      <aside class="right-panel material-side-panel">
        <div v-if="!selectedSource" class="empty-side">
          <p>选择资料后查看分块和关联</p>
        </div>
        <template v-else>
          <div class="tab-bar">
            <button
              type="button"
              :class="{ active: rightTab === 'chunks' }"
              @click="rightTab = 'chunks'"
            >
              分块预览（{{ chunks.length }}）
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
            <div class="tab-actions">
              <button
                class="secondary-button"
                type="button"
                :disabled="isSaving"
                @click="handleRebuildChunks"
              >
                重建分块
              </button>
              <button
                class="secondary-button"
                type="button"
                :disabled="isIndexing || !selectedSource"
                @click="handleBuildSourceEmbeddings"
              >
                {{ isIndexing ? '索引中...' : '生成向量' }}
              </button>
            </div>
            <p v-if="indexStatus" class="index-status">
              向量索引：{{ indexStatus.indexed_chunks }} / {{ indexStatus.total_chunks }}
              <button
                class="link-button"
                type="button"
                :disabled="isIndexing"
                @click="handleRebuildIndex"
              >
                重建全部索引
              </button>
            </p>
            <p v-if="chunks.length === 0" class="empty-hint">
              暂无分块。填写正文内容后点击"重建分块"自动生成。
            </p>
            <ul v-else class="chunk-list">
              <li v-for="chunk in chunks" :key="chunk.id" class="chunk-item">
                <div class="chunk-head">
                  <span class="chunk-index">#{{ chunk.chunk_index + 1 }}</span>
                  <span v-if="chunk.heading" class="chunk-heading">{{ chunk.heading }}</span>
                  <span class="chunk-size">{{ chunk.token_count }} 字</span>
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
        </template>
      </aside>
    </section>
    </template>

    <KnowledgeImportDialog
      v-if="isImportDialogOpen"
      :project-id="projectId"
      @close="isImportDialogOpen = false"
      @imported="handleImported"
    />
  </main>
</template>

<style scoped>
.knowledge-page {
  display: grid;
  gap: 14px;
  padding: 20px;
  min-height: 100vh;
  background: var(--zs-canvas-bg, var(--zs-color-bg));
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.back-link {
  color: var(--zs-color-primary);
  font-size: 0.82rem;
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.eyebrow {
  color: var(--zs-color-text-muted);
  font-size: 0.75rem;
  font-weight: 800;
  margin: 0;
}

h1 {
  color: var(--zs-color-text);
  font-size: 1.25rem;
  margin: 2px 0 0;
}

.page-note {
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
  line-height: 1.6;
  margin: 4px 0 0;
}

.primary-button {
  background: var(--zs-color-primary);
  border: 1px solid var(--zs-color-primary);
  border-radius: 6px;
  color: var(--zs-color-on-primary);
  cursor: pointer;
  font-size: 0.84rem;
  font-weight: 700;
  padding: 6px 14px;
}

.primary-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.secondary-button {
  background: var(--zs-color-surface);
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  color: var(--zs-color-text);
  cursor: pointer;
  font-size: 0.82rem;
  padding: 5px 12px;
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
  color: var(--zs-color-danger);
}

.danger-button:hover {
  background: var(--zs-color-danger-soft);
}

.knowledge-toolbar {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: flex-start;
}

.view-mode-toggle {
  display: flex;
  gap: 0;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
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

.search-group {
  display: flex;
  gap: 6px;
  flex: 1;
  min-width: 200px;
}

.search-group input {
  flex: 1;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  padding: 6px 10px;
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
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  background: var(--zs-color-surface);
  min-width: 220px;
  margin-top: 4px;
  box-shadow: var(--zs-shadow-card, 0 4px 16px rgb(0 0 0 / 8%));
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
  gap: 6px;
  justify-content: flex-end;
  padding-top: 4px;
}

.error-banner,
.success-banner {
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.82rem;
}

.error-banner {
  background: var(--zs-color-danger-soft);
  border: 1px solid var(--zs-color-danger);
  color: var(--zs-color-danger);
}

.success-banner {
  background: var(--zs-color-success-soft, #f0fdf4);
  border: 1px solid var(--zs-color-success, #22c55e);
  color: var(--zs-color-success, #166534);
}

.state-message {
  text-align: center;
  color: var(--zs-color-text-muted);
  padding: 40px 20px;
}

.knowledge-layout {
  display: grid;
  grid-template-columns: 260px 1fr 300px;
  gap: 14px;
  min-height: 500px;
}

.list-panel {
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  background: var(--zs-color-surface);
  padding: 10px;
  overflow-y: auto;
  max-height: calc(100vh - 260px);
}

.empty-state,
.empty-hint {
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
  text-align: center;
  padding: 20px 8px;
}

.source-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
}

.source-item button {
  display: grid;
  gap: 3px;
  width: 100%;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 8px;
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
  border-radius: 999px;
  padding: 1px 6px;
  font-size: 0.68rem;
  font-weight: 700;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
}

.status-badge.archived {
  background: var(--zs-color-text-faint-bg, #f1f5f9);
  color: var(--zs-color-text-muted);
}

.credibility-badge.high {
  background: var(--zs-color-success-soft, #f0fdf4);
  color: var(--zs-color-success, #166534);
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

.detail-panel {
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  background: var(--zs-color-surface);
  padding: 16px;
  overflow-y: auto;
  max-height: calc(100vh - 260px);
}

.empty-detail,
.empty-side {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--zs-color-text-muted);
  font-size: 0.84rem;
}

.detail-form {
  display: grid;
  gap: 10px;
}

.form-head h2 {
  margin: 0;
  font-size: 1rem;
  color: var(--zs-color-text);
}

.form-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
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
  border-radius: 6px;
  padding: 6px 10px;
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
  gap: 8px;
  padding-top: 6px;
}

.right-panel {
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  background: var(--zs-color-surface);
  padding: 10px;
  overflow-y: auto;
  max-height: calc(100vh - 260px);
  display: grid;
  gap: 8px;
  align-content: start;
}

.tab-bar {
  display: flex;
  gap: 4px;
  border-bottom: 1px solid var(--zs-color-border-soft, var(--zs-color-border));
  padding-bottom: 6px;
}

.tab-bar button {
  border: none;
  background: transparent;
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
  font-weight: 700;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.tab-bar button.active {
  color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
}

.tab-content {
  display: grid;
  gap: 8px;
}

.tab-actions {
  display: flex;
  gap: 6px;
}

.index-status {
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;
}

.link-button {
  border: none;
  background: none;
  color: var(--zs-color-primary);
  font-size: 0.78rem;
  cursor: pointer;
  padding: 0;
  text-decoration: underline;
}

.link-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.link-button:hover:not(:disabled) {
  color: var(--zs-color-primary-hover);
}

.chunk-list,
.link-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 6px;
}

.chunk-item {
  border: 1px solid var(--zs-color-border-soft, var(--zs-color-border));
  border-radius: 6px;
  padding: 8px;
  display: grid;
  gap: 4px;
}

.chunk-head {
  display: flex;
  gap: 6px;
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
  gap: 6px;
  border: 1px dashed var(--zs-color-border);
  border-radius: 6px;
  padding: 10px;
}

.link-item {
  border: 1px solid var(--zs-color-border-soft, var(--zs-color-border));
  border-radius: 6px;
  padding: 8px;
  display: grid;
  gap: 3px;
}

.link-info {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-wrap: wrap;
}

.link-type {
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  border-radius: 999px;
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

@media (max-width: 1100px) {
  .knowledge-layout {
    grid-template-columns: 220px 1fr;
  }

  .right-panel {
    grid-column: 1 / -1;
    max-height: none;
  }
}

@media (max-width: 760px) {
  .knowledge-layout {
    grid-template-columns: 1fr;
  }

  .list-panel {
    max-height: 240px;
  }

  .detail-panel {
    max-height: none;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
