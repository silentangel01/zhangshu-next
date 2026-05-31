<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { deleteOutline, getOutline, listChapterOutlines, updateOutline } from '@/entities/outline/api'
import type { OutlineImportance, OutlineItem, OutlineItemType, OutlineStatus } from '@/entities/outline/types'
import {
  outlineImportanceLabels,
  outlineItemTypeLabels,
  outlineStatusLabels,
} from '@/entities/outline/types'
import { cloudSyncManager } from '@/features/cloud/cloudSyncManager'
import OutlineTreeNode from './OutlineTreeNode.vue'

const props = defineProps<{
  projectId: string
  chapterId: string | null
  compact?: boolean
}>()

const outlines = ref<OutlineItem[]>([])
const isLoading = ref(false)
const isSaving = ref(false)
const errorMessage = ref('')
const selectedOutlineId = ref<string | null>(null)

const itemTypes: OutlineItemType[] = [
  'book_outline',
  'volume_outline',
  'chapter_outline',
  'scene',
  'plot_point',
  'note',
]
const statuses: OutlineStatus[] = ['planned', 'writing', 'done', 'abandoned']
const importances: OutlineImportance[] = ['normal', 'important', 'critical']

const form = reactive({
  title: '',
  content: '',
  item_type: 'chapter_outline' as OutlineItemType,
  status: 'planned' as OutlineStatus,
  importance: 'normal' as OutlineImportance,
})

const outlineTree = computed(() => buildOutlineTree(outlines.value))
const selectedOutline = computed(
  () => outlines.value.find((outline) => outline.id === selectedOutlineId.value) ?? null,
)

onMounted(() => {
  void refreshOutlines()
})

watch(
  () => props.chapterId,
  () => {
    selectedOutlineId.value = null
    void refreshOutlines()
  },
)

watch(selectedOutline, (outline) => {
  if (!outline) {
    resetForm()
    return
  }
  applyOutlineToForm(outline)
})

async function refreshOutlines() {
  if (!props.chapterId) {
    outlines.value = []
    return
  }

  isLoading.value = true
  errorMessage.value = ''

  try {
    outlines.value = await listChapterOutlines(props.chapterId)
    if (selectedOutlineId.value) {
      selectedOutlineId.value =
        outlines.value.find((outline) => outline.id === selectedOutlineId.value)?.id ?? null
    }
  } catch (error) {
    void error
    errorMessage.value = '加载章节细纲失败。'
  } finally {
    isLoading.value = false
  }
}

function buildOutlineTree(items: OutlineItem[]) {
  const nodes = new Map<string, { item: OutlineItem; children: Array<{ item: OutlineItem; children: any[] }> }>()

  for (const item of items) {
    nodes.set(item.id, { item, children: [] })
  }

  const roots: Array<{ item: OutlineItem; children: any[] }> = []
  for (const node of nodes.values()) {
    const parent = node.item.parent_id ? nodes.get(node.item.parent_id) : null
    if (parent) {
      parent.children.push(node)
    } else {
      roots.push(node)
    }
  }

  sortTreeNodes(roots)
  return roots
}

function sortTreeNodes(nodes: Array<{ item: OutlineItem; children: any[] }>) {
  nodes.sort((left, right) => {
    if (left.item.order_index !== right.item.order_index) {
      return left.item.order_index - right.item.order_index
    }
    return new Date(left.item.created_at).getTime() - new Date(right.item.created_at).getTime()
  })
  for (const node of nodes) {
    sortTreeNodes(node.children)
  }
}

function handleSelectOutline(outline: OutlineItem) {
  selectedOutlineId.value = outline.id
}

function handleBackToList() {
  selectedOutlineId.value = null
  resetForm()
}

async function handleSave() {
  if (!selectedOutline.value) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    const saved = await updateOutline(selectedOutline.value.id, {
      title: form.title,
      content: form.content,
      item_type: form.item_type,
      status: form.status,
      importance: form.importance,
    })
    selectedOutlineId.value = saved.id
    outlines.value = outlines.value.map((outline) => (outline.id === saved.id ? saved : outline))
    applyOutlineToForm(saved)
    cloudSyncManager.notifyDirty(props.projectId)
  } catch (error) {
    void error
    errorMessage.value = '保存章节细纲失败。'
  } finally {
    isSaving.value = false
  }
}

async function handleDelete() {
  if (!selectedOutline.value) {
    return
  }

  const confirmed = window.confirm('确认删除这条细纲吗？')
  if (!confirmed) {
    return
  }

  isSaving.value = true
  errorMessage.value = ''

  try {
    await deleteOutline(selectedOutline.value.id)
    selectedOutlineId.value = null
    resetForm()
    await refreshOutlines()
    cloudSyncManager.notifyDirty(props.projectId)
  } catch (error) {
    void error
    errorMessage.value = '删除章节细纲失败。'
  } finally {
    isSaving.value = false
  }
}

function applyOutlineToForm(outline: OutlineItem) {
  form.title = outline.title
  form.content = outline.content
  form.item_type = outline.item_type
  form.status = outline.status
  form.importance = outline.importance
}

function resetForm() {
  form.title = ''
  form.content = ''
  form.item_type = 'chapter_outline'
  form.status = 'planned'
  form.importance = 'normal'
}
</script>

<template>
  <aside class="chapter-outline-panel" :class="{ compact }">
    <template v-if="selectedOutline">
      <header class="panel-header detail-header">
        <div>
          <p class="eyebrow">当前章节细纲</p>
          <h2>{{ selectedOutline.title }}</h2>
        </div>
        <button class="text-button" type="button" @click="handleBackToList">返回列表</button>
      </header>

      <section class="detail-card">
        <div class="summary-grid">
          <div>
            <span class="field-label">类型</span>
            <strong>{{ outlineItemTypeLabels[selectedOutline.item_type] }}</strong>
          </div>
          <div>
            <span class="field-label">状态</span>
            <strong>{{ outlineStatusLabels[selectedOutline.status] }}</strong>
          </div>
          <div>
            <span class="field-label">重要程度</span>
            <strong>{{ outlineImportanceLabels[selectedOutline.importance] }}</strong>
          </div>
        </div>

        <label>
          <span>标题</span>
          <input v-model.trim="form.title" type="text" required />
        </label>

        <div class="form-grid">
          <label>
            <span>类型</span>
            <select v-model="form.item_type">
              <option v-for="type in itemTypes" :key="type" :value="type">
                {{ outlineItemTypeLabels[type] }}
              </option>
            </select>
          </label>
          <label>
            <span>状态</span>
            <select v-model="form.status">
              <option v-for="status in statuses" :key="status" :value="status">
                {{ outlineStatusLabels[status] }}
              </option>
            </select>
          </label>
          <label>
            <span>重要程度</span>
            <select v-model="form.importance">
              <option v-for="importance in importances" :key="importance" :value="importance">
                {{ outlineImportanceLabels[importance] }}
              </option>
            </select>
          </label>
        </div>

        <label>
          <span>内容</span>
          <textarea v-model="form.content" rows="8" />
        </label>

        <footer class="detail-actions">
          <button class="danger-button" type="button" :disabled="isSaving" @click="handleDelete">
            删除
          </button>
          <button class="primary-button" type="button" :disabled="isSaving" @click="handleSave">
            {{ isSaving ? '正在保存……' : '保存细纲' }}
          </button>
        </footer>
      </section>
    </template>

    <template v-else>
      <header class="panel-header">
        <div>
          <p class="eyebrow">规划层级</p>
          <h2>当前章节细纲</h2>
          <p class="panel-note">场景 / 剧情节点</p>
        </div>
      </header>

      <p v-if="isLoading" class="state-message">正在加载章节细纲……</p>
      <p v-else-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      <p v-else-if="outlines.length === 0" class="state-message">本章暂无大纲</p>

      <ul v-else class="outline-list">
        <OutlineTreeNode
          v-for="node in outlineTree"
          :key="node.item.id"
          :node="node"
          :depth="0"
          :selected-outline-id="selectedOutlineId"
          @select="handleSelectOutline"
        />
      </ul>
    </template>
  </aside>
</template>

<style scoped>
.chapter-outline-panel {
  display: grid;
  gap: 12px;
}

.chapter-outline-panel.compact {
  border: 0;
  padding: 0;
  background: transparent;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.detail-header {
  padding-bottom: 4px;
  border-bottom: 1px solid var(--zs-color-border-soft);
}

.eyebrow,
h2,
p {
  margin: 0;
}

.eyebrow {
  color: var(--zs-color-text-muted);
  font-size: 0.75rem;
  font-weight: 800;
}

h2 {
  color: var(--zs-color-text);
  font-size: 1rem;
}

.panel-note {
  margin-top: 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.82rem;
}

.text-button,
.primary-button,
.danger-button {
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  padding: 0 10px;
  background: var(--zs-color-surface);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 800;
  cursor: pointer;
}

.text-button {
  min-height: 30px;
  color: var(--zs-color-primary);
}

.detail-card {
  display: grid;
  gap: 14px;
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  padding: 14px;
  background: var(--zs-color-surface);
}

.summary-grid,
.form-grid {
  display: grid;
  gap: 10px;
}

.summary-grid {
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
}

.summary-grid div {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: 8px;
  padding: 10px;
  background: var(--zs-color-bg);
}

.field-label,
.summary-grid strong {
  display: block;
}

.field-label {
  margin-bottom: 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.75rem;
  font-weight: 800;
}

.summary-grid strong {
  color: var(--zs-color-text);
  font-size: 0.9rem;
}

label {
  display: grid;
  gap: 6px;
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
  font-weight: 800;
}

input,
select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  padding: 10px 12px;
  color: var(--zs-color-text);
  font: inherit;
}

textarea {
  resize: vertical;
  line-height: 1.7;
}

.detail-actions {
  display: flex;
  justify-content: space-between;
  gap: 10px;
}

.primary-button {
  border-color: transparent;
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.danger-button {
  border-color: var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}

.outline-list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.state-message,
.error-message {
  border: 1px dashed var(--zs-color-border);
  border-radius: 8px;
  padding: 14px;
  color: var(--zs-color-text-muted);
  text-align: center;
}

.error-message {
  border-color: var(--zs-color-danger);
  color: var(--zs-color-danger);
}
</style>
