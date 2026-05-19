<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { updateChapter } from '@/entities/chapter/api'
import type { Chapter } from '@/entities/chapter/types'
import {
  calculateContentWordCount,
  clearRecoveryDraft,
  getRecoveryDraft,
  saveRecoveryDraft,
} from './recoveryDraft'

const props = defineProps<{
  chapter: Chapter
}>()

const emit = defineEmits<{
  dirtyChange: [isDirty: boolean]
  saved: [chapter: Chapter]
}>()

type SaveStatus =
  | 'loaded'
  | 'dirty'
  | 'manual-saving'
  | 'manual-saved'
  | 'autosaving'
  | 'autosaved'
  | 'autosave-failed'
  | 'manual-save-failed'
  | 'offline'

const localContent = ref(props.chapter.content)
const originalContent = ref(props.chapter.content)
const savedWordCount = ref(props.chapter.word_count)
const lastSavedAt = ref(props.chapter.updated_at)
const isManualSaving = ref(false)
const isAutosaving = ref(false)
const saveStatus = ref<SaveStatus>('loaded')
const errorMessage = ref('')
let autosaveTimer: ReturnType<typeof window.setTimeout> | null = null
let isApplyingLoadedContent = false

const localWordCount = computed(() => calculateContentWordCount(localContent.value))
const hasUnsavedChanges = computed(() => localContent.value !== originalContent.value)
const isSaveInProgress = computed(() => isManualSaving.value || isAutosaving.value)
const saveStatusText = computed(() => {
  if (isManualSaving.value) {
    return '正在保存……'
  }

  if (isAutosaving.value) {
    return '正在自动保存……'
  }

  if (hasUnsavedChanges.value) {
    return '有未保存更改'
  }

  const statusText: Record<SaveStatus, string> = {
    loaded: '已加载',
    dirty: '有未保存更改',
    'manual-saving': '正在保存……',
    'manual-saved': '已保存',
    autosaving: '正在自动保存……',
    autosaved: '已自动保存',
    'autosave-failed': '自动保存失败',
    'manual-save-failed': '保存失败',
    offline: '离线或后端不可用',
  }

  return statusText[saveStatus.value]
})
const formattedLastSavedAt = computed(() => formatDateTime(lastSavedAt.value))

watch(
  () => props.chapter,
  (chapter) => {
    applyLoadedChapter(chapter)
  },
  { immediate: true },
)

watch(hasUnsavedChanges, (isDirty) => {
  emit('dirtyChange', isDirty)
})

watch(
  localContent,
  () => {
    if (isApplyingLoadedContent) {
      return
    }

    cancelPendingAutosave()
    errorMessage.value = ''

    if (!hasUnsavedChanges.value) {
      clearRecoveryDraft(props.chapter.id)
      saveStatus.value = 'loaded'
      return
    }

    saveStatus.value = 'dirty'
    saveRecoveryDraft({
      chapter_id: props.chapter.id,
      content: localContent.value,
      saved_content_snapshot: originalContent.value,
      updated_at: new Date().toISOString(),
      word_count: localWordCount.value,
    })

    scheduleAutosave()
  },
)

onBeforeUnmount(() => {
  cancelPendingAutosave()
})

defineExpose({
  cancelPendingAutosave,
})

async function handleSave() {
  cancelPendingAutosave()
  isManualSaving.value = true
  saveStatus.value = 'manual-saving'
  errorMessage.value = ''

  try {
    await saveCurrentContent('manual')
  } catch (error) {
    saveStatus.value = isNetworkLikeError(error) ? 'offline' : 'manual-save-failed'
    errorMessage.value = '保存失败，正文仍保留在本地编辑框中。'
  } finally {
    isManualSaving.value = false
    if (hasUnsavedChanges.value && !isAutosaving.value) {
      scheduleAutosave()
    }
  }
}

async function runAutosave() {
  if (!hasUnsavedChanges.value || isManualSaving.value || isAutosaving.value) {
    return
  }

  isAutosaving.value = true
  saveStatus.value = 'autosaving'
  errorMessage.value = ''

  try {
    await saveCurrentContent('autosave')
  } catch (error) {
    saveStatus.value = isNetworkLikeError(error) ? 'offline' : 'autosave-failed'
    errorMessage.value = '自动保存失败，正文仍保留在本地编辑框中。'
  } finally {
    isAutosaving.value = false
    if (hasUnsavedChanges.value && saveStatus.value !== 'autosave-failed' && saveStatus.value !== 'offline') {
      scheduleAutosave()
    }
  }
}

async function saveCurrentContent(source: 'manual' | 'autosave') {
  const contentToSave = localContent.value
  const savedChapter = await updateChapter(props.chapter.id, {
    title: props.chapter.title,
    content: contentToSave,
    volume_id: props.chapter.volume_id,
    order_index: props.chapter.order_index,
    status: props.chapter.status,
  })

  savedWordCount.value = savedChapter.word_count
  lastSavedAt.value = savedChapter.updated_at

  if (localContent.value === contentToSave) {
    isApplyingLoadedContent = true
    localContent.value = savedChapter.content
    originalContent.value = savedChapter.content
    isApplyingLoadedContent = false
    clearRecoveryDraft(props.chapter.id)
    emit('dirtyChange', false)
    emit('saved', savedChapter)
    saveStatus.value = source === 'autosave' ? 'autosaved' : 'manual-saved'
    return
  }

  originalContent.value = savedChapter.content
  saveStatus.value = 'dirty'
  scheduleAutosave()
}

function applyLoadedChapter(chapter: Chapter) {
  cancelPendingAutosave()
  isApplyingLoadedContent = true
  errorMessage.value = ''
  savedWordCount.value = chapter.word_count
  lastSavedAt.value = chapter.updated_at
  originalContent.value = chapter.content

  const draft = getRecoveryDraft(chapter.id)
  if (draft && draft.content !== chapter.content) {
    const shouldRestore = window.confirm('检测到本地恢复稿，是否恢复？')
    if (shouldRestore) {
      localContent.value = draft.content
      saveStatus.value = 'dirty'
    } else {
      localContent.value = chapter.content
      saveStatus.value = 'loaded'
      clearRecoveryDraft(chapter.id)
    }
  } else {
    localContent.value = chapter.content
    saveStatus.value = 'loaded'
    if (draft) {
      clearRecoveryDraft(chapter.id)
    }
  }

  isApplyingLoadedContent = false
  emit('dirtyChange', localContent.value !== originalContent.value)
}

function scheduleAutosave() {
  if (isManualSaving.value || !hasUnsavedChanges.value) {
    return
  }

  autosaveTimer = window.setTimeout(() => {
    autosaveTimer = null
    void runAutosave()
  }, 2000)
}

function cancelPendingAutosave() {
  if (autosaveTimer) {
    window.clearTimeout(autosaveTimer)
    autosaveTimer = null
  }
}

function formatDateTime(value: string): string {
  const date = new Date(value)
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`
}

function isNetworkLikeError(error: unknown): boolean {
  return error instanceof TypeError || (error instanceof Error && error.message.includes('Failed to fetch'))
}
</script>

<template>
  <section class="chapter-editor" aria-label="章节编辑器">
    <header class="editor-toolbar">
      <div class="word-counts">
        <span>当前字数：{{ localWordCount }}</span>
        <span>已保存字数：{{ savedWordCount }}</span>
        <span>上次保存：{{ formattedLastSavedAt }}</span>
      </div>
      <div class="save-actions">
        <span class="status-label" :class="{ warning: hasUnsavedChanges || errorMessage }">
          {{ saveStatusText }}
        </span>
        <button
          class="save-button"
          type="button"
          :disabled="isSaveInProgress || !hasUnsavedChanges"
          @click="handleSave"
        >
          {{ isManualSaving ? '正在保存……' : '保存' }}
        </button>
      </div>
    </header>

    <textarea
      v-model="localContent"
      class="editor-textarea"
      aria-label="章节正文"
      placeholder="暂无正文内容"
      spellcheck="false"
    />

    <footer class="editor-messages" aria-live="polite">
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

.status-label {
  color: #047857;
  font-size: 0.9rem;
  font-weight: 800;
}

.status-label.warning {
  color: #9a3412;
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

.error-message {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 800;
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
