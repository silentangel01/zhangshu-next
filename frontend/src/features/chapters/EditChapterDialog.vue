<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import type {
  Chapter,
  ChapterStatus,
  UpdateChapterMetadataPayload,
} from '@/entities/chapter/types'
import type { Volume } from '@/entities/volume/types'

const props = defineProps<{
  chapter: Chapter
  volumes: Volume[]
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: UpdateChapterMetadataPayload]
}>()

const statuses: ChapterStatus[] = ['draft', 'writing', 'revised', 'completed']

const form = reactive({
  title: props.chapter.title,
  volume_id: props.chapter.volume_id ?? '',
  order_index: props.chapter.order_index,
  status: props.chapter.status,
})

const titleError = ref('')

watch(
  () => props.chapter,
  (chapter) => {
    form.title = chapter.title
    form.volume_id = chapter.volume_id ?? ''
    form.order_index = chapter.order_index
    form.status = chapter.status
    titleError.value = ''
  },
)

function handleSubmit() {
  const title = form.title.trim()

  if (!title) {
    titleError.value = '标题不能为空。'
    return
  }

  titleError.value = ''
  emit('submit', {
    title,
    volume_id: form.volume_id || null,
    order_index: Number(form.order_index),
    status: form.status,
  })
}

function getStatusLabel(status: ChapterStatus): string {
  const labels: Record<ChapterStatus, string> = {
    draft: '草稿',
    writing: '写作中',
    revised: '已修订',
    completed: '已完成',
  }

  return labels[status]
}
</script>

<template>
  <div class="dialog-backdrop" role="presentation">
    <section class="dialog" role="dialog" aria-modal="true" aria-labelledby="edit-chapter-title">
      <header class="dialog-header">
        <h2 id="edit-chapter-title">编辑章节信息</h2>
        <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')">x</button>
      </header>

      <form class="form" @submit.prevent="handleSubmit">
        <label>
          <span>标题</span>
          <input v-model="form.title" type="text" required autocomplete="off" />
        </label>
        <p v-if="titleError" class="field-error">{{ titleError }}</p>

        <label>
          <span>分卷</span>
          <select v-model="form.volume_id">
            <option value="">未分卷章节</option>
            <option v-for="volume in volumes" :key="volume.id" :value="volume.id">
              {{ volume.title }}
            </option>
          </select>
        </label>

        <label>
          <span>排序</span>
          <input v-model.number="form.order_index" type="number" min="0" required />
        </label>

        <label>
          <span>状态</span>
          <select v-model="form.status">
            <option v-for="status in statuses" :key="status" :value="status">
              {{ getStatusLabel(status) }}
            </option>
          </select>
        </label>

        <footer class="dialog-actions">
          <button class="secondary-button" type="button" @click="emit('close')">取消</button>
          <button class="primary-button" type="submit">保存</button>
        </footer>
      </form>
    </section>
  </div>
</template>

<style scoped>
.dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 20;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgb(20 24 31 / 54%);
}

.dialog {
  width: min(520px, 100%);
  border: 1px solid #d8dee9;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 24px 80px rgb(20 24 31 / 22%);
}

.dialog-header,
.dialog-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 24px;
}

.dialog-header {
  border-bottom: 1px solid #edf0f5;
}

h2 {
  margin: 0;
  color: #1f2937;
  font-size: 1.25rem;
}

.form {
  display: grid;
  gap: 16px;
  padding: 20px 24px 24px;
}

label {
  display: grid;
  gap: 8px;
  color: #4b5563;
  font-size: 0.9rem;
  font-weight: 700;
}

input,
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #cfd7e3;
  border-radius: 6px;
  padding: 10px 12px;
  color: #111827;
  font: inherit;
}

input:focus,
select:focus {
  border-color: #2563eb;
  outline: 3px solid rgb(37 99 235 / 15%);
}

.field-error {
  margin: -8px 0 0;
  color: #b42318;
  font-size: 0.9rem;
}

.dialog-actions {
  padding: 4px 0 0;
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

.icon-button {
  width: 36px;
  min-height: 36px;
  padding: 0;
  border-color: #d8dee9;
  background: #ffffff;
  color: #374151;
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
