<script setup lang="ts">
import { reactive } from 'vue'

import type { Chapter } from '@/entities/chapter/types'
import type {
  OutlineImportance,
  OutlineItem,
  OutlineItemCreatePayload,
  OutlineItemType,
  OutlineStatus,
} from '@/entities/outline/types'
import {
  outlineImportanceLabels,
  outlineItemTypeLabels,
  outlineStatusLabels,
} from '@/entities/outline/types'
import type { Volume } from '@/entities/volume/types'

defineProps<{
  outlines: OutlineItem[]
  volumes: Volume[]
  chapters: Chapter[]
  isSaving: boolean
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: OutlineItemCreatePayload]
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

function handleSubmit() {
  emit('submit', {
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
  <div class="dialog-backdrop" role="presentation" @click.self="emit('close')">
    <form class="dialog" @submit.prevent="handleSubmit">
      <header class="dialog-header">
        <h2>新建大纲条目</h2>
        <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')">×</button>
      </header>

      <label>
        <span>标题</span>
        <input v-model.trim="form.title" type="text" required />
      </label>

      <label>
        <span>内容</span>
        <textarea v-model="form.content" rows="5" />
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
            <option v-for="outline in outlines" :key="outline.id" :value="outline.id">
              {{ outline.title }}
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

      <footer class="dialog-actions">
        <button class="secondary-button" type="button" @click="emit('close')">取消</button>
        <button class="primary-button" type="submit" :disabled="isSaving || !form.title.trim()">
          {{ isSaving ? '正在保存……' : '新建大纲条目' }}
        </button>
      </footer>
    </form>
  </div>
</template>

<style scoped>
.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgb(15 23 42 / 42%);
}

.dialog {
  display: grid;
  gap: 16px;
  width: min(760px, 100%);
  max-height: min(90vh, 760px);
  overflow: auto;
  box-sizing: border-box;
  border-radius: 8px;
  padding: 22px;
  background: #ffffff;
  color: #111827;
}

.dialog-header,
.dialog-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

h2 {
  margin: 0;
  font-size: 1.25rem;
}

label {
  display: grid;
  gap: 7px;
  color: #4b5563;
  font-weight: 800;
}

input,
select,
textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 10px 12px;
  color: #111827;
  font: inherit;
}

textarea {
  resize: vertical;
  line-height: 1.7;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
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

.icon-button {
  width: 36px;
  padding: 0;
  border-color: #cfd7e3;
  background: #ffffff;
  color: #374151;
  font-size: 1.2rem;
}

.primary-button {
  background: #2563eb;
  color: #ffffff;
}

.secondary-button {
  border-color: #cfd7e3;
  background: #ffffff;
  color: #374151;
}
</style>
