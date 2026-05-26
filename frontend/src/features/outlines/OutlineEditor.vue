<script setup lang="ts">
import { computed, reactive, watch } from 'vue'

import type { Chapter } from '@/entities/chapter/types'
import type {
  OutlineImportance,
  OutlineItem,
  OutlineItemUpdatePayload,
  OutlineItemType,
  OutlineStatus,
} from '@/entities/outline/types'
import {
  outlineImportanceLabels,
  outlineItemTypeLabels,
  outlineStatusLabels,
} from '@/entities/outline/types'
import type { Volume } from '@/entities/volume/types'
import { formatDateTime } from '@/shared/utils/formatDateTime'

const props = defineProps<{
  outline: OutlineItem
  outlines: OutlineItem[]
  volumes: Volume[]
  chapters: Chapter[]
  isSaving: boolean
}>()

const emit = defineEmits<{
  save: [payload: OutlineItemUpdatePayload]
  delete: []
}>()

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
  item_type: 'book_outline' as OutlineItemType,
  status: 'planned' as OutlineStatus,
  importance: 'normal' as OutlineImportance,
  parent_id: '',
  volume_id: '',
  chapter_id: '',
  order_index: 0,
})

const parentOptions = computed(() =>
  props.outlines.filter((outline) => outline.id !== props.outline.id),
)

watch(
  () => props.outline,
  (outline) => {
    form.title = outline.title
    form.content = outline.content
    form.item_type = outline.item_type
    form.status = outline.status
    form.importance = outline.importance
    form.parent_id = outline.parent_id ?? ''
    form.volume_id = outline.volume_id ?? ''
    form.chapter_id = outline.chapter_id ?? ''
    form.order_index = outline.order_index
  },
  { immediate: true },
)

function handleSave() {
  emit('save', {
    title: form.title,
    content: form.content,
    item_type: form.item_type,
    status: form.status,
    importance: form.importance,
    parent_id: form.parent_id || null,
    volume_id: form.volume_id || null,
    chapter_id: form.chapter_id || null,
    order_index: Number(form.order_index) || 0,
  })
}
</script>

<template>
  <form class="outline-editor" @submit.prevent="handleSave">
    <header class="editor-header">
      <div>
        <p class="eyebrow">大纲详情</p>
        <h2>{{ outline.title }}</h2>
      </div>
      <span class="version">v{{ outline.version }}</span>
    </header>

    <label>
      <span>标题</span>
      <input v-model.trim="form.title" type="text" required />
    </label>

    <label>
      <span>内容</span>
      <textarea v-model="form.content" rows="8" />
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

      <label>
        <span>排序序号</span>
        <input v-model.number="form.order_index" type="number" min="0" />
      </label>
    </div>

    <div class="form-grid">
      <label>
        <span>父级条目</span>
        <select v-model="form.parent_id">
          <option value="">无父级</option>
          <option v-for="parent in parentOptions" :key="parent.id" :value="parent.id">
            {{ parent.title }}
          </option>
        </select>
      </label>

      <label>
        <span>绑定分卷</span>
        <select v-model="form.volume_id">
          <option value="">不绑定分卷</option>
          <option v-for="volume in volumes" :key="volume.id" :value="volume.id">
            {{ volume.title }}
          </option>
        </select>
      </label>

      <label>
        <span>绑定章节</span>
        <select v-model="form.chapter_id">
          <option value="">不绑定章节</option>
          <option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">
            {{ chapter.title }}
          </option>
        </select>
      </label>
    </div>

    <dl class="metadata-grid">
      <div>
        <dt>创建时间</dt>
        <dd>{{ formatDateTime(outline.created_at) }}</dd>
      </div>
      <div>
        <dt>更新时间</dt>
        <dd>{{ formatDateTime(outline.updated_at) }}</dd>
      </div>
    </dl>

    <footer class="editor-actions">
      <button class="danger-button" type="button" :disabled="isSaving" @click="emit('delete')">
        删除大纲
      </button>
      <button class="primary-button" type="submit" :disabled="isSaving || !form.title.trim()">
        {{ isSaving ? '正在保存……' : '保存大纲' }}
      </button>
    </footer>
  </form>
</template>

<style scoped>
.outline-editor {
  display: grid;
  gap: var(--zs-space-4);
}

.editor-header,
.editor-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--zs-space-3);
}

.eyebrow {
  margin: 0 0 var(--zs-space-1);
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

h2 {
  margin: 0;
  font-size: 1.35rem;
}

label {
  display: grid;
  gap: 7px;
  color: var(--zs-color-text-muted);
  font-weight: 800;
}

input,
select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 10px 12px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
}

textarea {
  resize: vertical;
  line-height: 1.7;
}

.form-grid,
.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--zs-space-3);
}

.metadata-grid {
  margin: 0;
}

.metadata-grid div {
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-3);
  background: var(--zs-color-surface-soft);
}

dt {
  margin: 0 0 4px;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  font-weight: 800;
}

dd {
  margin: 0;
  color: var(--zs-color-text);
  font-weight: 800;
}

.version {
  flex: 0 0 auto;
  border-radius: var(--zs-radius-pill);
  padding: 4px 9px;
  background: var(--zs-color-info-soft);
  color: var(--zs-color-info);
  font-size: 0.78rem;
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

.danger-button {
  border-color: var(--zs-color-danger);
  background: var(--zs-color-danger-soft);
  color: var(--zs-color-danger);
}
</style>
