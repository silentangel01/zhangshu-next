<script setup lang="ts">
import { reactive, ref } from 'vue'

import type { CreateProjectPayload } from '@/entities/project/types'

const emit = defineEmits<{
  close: []
  submit: [payload: CreateProjectPayload]
}>()

const form = reactive({
  title: '',
  genre: '',
  summary: '',
})

const titleError = ref('')

function normalizeOptional(value: string): string | null {
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function handleSubmit() {
  const title = form.title.trim()

  if (!title) {
    titleError.value = 'Title is required.'
    return
  }

  titleError.value = ''
  emit('submit', {
    title,
    genre: normalizeOptional(form.genre),
    summary: normalizeOptional(form.summary),
  })
}
</script>

<template>
  <div class="dialog-backdrop" role="presentation">
    <section class="dialog" role="dialog" aria-modal="true" aria-labelledby="create-project-title">
      <header class="dialog-header">
        <h2 id="create-project-title">Create Project</h2>
        <button class="icon-button" type="button" aria-label="Close" @click="emit('close')">x</button>
      </header>

      <form class="project-form" @submit.prevent="handleSubmit">
        <label>
          <span>Title</span>
          <input v-model="form.title" name="title" type="text" autocomplete="off" required />
        </label>
        <p v-if="titleError" class="field-error">{{ titleError }}</p>

        <label>
          <span>Genre</span>
          <input v-model="form.genre" name="genre" type="text" autocomplete="off" />
        </label>

        <label>
          <span>Summary</span>
          <textarea v-model="form.summary" name="summary" rows="5" />
        </label>

        <footer class="dialog-actions">
          <button class="secondary-button" type="button" @click="emit('close')">Cancel</button>
          <button class="primary-button" type="submit">Create</button>
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
  width: min(560px, 100%);
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

.project-form {
  display: grid;
  gap: 16px;
  padding: 20px 24px 24px;
}

label {
  display: grid;
  gap: 8px;
  color: #4b5563;
  font-size: 0.9rem;
  font-weight: 600;
}

input,
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
}

input:focus,
textarea:focus {
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
  font-weight: 700;
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
