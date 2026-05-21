<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import { updateChapter } from '@/entities/chapter/api'
import type { Chapter } from '@/entities/chapter/types'
import {
  createRecoveryDraft,
  deleteRecoveryDraft,
  listRecoveryDrafts,
} from '@/entities/recovery/api'
import type { RecoveryDraft as RemoteRecoveryDraft } from '@/entities/recovery/types'
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

interface DraftCandidate {
  id?: string
  chapter_id: string
  content: string
  saved_content_snapshot: string
  updated_at: string
  word_count: number
}

const localContent = ref(props.chapter.content)
const originalContent = ref(props.chapter.content)
const lastSavedAt = ref(props.chapter.updated_at)
const isManualSaving = ref(false)
const isAutosaving = ref(false)
const saveStatus = ref<SaveStatus>('loaded')
const errorMessage = ref('')
const recoveryMessage = ref('')
const pendingDraft = ref<DraftCandidate | null>(null)
const showDraftPreview = ref(false)
let autosaveTimer: ReturnType<typeof window.setTimeout> | null = null
let isApplyingLoadedContent = false

const localWordCount = computed(() => calculateContentWordCount(localContent.value))
const hasUnsavedChanges = computed(() => localContent.value !== originalContent.value)
const isSaveInProgress = computed(() => isManualSaving.value || isAutosaving.value)
const formattedLastSavedAt = computed(() => formatDateTime(lastSavedAt.value))
const saveStatusText = computed(() => {
  if (isManualSaving.value) {
    return '正在保存…'
  }
  if (isAutosaving.value) {
    return '正在自动保存…'
  }
  if (hasUnsavedChanges.value) {
    return '有未保存更改'
  }

  const statusText: Record<SaveStatus, string> = {
    loaded: '已加载',
    dirty: '有未保存更改',
    'manual-saving': '正在保存…',
    'manual-saved': '已保存',
    autosaving: '正在自动保存…',
    autosaved: '已自动保存',
    'autosave-failed': '自动保存失败',
    'manual-save-failed': '保存失败',
    offline: '离线或后端不可用',
  }
  return statusText[saveStatus.value]
})

watch(
  () => props.chapter,
  (chapter) => {
    void applyLoadedChapter(chapter)
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
    saveLocalDraft()
    scheduleAutosave()
  },
)

window.addEventListener('beforeunload', handleBeforeUnload)

onBeforeUnmount(() => {
  cancelPendingAutosave()
  window.removeEventListener('beforeunload', handleBeforeUnload)
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
    await preserveRecoveryDraft()
    saveStatus.value = isNetworkLikeError(error) ? 'offline' : 'manual-save-failed'
    errorMessage.value = '保存失败，已保留恢复稿'
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
    await preserveRecoveryDraft()
    saveStatus.value = isNetworkLikeError(error) ? 'offline' : 'autosave-failed'
    errorMessage.value = '自动保存失败，当前内容已保留在本地'
  } finally {
    isAutosaving.value = false
    if (
      hasUnsavedChanges.value &&
      saveStatus.value !== 'autosave-failed' &&
      saveStatus.value !== 'offline'
    ) {
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
    save_source: source,
  })

  lastSavedAt.value = savedChapter.updated_at

  if (localContent.value === contentToSave) {
    isApplyingLoadedContent = true
    localContent.value = savedChapter.content
    originalContent.value = savedChapter.content
    isApplyingLoadedContent = false
    clearRecoveryDraft(props.chapter.id)
    pendingDraft.value = null
    emit('dirtyChange', false)
    emit('saved', savedChapter)
    saveStatus.value = source === 'autosave' ? 'autosaved' : 'manual-saved'
    return
  }

  originalContent.value = savedChapter.content
  saveStatus.value = 'dirty'
  scheduleAutosave()
}

async function applyLoadedChapter(chapter: Chapter) {
  cancelPendingAutosave()
  isApplyingLoadedContent = true
  errorMessage.value = ''
  recoveryMessage.value = ''
  pendingDraft.value = null
  showDraftPreview.value = false
  lastSavedAt.value = chapter.updated_at
  originalContent.value = chapter.content

  const draft = await getLatestRecoveryDraft(chapter)
  if (draft && draft.content !== chapter.content && isDraftNewerThanChapter(draft.updated_at, chapter.updated_at)) {
    pendingDraft.value = draft
    localContent.value = chapter.content
    saveStatus.value = 'loaded'
    window.setTimeout(() => {
      const shouldRestore = window.confirm('检测到未恢复的草稿，是否恢复？')
      if (shouldRestore) {
        restorePendingDraftToEditor()
      }
    }, 0)
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

async function getLatestRecoveryDraft(chapter: Chapter): Promise<DraftCandidate | null> {
  const localDraft = getRecoveryDraft(chapter.id)
  try {
    const remoteDrafts = await listRecoveryDrafts(chapter.id)
    const remoteDraft = remoteDrafts[0]
    if (remoteDraft && (!localDraft || new Date(remoteDraft.updated_at) > new Date(localDraft.updated_at))) {
      return toDraftCandidate(remoteDraft)
    }
  } catch {
    // Backend may be unavailable; local draft still protects the user.
  }
  return localDraft
}

async function preserveRecoveryDraft() {
  const draft = saveLocalDraft()
  try {
    const remoteDraft = await createRecoveryDraft(props.chapter.id, {
      content: draft.content,
      saved_content_snapshot: draft.saved_content_snapshot,
    })
    saveRecoveryDraft({ ...draft, id: remoteDraft.id, updated_at: remoteDraft.updated_at })
  } catch {
    // Local draft is enough when backend is down.
  }
}

function saveLocalDraft(): DraftCandidate {
  const draft = {
    chapter_id: props.chapter.id,
    content: localContent.value,
    saved_content_snapshot: originalContent.value,
    updated_at: new Date().toISOString(),
    word_count: localWordCount.value,
  }
  saveRecoveryDraft(draft)
  return draft
}

function restorePendingDraftToEditor() {
  const draft = pendingDraft.value
  if (!draft) {
    return
  }
  const confirmed = window.confirm('恢复草稿会替换当前编辑框内容，但不会自动保存到章节正文。是否继续？')
  if (!confirmed) {
    return
  }
  localContent.value = draft.content
  saveStatus.value = 'dirty'
  recoveryMessage.value = '已恢复草稿，请确认内容后保存。'
}

async function ignorePendingDraft() {
  const draft = pendingDraft.value
  const confirmed = window.confirm('忽略草稿后将删除该恢复稿，是否继续？')
  if (!confirmed) {
    return
  }
  clearRecoveryDraft(props.chapter.id)
  if (draft?.id) {
    try {
      await deleteRecoveryDraft(draft.id)
    } catch {
      // Ignore remote cleanup failure.
    }
  }
  pendingDraft.value = null
  showDraftPreview.value = false
  recoveryMessage.value = '已忽略草稿。'
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

function toDraftCandidate(draft: RemoteRecoveryDraft): DraftCandidate {
  return {
    id: draft.id,
    chapter_id: draft.chapter_id,
    content: draft.content,
    saved_content_snapshot: draft.saved_content_snapshot,
    updated_at: draft.updated_at,
    word_count: draft.word_count,
  }
}

function isDraftNewerThanChapter(draftUpdatedAt: string, chapterUpdatedAt: string): boolean {
  return new Date(draftUpdatedAt).getTime() > new Date(chapterUpdatedAt).getTime()
}

function handleBeforeUnload(event: BeforeUnloadEvent) {
  if (!hasUnsavedChanges.value) {
    return
  }
  saveLocalDraft()
  event.preventDefault()
  event.returnValue = ''
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
      <div class="editor-title">
        <h2>{{ chapter.title }}</h2>
        <p class="word-count">当前字数：{{ localWordCount }}</p>
      </div>
      <div class="save-actions">
        <span class="status-label" :class="{ warning: hasUnsavedChanges || errorMessage }">
          {{ saveStatusText }}
        </span>
        <small class="save-note">上次保存：{{ formattedLastSavedAt }}</small>
        <button
          class="save-button"
          type="button"
          :disabled="isSaveInProgress || !hasUnsavedChanges"
          @click="handleSave"
        >
          {{ isManualSaving ? '正在保存…' : '保存' }}
        </button>
      </div>
    </header>

    <section v-if="pendingDraft" class="recovery-banner">
      <div>
        <h3>检测到未恢复的草稿</h3>
        <p>草稿更新时间：{{ formatDateTime(pendingDraft.updated_at) }}，字数：{{ pendingDraft.word_count }}</p>
      </div>
      <div class="recovery-actions">
        <button class="secondary-button" type="button" @click="showDraftPreview = !showDraftPreview">
          草稿预览
        </button>
        <button class="primary-outline-button" type="button" @click="restorePendingDraftToEditor">
          恢复草稿
        </button>
        <button class="secondary-button" type="button" @click="ignorePendingDraft">忽略</button>
      </div>
      <pre v-if="showDraftPreview" class="draft-preview">{{ pendingDraft.content }}</pre>
    </section>

    <textarea
      v-model="localContent"
      class="editor-textarea"
      aria-label="章节正文"
      placeholder="暂无正文内容"
      spellcheck="false"
    />

    <footer class="editor-messages" aria-live="polite">
      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      <p v-if="recoveryMessage" class="recovery-message">{{ recoveryMessage }}</p>
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
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.editor-title,
.save-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.editor-title h2 {
  margin: 0;
  color: #111827;
  font-size: 1.1rem;
  line-height: 1.4;
}

.word-count,
.save-note {
  margin: 0;
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 700;
}

.save-actions {
  align-items: flex-end;
}

.status-label {
  color: #047857;
  font-size: 0.9rem;
  font-weight: 800;
}

.status-label.warning {
  color: #9a3412;
}

.recovery-banner {
  display: grid;
  gap: 10px;
  border: 1px solid #facc15;
  border-radius: 8px;
  padding: 12px;
  background: #fffbeb;
}

.recovery-banner h3,
.recovery-banner p {
  margin: 0;
}

.recovery-banner h3 {
  color: #92400e;
  font-size: 1rem;
}

.recovery-banner p {
  color: #64748b;
  font-size: 0.88rem;
}

.recovery-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.draft-preview {
  max-height: 220px;
  overflow: auto;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 10px;
  background: #ffffff;
  color: #111827;
  white-space: pre-wrap;
}

.save-button,
.secondary-button,
.primary-outline-button {
  min-height: 38px;
  border-radius: 6px;
  padding: 0 14px;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

.save-button {
  border: 1px solid transparent;
  background: #2563eb;
  color: #ffffff;
}

.secondary-button {
  border: 1px solid #cfd7e3;
  background: #ffffff;
  color: #374151;
}

.primary-outline-button {
  border: 1px solid #2563eb;
  background: #eff6ff;
  color: #2563eb;
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

.error-message,
.recovery-message {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 800;
}

.error-message {
  color: #b42318;
}

.recovery-message {
  color: #047857;
}

@media (max-width: 720px) {
  .editor-toolbar,
  .save-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .save-button,
  .secondary-button,
  .primary-outline-button {
    width: 100%;
  }
}
</style>
