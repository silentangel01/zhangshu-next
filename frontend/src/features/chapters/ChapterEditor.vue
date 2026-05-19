<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { updateChapter } from '@/entities/chapter/api'
import type { Chapter } from '@/entities/chapter/types'

const props = defineProps<{
  chapter: Chapter
}>()

const emit = defineEmits<{
  dirtyChange: [isDirty: boolean]
  saved: [chapter: Chapter]
}>()

const localContent = ref(props.chapter.content)
const originalContent = ref(props.chapter.content)
const isSaving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const localWordCount = computed(() => calculateWordCount(localContent.value))
const hasUnsavedChanges = computed(() => localContent.value !== originalContent.value)

watch(
  () => props.chapter.id,
  () => {
    localContent.value = props.chapter.content
    originalContent.value = props.chapter.content
    errorMessage.value = ''
    successMessage.value = ''
    emit('dirtyChange', false)
  },
)

watch(hasUnsavedChanges, (isDirty) => {
  emit('dirtyChange', isDirty)
})

watch(localContent, () => {
  if (hasUnsavedChanges.value) {
    successMessage.value = ''
  }
})

async function handleSave() {
  isSaving.value = true
  errorMessage.value = ''
  successMessage.value = ''

  try {
    const savedChapter = await updateChapter(props.chapter.id, {
      title: props.chapter.title,
      content: localContent.value,
      volume_id: props.chapter.volume_id,
      order_index: props.chapter.order_index,
      status: props.chapter.status,
    })

    localContent.value = savedChapter.content
    originalContent.value = savedChapter.content
    successMessage.value = 'Saved.'
    emit('dirtyChange', false)
    emit('saved', savedChapter)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Could not save chapter.'
  } finally {
    isSaving.value = false
  }
}

function calculateWordCount(content: string): number {
  return Array.from(content).filter((character) => !/\s/.test(character)).length
}
</script>

<template>
  <section class="chapter-editor" aria-label="Chapter editor">
    <header class="editor-toolbar">
      <div class="word-counts">
        <span>Local word count: {{ localWordCount }}</span>
        <span>Saved word count: {{ chapter.word_count }}</span>
      </div>
      <div class="save-actions">
        <span v-if="hasUnsavedChanges" class="dirty-label">Unsaved changes</span>
        <button
          class="save-button"
          type="button"
          :disabled="isSaving || !hasUnsavedChanges"
          @click="handleSave"
        >
          {{ isSaving ? 'Saving...' : 'Save' }}
        </button>
      </div>
    </header>

    <textarea
      v-model="localContent"
      class="editor-textarea"
      aria-label="Chapter content"
      placeholder="No content yet."
      spellcheck="false"
    />

    <footer class="editor-messages" aria-live="polite">
      <p v-if="successMessage" class="success-message">{{ successMessage }}</p>
      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
    </footer>
  </section>
</template>

<style scoped>
.chapter-editor {
  display: grid;
  gap: 12px;
}

.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.word-counts,
.save-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.word-counts {
  color: #64748b;
  font-size: 0.9rem;
  font-weight: 700;
}

.dirty-label {
  color: #9a3412;
  font-size: 0.9rem;
  font-weight: 800;
}

.save-button {
  min-height: 38px;
  border: 1px solid transparent;
  border-radius: 6px;
  padding: 0 14px;
  background: #2563eb;
  color: #ffffff;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.save-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.editor-textarea {
  width: 100%;
  min-height: 420px;
  box-sizing: border-box;
  border: 1px solid #cfd7e3;
  border-radius: 8px;
  padding: 16px;
  resize: vertical;
  background: #fbfcfe;
  color: #111827;
  font: inherit;
  font-size: 1rem;
  line-height: 1.8;
  white-space: pre-wrap;
}

.editor-textarea:focus {
  border-color: #2563eb;
  outline: 3px solid rgb(37 99 235 / 15%);
}

.editor-messages {
  min-height: 22px;
}

.success-message,
.error-message {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 800;
}

.success-message {
  color: #047857;
}

.error-message {
  color: #b42318;
}

@media (max-width: 720px) {
  .editor-toolbar,
  .save-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .save-button {
    width: 100%;
  }
}
</style>
