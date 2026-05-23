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
  <div class="zs-dialog" role="presentation" @click.self="emit('close')">
    <form class="zs-dialog-content" @submit.prevent="handleSubmit">
      <header class="zs-dialog-header">
        <h2>新建大纲条目</h2>
        <button class="zs-icon-button" type="button" aria-label="关闭" @click="emit('close')">×</button>
      </header>

      <label class="zs-field">
        <span>标题</span>
        <input v-model.trim="form.title" type="text" required />
      </label>

      <label class="zs-field">
        <span>内容</span>
        <textarea v-model="form.content" rows="5" />
      </label>

      <div class="form-grid">
        <label class="zs-field">
          <span>类型</span>
          <select v-model="form.item_type">
            <option v-for="type in itemTypes" :key="type" :value="type">
              {{ outlineItemTypeLabels[type] }}
            </option>
          </select>
        </label>

        <label class="zs-field">
          <span>状态</span>
          <select v-model="form.status">
            <option v-for="status in statuses" :key="status" :value="status">
              {{ outlineStatusLabels[status] }}
            </option>
          </select>
        </label>

        <label class="zs-field">
          <span>重要程度</span>
          <select v-model="form.importance">
            <option v-for="importance in importances" :key="importance" :value="importance">
              {{ outlineImportanceLabels[importance] }}
            </option>
          </select>
        </label>

        <label class="zs-field">
          <span>排序序号</span>
          <input v-model.number="form.order_index" type="number" min="0" />
        </label>
      </div>

      <div class="form-grid">
        <label class="zs-field">
          <span>父级条目</span>
          <select v-model="form.parent_id">
            <option value="">无父级</option>
            <option v-for="outline in outlines" :key="outline.id" :value="outline.id">
              {{ outline.title }}
            </option>
          </select>
        </label>

        <label class="zs-field">
          <span>绑定分卷</span>
          <select v-model="form.volume_id">
            <option value="">不绑定分卷</option>
            <option v-for="volume in volumes" :key="volume.id" :value="volume.id">
              {{ volume.title }}
            </option>
          </select>
        </label>

        <label class="zs-field">
          <span>绑定章节</span>
          <select v-model="form.chapter_id">
            <option value="">不绑定章节</option>
            <option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">
              {{ chapter.title }}
            </option>
          </select>
        </label>
      </div>

      <footer class="zs-dialog-footer">
        <button class="zs-button zs-button-secondary" type="button" @click="emit('close')">取消</button>
        <button class="zs-button zs-button-primary" type="submit" :disabled="isSaving || !form.title.trim()">
          {{ isSaving ? '正在保存……' : '新建大纲条目' }}
        </button>
      </footer>
    </form>
  </div>
</template>

<style scoped>
h2 {
  margin: 0;
  font-size: 1.25rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
}
</style>
