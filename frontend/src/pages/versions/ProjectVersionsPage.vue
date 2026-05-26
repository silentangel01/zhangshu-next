<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import {
  cleanupVersions,
  compareVersions,
  createSnapshot,
  deleteVersion,
  getVersion,
  listVersions,
  restoreVersion,
  updateVersion,
} from '@/entities/version/api'
import type {
  CreateVersionSnapshotRequest,
  DiffLine,
  VersionCompareResponse,
  VersionDetail,
  VersionListItem,
} from '@/entities/version/types'
import {
  VERSION_ENTITY_TYPE_LABELS,
  VERSION_SOURCE_LABELS,
} from '@/entities/version/types'
import { formatDateTime } from '@/shared/utils/formatDateTime'

const route = useRoute()

const projectId = computed<string>(() => {
  const v = route.params.projectId
  return (Array.isArray(v) ? v[0] : v) ?? ''
})

// -- state
const versions = ref<VersionListItem[]>([])
const totalCount = ref(0)
const isLoading = ref(false)
const errorMessage = ref('')
const statusMessage = ref('')

const selectedVersion = ref<VersionDetail | null>(null)
const isDetailLoading = ref(false)

const compareResult = ref<VersionCompareResponse | null>(null)
const isComparing = ref(false)

const showRestoreDialog = ref(false)
const isRestoring = ref(false)

const showSnapshotDialog = ref(false)
const snapshotForm = ref({
  entity_type: 'chapter' as string,
  entity_id: '',
  label: '',
  note: '',
})

// -- filters
const filterEntityType = ref('')
const filterSource = ref('')
const filterPinned = ref<boolean | null>(null)
const filterKeyword = ref('')

const PAGE_SIZE = 30
const currentOffset = ref(0)

// -- computed
const entityTypeOptions = [
  { value: '', label: '全部类型' },
  { value: 'chapter', label: '正文' },
  { value: 'setting', label: '设定' },
  { value: 'character', label: '人物' },
  { value: 'clue', label: '伏笔' },
  { value: 'outline', label: '大纲' },
  { value: 'knowledge_source', label: '知识库' },
]

const sourceOptions = [
  { value: '', label: '全部来源' },
  { value: 'manual', label: '手动快照' },
  { value: 'autosave', label: '自动保存' },
  { value: 'before_restore', label: '恢复前备份' },
  { value: 'restore', label: '恢复记录' },
]

const hasMore = computed(() => currentOffset.value + PAGE_SIZE < totalCount.value)

// -- load
async function loadVersions() {
  isLoading.value = true
  errorMessage.value = ''
  try {
    const resp = await listVersions(projectId.value, {
      entity_type: filterEntityType.value || undefined,
      source: filterSource.value || undefined,
      pinned: filterPinned.value ?? undefined,
      keyword: filterKeyword.value || undefined,
      limit: PAGE_SIZE,
      offset: currentOffset.value,
    })
    versions.value = resp.versions
    totalCount.value = resp.total
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '加载版本列表失败'
  } finally {
    isLoading.value = false
  }
}

function handleFilterChange() {
  currentOffset.value = 0
  void loadVersions()
}

function handleLoadMore() {
  currentOffset.value += PAGE_SIZE
  void loadVersions()
}

// -- detail
async function selectVersion(version: VersionListItem) {
  isDetailLoading.value = true
  compareResult.value = null
  try {
    selectedVersion.value = await getVersion(projectId.value, version.version_ref)
  } catch {
    selectedVersion.value = null
  } finally {
    isDetailLoading.value = false
  }
}

// -- compare
async function handleCompare() {
  if (!selectedVersion.value) return
  isComparing.value = true
  try {
    compareResult.value = await compareVersions(projectId.value, {
      version_ref_a: selectedVersion.value.version_ref,
    })
  } catch {
    statusMessage.value = '对比失败'
  } finally {
    isComparing.value = false
  }
}

// -- restore
function openRestoreDialog() {
  if (!selectedVersion.value) return
  showRestoreDialog.value = true
}

async function handleRestore() {
  if (!selectedVersion.value) return
  isRestoring.value = true
  try {
    const resp = await restoreVersion(
      projectId.value,
      selectedVersion.value.version_ref,
    )
    statusMessage.value = resp.message
    showRestoreDialog.value = false
    selectedVersion.value = null
    compareResult.value = null
    await loadVersions()
  } catch (error) {
    statusMessage.value =
      error instanceof Error ? error.message : '恢复失败'
  } finally {
    isRestoring.value = false
  }
}

// -- pin / unpin
async function handleTogglePin(version: VersionListItem) {
  try {
    await updateVersion(projectId.value, version.version_ref, {
      is_pinned: !version.is_pinned,
    })
    await loadVersions()
  } catch {
    statusMessage.value = '更新标记失败'
  }
}

// -- delete
async function handleDelete(version: VersionListItem) {
  if (version.is_pinned) {
    statusMessage.value = '已标记的版本不能删除，请先取消标记'
    return
  }
  if (!confirm(`确定删除版本「${version.entity_title}」？此操作为软删除。`)) return
  try {
    await deleteVersion(projectId.value, version.version_ref)
    if (selectedVersion.value?.version_ref === version.version_ref) {
      selectedVersion.value = null
      compareResult.value = null
    }
    await loadVersions()
  } catch (error) {
    statusMessage.value =
      error instanceof Error ? error.message : '删除失败'
  }
}

// -- snapshot
function openSnapshotDialog() {
  snapshotForm.value = { entity_type: 'chapter', entity_id: '', label: '', note: '' }
  showSnapshotDialog.value = true
}

async function handleCreateSnapshot() {
  if (!snapshotForm.value.entity_id.trim()) {
    statusMessage.value = '请输入实体 ID'
    return
  }
  try {
    const req: CreateVersionSnapshotRequest = {
      entity_type: snapshotForm.value.entity_type as CreateVersionSnapshotRequest['entity_type'],
      entity_id: snapshotForm.value.entity_id.trim(),
      label: snapshotForm.value.label || null,
      note: snapshotForm.value.note || null,
    }
    await createSnapshot(projectId.value, req)
    showSnapshotDialog.value = false
    statusMessage.value = '快照已创建'
    await loadVersions()
  } catch (error) {
    statusMessage.value =
      error instanceof Error ? error.message : '创建快照失败'
  }
}

// -- cleanup
async function handleCleanup() {
  if (!confirm('确定清理 30 天前的未标记自动保存版本？')) return
  try {
    const resp = await cleanupVersions(projectId.value, 30)
    statusMessage.value = resp.message
    await loadVersions()
  } catch {
    statusMessage.value = '清理失败'
  }
}

// -- helpers
function getTypeLabel(type: string): string {
  return VERSION_ENTITY_TYPE_LABELS[type] ?? type
}

function getSourceLabel(source: string): string {
  return VERSION_SOURCE_LABELS[source] ?? source
}

function getDiffClass(tag: DiffLine['tag']): string {
  switch (tag) {
    case 'insert':
      return 'diff-insert'
    case 'delete':
      return 'diff-delete'
    default:
      return ''
  }
}

// clear status message after 3s
watch(statusMessage, (v) => {
  if (v) setTimeout(() => { statusMessage.value = '' }, 3000)
})

onMounted(() => {
  void loadVersions()
})
</script>

<template>
  <main class="versions-page">
    <header class="page-header">
      <div>
        <RouterLink class="back-link" :to="`/projects/${projectId}`">返回写作页</RouterLink>
        <p class="eyebrow">版本中心</p>
        <h1>版本管理</h1>
      </div>
      <div class="header-actions">
        <button class="secondary-button" type="button" @click="openSnapshotDialog">创建快照</button>
        <button class="ghost-button" type="button" @click="handleCleanup">清理旧版本</button>
        <RouterLink class="secondary-link" to="/projects">项目列表</RouterLink>
      </div>
    </header>

    <p v-if="statusMessage" class="status-banner" role="status">{{ statusMessage }}</p>
    <p v-if="errorMessage" class="error-banner" role="alert">{{ errorMessage }}</p>

    <section class="filters-bar">
      <select v-model="filterEntityType" @change="handleFilterChange">
        <option v-for="opt in entityTypeOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>

      <select v-model="filterSource" @change="handleFilterChange">
        <option v-for="opt in sourceOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>

      <select v-model="filterPinned" @change="handleFilterChange">
        <option :value="null">全部标记</option>
        <option :value="true">已标记</option>
        <option :value="false">未标记</option>
      </select>

      <input
        v-model="filterKeyword"
        type="search"
        placeholder="搜索版本…"
        @keydown.enter="handleFilterChange"
      />
    </section>

    <div class="versions-layout">
      <section class="version-list-panel">
        <p class="list-header">
          共 {{ totalCount }} 个版本
          <span v-if="isLoading" class="loading-indicator">加载中…</span>
        </p>

        <div v-if="versions.length === 0 && !isLoading" class="empty-state">
          暂无版本记录
        </div>

        <article
          v-for="v in versions"
          :key="v.version_ref"
          class="version-card"
          :class="{ active: selectedVersion?.version_ref === v.version_ref }"
          @click="selectVersion(v)"
        >
          <div class="version-card-header">
            <span class="type-pill">{{ getTypeLabel(v.entity_type) }}</span>
            <span class="source-pill">{{ getSourceLabel(v.source) }}</span>
          </div>
          <h3 class="version-title">{{ v.entity_title || '(无标题)' }}</h3>
          <p class="version-meta">
            <span v-if="v.label" class="version-label">{{ v.label }}</span>
            <span>{{ formatDateTime(v.created_at) }}</span>
          </p>
          <div class="version-actions-inline">
            <button
              class="icon-button"
              type="button"
              :title="v.is_pinned ? '取消标记' : '标记'"
              @click.stop="handleTogglePin(v)"
            >
              {{ v.is_pinned ? '★' : '☆' }}
            </button>
            <button
              v-if="!v.is_pinned"
              class="icon-button danger"
              type="button"
              title="删除"
              @click.stop="handleDelete(v)"
            >
              ✕
            </button>
          </div>
        </article>

        <button
          v-if="hasMore"
          class="load-more-button"
          type="button"
          :disabled="isLoading"
          @click="handleLoadMore"
        >
          加载更多
        </button>
      </section>

      <section class="version-detail-panel">
        <template v-if="selectedVersion">
          <div class="detail-header">
            <div>
              <h2>{{ selectedVersion.entity_title }}</h2>
              <p class="detail-meta">
                {{ getTypeLabel(selectedVersion.entity_type) }} ·
                {{ getSourceLabel(selectedVersion.source) }} ·
                {{ formatDateTime(selectedVersion.created_at) }}
                <span v-if="selectedVersion.is_pinned" class="pinned-badge">★ 已标记</span>
              </p>
            </div>
            <div class="detail-actions">
              <button
                class="secondary-button"
                type="button"
                :disabled="isComparing"
                @click="handleCompare"
              >
                {{ isComparing ? '对比中…' : '对比当前' }}
              </button>
              <button class="primary-button" type="button" @click="openRestoreDialog">
                恢复
              </button>
            </div>
          </div>

          <p v-if="selectedVersion.note" class="detail-note">{{ selectedVersion.note }}</p>

          <div v-if="isDetailLoading" class="loading-state">加载中…</div>

          <template v-else-if="compareResult">
            <h3 class="diff-title">
              对比：{{ compareResult.title_a }} → {{ compareResult.title_b || '当前内容' }}
            </h3>
            <div class="diff-view">
              <pre
                v-for="(line, idx) in compareResult.diff"
                :key="idx"
                class="diff-line"
                :class="getDiffClass(line.tag)"
              >{{ line.tag === 'delete' ? '- ' : line.tag === 'insert' ? '+ ' : '  ' }}{{ line.tag === 'delete' ? line.old_text : line.tag === 'insert' ? line.new_text : line.old_text }}</pre>
            </div>
          </template>

          <template v-else>
            <h3>版本内容</h3>
            <pre class="content-view">{{ selectedVersion.content_text }}</pre>
          </template>
        </template>

        <div v-else class="empty-state detail-empty">
          选择左侧版本查看详情
        </div>
      </section>
    </div>

    <!-- Restore dialog -->
    <Teleport to="body">
      <div v-if="showRestoreDialog" class="dialog-overlay" @click.self="showRestoreDialog = false">
        <div class="dialog-card">
          <h2>确认恢复</h2>
          <p>即将恢复「{{ selectedVersion?.entity_title }}」到所选版本的状态。</p>
          <ul class="restore-warnings">
            <li>当前内容会被覆盖。</li>
            <li>系统会先创建一个恢复前快照，以便撤销。</li>
            <li>此操作只恢复当前实体，不影响其他资料。</li>
          </ul>
          <div class="dialog-actions">
            <button class="secondary-button" type="button" @click="showRestoreDialog = false">
              取消
            </button>
            <button
              class="primary-button danger-bg"
              type="button"
              :disabled="isRestoring"
              @click="handleRestore"
            >
              {{ isRestoring ? '正在恢复…' : '确认恢复' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Snapshot dialog -->
    <Teleport to="body">
      <div
        v-if="showSnapshotDialog"
        class="dialog-overlay"
        @click.self="showSnapshotDialog = false"
      >
        <div class="dialog-card">
          <h2>创建版本快照</h2>
          <form @submit.prevent="handleCreateSnapshot">
            <label class="field-group">
              <span>实体类型</span>
              <select v-model="snapshotForm.entity_type">
                <option value="chapter">正文</option>
                <option value="setting">设定</option>
                <option value="character">人物</option>
                <option value="clue">伏笔</option>
                <option value="outline">大纲</option>
                <option value="knowledge_source">知识库</option>
              </select>
            </label>
            <label class="field-group">
              <span>实体 ID</span>
              <input v-model="snapshotForm.entity_id" type="text" placeholder="粘贴实体 ID" />
            </label>
            <label class="field-group">
              <span>标签（可选）</span>
              <input v-model="snapshotForm.label" type="text" placeholder="例如：初稿完成" />
            </label>
            <label class="field-group">
              <span>备注（可选）</span>
              <input v-model="snapshotForm.note" type="text" placeholder="备注说明" />
            </label>
            <div class="dialog-actions">
              <button
                class="secondary-button"
                type="button"
                @click="showSnapshotDialog = false"
              >
                取消
              </button>
              <button class="primary-button" type="submit">创建</button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </main>
</template>

<style scoped>
.versions-page {
  min-height: 100vh;
  box-sizing: border-box;
  padding: var(--zs-space-8) var(--zs-space-5);
  background: var(--zs-color-bg);
  color: var(--zs-color-text);
}

.page-header,
.filters-bar,
.versions-layout,
.status-banner,
.error-banner {
  max-width: 1200px;
  margin-right: auto;
  margin-left: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: var(--zs-space-4);
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
}

h1 {
  margin: 0;
  font-size: 1.8rem;
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
  min-height: 38px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 14px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font-weight: 800;
  text-decoration: none;
}

.filters-bar {
  display: flex;
  gap: var(--zs-space-3);
  flex-wrap: wrap;
  margin-bottom: var(--zs-space-5);
}

.filters-bar select,
.filters-bar input {
  min-height: 38px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
}

.filters-bar input {
  flex: 1;
  min-width: 160px;
}

.versions-layout {
  display: grid;
  grid-template-columns: 360px 1fr;
  gap: var(--zs-space-5);
}

.version-list-panel {
  display: grid;
  gap: var(--zs-space-2);
  align-content: start;
}

.list-header {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
  font-weight: 800;
  display: flex;
  justify-content: space-between;
}

.loading-indicator {
  color: var(--zs-color-primary);
}

.version-card {
  display: grid;
  gap: 6px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: 12px;
  background: var(--zs-color-surface);
  cursor: pointer;
  transition: border-color 0.15s;
}

.version-card:hover {
  border-color: var(--zs-color-primary);
}

.version-card.active {
  border-color: var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
}

.version-card-header {
  display: flex;
  gap: var(--zs-space-2);
}

.type-pill,
.source-pill {
  font-size: 0.72rem;
  font-weight: 800;
  border-radius: 999px;
  padding: 2px 8px;
}

.type-pill {
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
}

.source-pill {
  background: var(--zs-color-info-soft, rgba(59, 130, 246, 0.1));
  color: var(--zs-color-info);
}

.version-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 800;
  line-height: 1.3;
}

.version-meta {
  margin: 0;
  display: flex;
  gap: var(--zs-space-2);
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
}

.version-label {
  background: var(--zs-color-warning-soft, rgba(245, 158, 11, 0.1));
  color: var(--zs-color-warning);
  border-radius: 4px;
  padding: 0 6px;
  font-weight: 800;
}

.version-actions-inline {
  display: flex;
  gap: 4px;
}

.icon-button {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
  cursor: pointer;
}

.icon-button.danger:hover {
  color: var(--zs-color-danger);
  border-color: var(--zs-color-danger);
}

.version-detail-panel {
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-5);
  background: var(--zs-color-surface);
  min-height: 400px;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--zs-space-4);
  margin-bottom: var(--zs-space-4);
}

.detail-header h2 {
  margin: 0 0 6px;
}

.detail-meta {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.85rem;
}

.pinned-badge {
  color: var(--zs-color-warning);
  font-weight: 800;
}

.detail-actions {
  display: flex;
  gap: var(--zs-space-2);
  flex-shrink: 0;
}

.detail-note {
  margin: 0 0 var(--zs-space-4);
  padding: 10px 14px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-bg);
  color: var(--zs-color-text-muted);
  font-size: 0.88rem;
}

.diff-title {
  margin: 0 0 var(--zs-space-3);
  font-size: 0.95rem;
  color: var(--zs-color-text-muted);
}

.diff-view {
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  overflow: auto;
  max-height: 60vh;
  background: var(--zs-color-bg);
}

.diff-line {
  margin: 0;
  padding: 2px 12px;
  font-size: 0.82rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.diff-insert {
  background: rgba(34, 197, 94, 0.1);
  color: var(--zs-color-success);
}

.diff-delete {
  background: rgba(239, 68, 68, 0.1);
  color: var(--zs-color-danger);
}

.content-view {
  margin: 0;
  padding: var(--zs-space-4);
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  background: var(--zs-color-bg);
  font-size: 0.88rem;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 60vh;
  overflow: auto;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 120px;
  border: 1px dashed var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

.detail-empty {
  min-height: 400px;
}

.loading-state {
  padding: var(--zs-space-4);
  text-align: center;
  color: var(--zs-color-text-muted);
}

.load-more-button {
  min-height: 38px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 14px;
  background: var(--zs-color-surface);
  color: var(--zs-color-primary);
  font: inherit;
  font-weight: 800;
  cursor: pointer;
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
  opacity: 0.65;
  cursor: wait;
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

.ghost-button {
  border-color: var(--zs-color-border);
  background: transparent;
  color: var(--zs-color-text-muted);
}

.danger-bg {
  background: var(--zs-color-danger);
}

.status-banner {
  margin-bottom: var(--zs-space-4);
  padding: 10px 14px;
  border: 1px solid var(--zs-color-success);
  border-radius: var(--zs-radius-md);
  background: rgba(34, 197, 94, 0.08);
  color: var(--zs-color-success);
  font-weight: 800;
}

.error-banner {
  margin-bottom: var(--zs-space-4);
  padding: 10px 14px;
  border: 1px solid var(--zs-color-danger);
  border-radius: var(--zs-radius-md);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
  font-weight: 800;
}

/* Dialogs */
.dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: grid;
  place-items: center;
  background: rgba(0, 0, 0, 0.45);
}

.dialog-card {
  width: 90%;
  max-width: 480px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-5);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-sm);
}

.dialog-card h2 {
  margin: 0 0 var(--zs-space-4);
}

.dialog-card form {
  display: grid;
  gap: var(--zs-space-3);
}

.field-group {
  display: grid;
  gap: 6px;
  color: var(--zs-color-text-muted);
  font-weight: 800;
  font-size: 0.88rem;
}

.field-group input,
.field-group select {
  min-height: 38px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--zs-space-3);
  margin-top: var(--zs-space-4);
}

.restore-warnings {
  margin: 0 0 var(--zs-space-3);
  padding-left: 20px;
  color: var(--zs-color-text-muted);
  line-height: 1.8;
}

@media (max-width: 860px) {
  .versions-layout {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    flex-wrap: wrap;
  }
}
</style>
