<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import type { ChapterStatus, CreateChapterPayload } from '@/entities/chapter/types'
import type { Volume } from '@/entities/volume/types'

const props = defineProps<{
  volumes: Volume[]
  initialVolumeId?: string | null
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: CreateChapterPayload]
}>()

const statuses: ChapterStatus[] = ['draft', 'writing', 'revised', 'completed']

const form = reactive({
  title: '',
  volume_id: '',
  order_index: 0,
  status: 'draft' as ChapterStatus,
})

const titleError = ref('')

watch(
  () => props.initialVolumeId,
  (volumeId) => {
    form.volume_id = volumeId ?? ''
  },
  { immediate: true },
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
    content: '',
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
    <section class="dialog" role="dialog" aria-modal="true" aria-labelledby="create-chapter-title">
      <header class="dialog-header">
        <h2 id="create-chapter-title">新建章节</h2>
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
          <button class="primary-button" type="submit">新建</button>
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
  border: 1px solid var(--zs-color-border);
  border-radius: 8px;
  background: var(--zs-color-surface);
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
  border-bottom: 1px solid var(--zs-color-border-soft);
}

h2 {
  margin: 0;
  color: var(--zs-color-text);
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
  color: var(--zs-color-text-muted);
  font-size: 0.9rem;
  font-weight: 700;
}

input,
select {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: 6px;
  padding: 10px 12px;
  color: var(--zs-color-text);
  font: inherit;
}

input:focus,
select:focus {
  border-color: var(--zs-color-primary);
  outline: 3px solid rgb(37 99 235 / 15%);
}

.field-error {
  margin: -8px 0 0;
  color: var(--zs-color-danger);
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
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.primary-button {
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.secondary-button {
  border-color: var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}
</style>
