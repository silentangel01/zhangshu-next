<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

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
import { safeReadJson, safeWriteJson } from '@/shared/storage/localWorkspaceState'

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

type FirstLineIndent = 'none' | '2em'
type EditorLineHeight = '1.4' | '1.6' | '1.8' | '2.0'
type EditorFontPreset =
  | 'system'
  | 'microsoft-yahei'
  | 'simsun'
  | 'simhei'
  | 'kaiti'
  | 'fangsong'
  | 'dengxian'
  | 'pingfang'
  | 'source-han-sans'
  | 'source-han-serif'
  | 'noto-sans-cjk'
  | 'noto-serif-cjk'
  | 'lxgw-wenkai'
  | 'sarasa-gothic'
  | 'arial'
  | 'georgia'
  | 'times-new-roman'
  | 'consolas'
  | 'courier-new'
type EditorFontSize = 14 | 16 | 18 | 20
type EditorWidth = 'standard' | 'wide' | 'full'
type ParagraphSpacing = 'normal' | 'comfortable'
type EditorTheme = 'plain' | 'eye' | 'dark'

interface EditorAppearanceSettings {
  firstLineIndent: FirstLineIndent
  lineHeight: EditorLineHeight
  selectedFontPreset: EditorFontPreset
  customFontFamily: string
  fontSize: EditorFontSize
  editorWidth: EditorWidth
  paragraphSpacing: ParagraphSpacing
  theme: EditorTheme
}

// 粗体、下划线、颜色等逐字格式需要先决定富文本存储方案，本轮仅做显示设置。
const EDITOR_APPEARANCE_STORAGE_KEY = 'zhangshu:editor:appearance'
const WRITING_IDLE_TIMEOUT_MS = 3 * 60 * 1000
const SESSION_SPEED_MIN_ACTIVE_MS = 10 * 1000
const defaultAppearanceSettings: EditorAppearanceSettings = {
  firstLineIndent: 'none',
  lineHeight: '1.8',
  selectedFontPreset: 'system',
  customFontFamily: '',
  fontSize: 16,
  editorWidth: 'full',
  paragraphSpacing: 'normal',
  theme: 'plain',
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
const appearanceSettings = ref<EditorAppearanceSettings>(readEditorAppearanceSettings())
const moreSettingsRef = ref<HTMLDetailsElement | null>(null)
const sessionChapterId = ref(props.chapter.id)
const initialSessionWordCount = ref(calculateContentWordCount(props.chapter.content))
const activeWritingMilliseconds = ref(0)
const activeWritingStartedAt = ref<number | null>(null)
const sessionClock = ref(Date.now())
let autosaveTimer: ReturnType<typeof window.setTimeout> | null = null
let writingIdleTimer: ReturnType<typeof window.setTimeout> | null = null
let writingClockTimer: ReturnType<typeof window.setInterval> | null = null
let isApplyingLoadedContent = false

const localWordCount = computed(() => calculateContentWordCount(localContent.value))
const sessionActiveMilliseconds = computed(() => {
  if (activeWritingStartedAt.value === null) {
    return activeWritingMilliseconds.value
  }
  return activeWritingMilliseconds.value + Math.max(sessionClock.value - activeWritingStartedAt.value, 0)
})
const sessionWritingMinutes = computed(() => Math.floor(sessionActiveMilliseconds.value / 60000))
const sessionWordsAdded = computed(() => Math.max(localWordCount.value - initialSessionWordCount.value, 0))
const sessionSpeedText = computed(() => {
  if (sessionWordsAdded.value <= 0 || sessionActiveMilliseconds.value < SESSION_SPEED_MIN_ACTIVE_MS) {
    return '--'
  }
  const activeHours = sessionActiveMilliseconds.value / 3600000
  return String(Math.round(sessionWordsAdded.value / activeHours))
})
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
const editorStyle = computed(() => ({
  fontFamily: getEditorFontFamily(appearanceSettings.value),
  fontSize: `${appearanceSettings.value.fontSize}px`,
  lineHeight: appearanceSettings.value.lineHeight,
  textIndent: appearanceSettings.value.firstLineIndent === '2em' ? '2em' : '0',
  paddingBlock: appearanceSettings.value.paragraphSpacing === 'comfortable' ? '22px' : '16px',
  ...getEditorThemeStyle(appearanceSettings.value.theme),
}))
const editorShellStyle = computed(() => ({
  maxWidth: getEditorMaxWidth(appearanceSettings.value.editorWidth),
}))

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

watch(
  appearanceSettings,
  (settings) => {
    safeWriteJson(EDITOR_APPEARANCE_STORAGE_KEY, settings)
  },
  { deep: true },
)

window.addEventListener('beforeunload', handleBeforeUnload)

onBeforeUnmount(() => {
  cancelPendingAutosave()
  pauseWritingTimer()
  stopWritingClock()
  clearWritingIdleTimer()
  removeMoreSettingsListeners()
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
  if (chapter.id !== sessionChapterId.value) {
    sessionChapterId.value = chapter.id
    resetWritingSession(chapter.content)
  }
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

function handleEditorInput() {
  recordWritingActivity()
}

function recordWritingActivity() {
  const now = Date.now()
  sessionClock.value = now
  if (activeWritingStartedAt.value === null) {
    activeWritingStartedAt.value = now
  }
  startWritingClock()
  resetWritingIdleTimer()
}

function resetWritingIdleTimer() {
  clearWritingIdleTimer()
  writingIdleTimer = window.setTimeout(() => {
    pauseWritingTimer()
  }, WRITING_IDLE_TIMEOUT_MS)
}

function clearWritingIdleTimer() {
  if (writingIdleTimer) {
    window.clearTimeout(writingIdleTimer)
    writingIdleTimer = null
  }
}

function pauseWritingTimer() {
  if (activeWritingStartedAt.value !== null) {
    const now = Date.now()
    activeWritingMilliseconds.value += Math.max(now - activeWritingStartedAt.value, 0)
    activeWritingStartedAt.value = null
    sessionClock.value = now
  }
  clearWritingIdleTimer()
  stopWritingClock()
}

function resetWritingSession(content: string) {
  pauseWritingTimer()
  initialSessionWordCount.value = calculateContentWordCount(content)
  activeWritingMilliseconds.value = 0
  activeWritingStartedAt.value = null
  sessionClock.value = Date.now()
}

function startWritingClock() {
  if (writingClockTimer !== null) {
    return
  }
  writingClockTimer = window.setInterval(() => {
    sessionClock.value = Date.now()
  }, 1000)
}

function stopWritingClock() {
  if (writingClockTimer !== null) {
    window.clearInterval(writingClockTimer)
    writingClockTimer = null
  }
}

function handleMoreSettingsToggle() {
  if (moreSettingsRef.value?.open) {
    void nextTick(() => {
      document.addEventListener('pointerdown', handleMoreSettingsOutsidePointerDown)
      document.addEventListener('keydown', handleMoreSettingsKeydown)
    })
    return
  }
  removeMoreSettingsListeners()
}

function handleMoreSettingsOutsidePointerDown(event: PointerEvent) {
  const root = moreSettingsRef.value
  const target = event.target
  if (!root || !(target instanceof Node) || root.contains(target)) {
    return
  }
  closeMoreSettings()
}

function handleMoreSettingsKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    closeMoreSettings()
  }
}

function closeMoreSettings() {
  if (moreSettingsRef.value) {
    moreSettingsRef.value.open = false
  }
  removeMoreSettingsListeners()
}

function removeMoreSettingsListeners() {
  document.removeEventListener('pointerdown', handleMoreSettingsOutsidePointerDown)
  document.removeEventListener('keydown', handleMoreSettingsKeydown)
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

function readEditorAppearanceSettings(): EditorAppearanceSettings {
  const settings = safeReadJson<(Partial<EditorAppearanceSettings> & { fontFamily?: unknown }) | null>(EDITOR_APPEARANCE_STORAGE_KEY, null)
  const legacyFontPreset = normalizeLegacyFontPreset(settings?.fontFamily)
  return {
    firstLineIndent: settings?.firstLineIndent === '2em' ? '2em' : defaultAppearanceSettings.firstLineIndent,
    lineHeight: isEditorLineHeight(settings?.lineHeight) ? settings.lineHeight : defaultAppearanceSettings.lineHeight,
    selectedFontPreset: isEditorFontPreset(settings?.selectedFontPreset)
      ? settings.selectedFontPreset
      : legacyFontPreset ?? defaultAppearanceSettings.selectedFontPreset,
    customFontFamily: typeof settings?.customFontFamily === 'string' ? settings.customFontFamily : '',
    fontSize: isEditorFontSize(settings?.fontSize) ? settings.fontSize : defaultAppearanceSettings.fontSize,
    editorWidth: isEditorWidth(settings?.editorWidth) ? settings.editorWidth : defaultAppearanceSettings.editorWidth,
    paragraphSpacing: settings?.paragraphSpacing === 'comfortable' ? 'comfortable' : defaultAppearanceSettings.paragraphSpacing,
    theme: isEditorTheme(settings?.theme) ? settings.theme : defaultAppearanceSettings.theme,
  }
}

function isEditorLineHeight(value: unknown): value is EditorLineHeight {
  return value === '1.4' || value === '1.6' || value === '1.8' || value === '2.0'
}

function isEditorFontPreset(value: unknown): value is EditorFontPreset {
  return value === 'system'
    || value === 'microsoft-yahei'
    || value === 'simsun'
    || value === 'simhei'
    || value === 'kaiti'
    || value === 'fangsong'
    || value === 'dengxian'
    || value === 'pingfang'
    || value === 'source-han-sans'
    || value === 'source-han-serif'
    || value === 'noto-sans-cjk'
    || value === 'noto-serif-cjk'
    || value === 'lxgw-wenkai'
    || value === 'sarasa-gothic'
    || value === 'arial'
    || value === 'georgia'
    || value === 'times-new-roman'
    || value === 'consolas'
    || value === 'courier-new'
}

function normalizeLegacyFontPreset(value: unknown): EditorFontPreset | null {
  if (isEditorFontPreset(value)) {
    return value
  }
  if (value === 'songti') {
    return 'simsun'
  }
  if (value === 'heiti') {
    return 'simhei'
  }
  return null
}

function isEditorFontSize(value: unknown): value is EditorFontSize {
  return value === 14 || value === 16 || value === 18 || value === 20
}

function isEditorWidth(value: unknown): value is EditorWidth {
  return value === 'standard' || value === 'wide' || value === 'full'
}

function isEditorTheme(value: unknown): value is EditorTheme {
  return value === 'plain' || value === 'eye' || value === 'dark'
}

function getEditorFontFamily(settings: EditorAppearanceSettings) {
  const customFont = settings.customFontFamily.trim()
  if (customFont) {
    return `${quoteFontFamily(customFont)}, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
  }

  const families: Record<EditorFontPreset, string> = {
    system: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    'microsoft-yahei': '"Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", sans-serif',
    simsun: '"SimSun", "Songti SC", "Noto Serif CJK SC", serif',
    simhei: '"SimHei", "Heiti SC", "Noto Sans CJK SC", sans-serif',
    kaiti: '"KaiTi", "Kaiti SC", serif',
    fangsong: '"FangSong", "FangSong_GB2312", serif',
    dengxian: '"DengXian", "Microsoft YaHei", sans-serif',
    pingfang: '"PingFang SC", "Microsoft YaHei", sans-serif',
    'source-han-sans': '"Source Han Sans SC", "Noto Sans CJK SC", sans-serif',
    'source-han-serif': '"Source Han Serif SC", "Noto Serif CJK SC", serif',
    'noto-sans-cjk': '"Noto Sans CJK SC", "Source Han Sans SC", sans-serif',
    'noto-serif-cjk': '"Noto Serif CJK SC", "Source Han Serif SC", serif',
    'lxgw-wenkai': '"LXGW WenKai", "KaiTi", serif',
    'sarasa-gothic': '"Sarasa Gothic SC", "Microsoft YaHei", sans-serif',
    arial: 'Arial, "Microsoft YaHei", sans-serif',
    georgia: 'Georgia, "Noto Serif CJK SC", serif',
    'times-new-roman': '"Times New Roman", "Noto Serif CJK SC", serif',
    consolas: 'Consolas, "Microsoft YaHei", monospace',
    'courier-new': '"Courier New", "Microsoft YaHei", monospace',
  }
  return families[settings.selectedFontPreset]
}

function quoteFontFamily(value: string) {
  const escaped = value.replace(/["\\]/g, '')
  return `"${escaped}"`
}

function getEditorMaxWidth(width: EditorWidth) {
  const widths: Record<EditorWidth, string> = {
    standard: '760px',
    wide: '920px',
    full: '100%',
  }
  return widths[width]
}

function getEditorThemeStyle(theme: EditorTheme) {
  const themes: Record<EditorTheme, Record<string, string>> = {
    plain: {
      background: '#fbfcfe',
      borderColor: '#cfd7e3',
      color: '#111827',
    },
    eye: {
      background: '#fbfaf0',
      borderColor: '#d7d3b8',
      color: '#263025',
    },
    dark: {
      background: '#1f2937',
      borderColor: '#374151',
      color: '#f8fafc',
    },
  }
  return themes[theme]
}
</script>

<template>
  <section class="chapter-editor" aria-label="章节编辑器">
    <header class="editor-toolbar">
      <div class="editor-title">
        <h2>{{ chapter.title }}</h2>
        <div class="writing-status-line" aria-label="写作状态">
          <span>当前字数：{{ localWordCount }}</span>
          <span aria-hidden="true">｜</span>
          <span>本次写作：{{ sessionWritingMinutes }} 分钟</span>
          <span aria-hidden="true">｜</span>
          <span>速度：{{ sessionSpeedText }}<template v-if="sessionSpeedText !== '--'"> 字/小时</template></span>
          <span aria-hidden="true">｜</span>
          <span>上次保存：{{ formattedLastSavedAt }}</span>
          <span aria-hidden="true">｜</span>
          <span :class="{ warning: hasUnsavedChanges || errorMessage }">{{ saveStatusText }}</span>
        </div>
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

    <div class="editor-textarea-shell" :style="editorShellStyle">
      <div class="writing-toolbar" aria-label="编辑器显示工具栏">
        <label>
          <span>字号</span>
          <select v-model.number="appearanceSettings.fontSize">
            <option :value="14">14</option>
            <option :value="16">16</option>
            <option :value="18">18</option>
            <option :value="20">20</option>
          </select>
        </label>
        <label>
          <span>行距</span>
          <select v-model="appearanceSettings.lineHeight">
            <option value="1.4">1.4</option>
            <option value="1.6">1.6</option>
            <option value="1.8">1.8</option>
            <option value="2.0">2.0</option>
          </select>
        </label>
        <label>
          <span>缩进</span>
          <select v-model="appearanceSettings.firstLineIndent">
            <option value="none">无</option>
            <option value="2em">2em</option>
          </select>
        </label>
        <label>
          <span>宽度</span>
          <select v-model="appearanceSettings.editorWidth">
            <option value="standard">标准</option>
            <option value="wide">宽</option>
            <option value="full">撑满</option>
          </select>
        </label>
        <label>
          <span>模式</span>
          <select v-model="appearanceSettings.theme">
            <option value="plain">默认</option>
            <option value="eye">护眼</option>
            <option value="dark">深色</option>
          </select>
        </label>
        <details ref="moreSettingsRef" class="more-settings" @toggle="handleMoreSettingsToggle">
          <summary>更多设置</summary>
          <div class="more-settings-menu">
            <label>
              <span>字体</span>
              <select v-model="appearanceSettings.selectedFontPreset" class="font-select">
                <option value="system">系统默认</option>
                <option value="microsoft-yahei">微软雅黑</option>
                <option value="simsun">宋体</option>
                <option value="simhei">黑体</option>
                <option value="kaiti">楷体</option>
                <option value="fangsong">仿宋</option>
                <option value="dengxian">等线</option>
                <option value="pingfang">苹方</option>
                <option value="source-han-sans">思源黑体</option>
                <option value="source-han-serif">思源宋体</option>
                <option value="noto-sans-cjk">Noto Sans CJK</option>
                <option value="noto-serif-cjk">Noto Serif CJK</option>
                <option value="lxgw-wenkai">霞鹜文楷</option>
                <option value="sarasa-gothic">更纱黑体</option>
                <option value="arial">Arial</option>
                <option value="georgia">Georgia</option>
                <option value="times-new-roman">Times New Roman</option>
                <option value="consolas">Consolas</option>
                <option value="courier-new">Courier New</option>
              </select>
            </label>
            <label>
              <span>自定义字体名称</span>
              <input
                v-model.trim="appearanceSettings.customFontFamily"
                class="font-input"
                type="text"
                placeholder="例如：霞鹜文楷"
              />
            </label>
            <label>
              <span>段间距</span>
              <select v-model="appearanceSettings.paragraphSpacing">
                <option value="normal">普通</option>
                <option value="comfortable">舒展</option>
              </select>
            </label>
            <p class="font-helper">字体仅调用本机已安装字体，不随软件分发字体文件；未安装时会自动使用后备字体。</p>
          </div>
        </details>
        <button
          class="save-button"
          type="button"
          :disabled="isSaveInProgress || !hasUnsavedChanges"
          @click="handleSave"
        >
          {{ isManualSaving ? '保存中…' : '保存' }}
        </button>
      </div>
      <textarea
        v-model="localContent"
        class="editor-textarea"
        :style="editorStyle"
        aria-label="章节正文"
        placeholder="开始写作……"
        spellcheck="false"
        @input="handleEditorInput"
      />
    </div>

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
  display: block;
}

.editor-title {
  display: grid;
  gap: 6px;
}

.editor-title h2 {
  margin: 0;
  color: #111827;
  font-size: 1.25rem;
  line-height: 1.4;
}

.writing-status-line {
  margin: 0;
  color: #64748b;
  font-size: 0.82rem;
  display: flex;
  flex-wrap: wrap;
  gap: 4px 8px;
  align-items: center;
  line-height: 1.5;
}

.writing-status-line .warning {
  color: #9a3412;
  font-weight: 800;
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

.editor-textarea-shell {
  width: 100%;
  justify-self: center;
}

.writing-toolbar {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
  color: #64748b;
  font-size: 0.82rem;
}

.writing-toolbar label {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.writing-toolbar select {
  min-height: 30px;
  border: 1px solid #d8dee9;
  border-radius: 6px;
  padding: 0 8px;
  background: #ffffff;
  color: #111827;
  font: inherit;
}

.writing-toolbar input {
  min-height: 30px;
  box-sizing: border-box;
  border: 1px solid #d8dee9;
  border-radius: 6px;
  padding: 0 8px;
  background: #ffffff;
  color: #111827;
  font: inherit;
}

.font-select,
.font-input {
  min-width: 180px;
}

.more-settings {
  position: relative;
}

.more-settings summary {
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  border: 1px solid #d8dee9;
  border-radius: 6px;
  padding: 0 9px;
  background: #ffffff;
  color: #374151;
  font-weight: 800;
  list-style: none;
  cursor: pointer;
}

.more-settings summary::-webkit-details-marker {
  display: none;
}

.more-settings-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  z-index: 10;
  display: grid;
  gap: 10px;
  min-width: 220px;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 12px;
  background: #ffffff;
  box-shadow: 0 16px 36px rgb(20 24 31 / 12%);
}

.more-settings-menu label {
  align-items: stretch;
  justify-content: space-between;
}

.font-helper {
  margin: 0;
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.55;
}

.editor-textarea {
  width: 100%;
  min-height: 420px;
  box-sizing: border-box;
  border: 1px solid #d8dee9;
  border-radius: 8px;
  padding: 20px;
  resize: vertical;
  color: #111827;
  font: inherit;
  white-space: pre-wrap;
  box-shadow: inset 0 1px 2px rgb(15 23 42 / 4%);
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
  .save-button,
  .secondary-button,
  .primary-outline-button {
    width: 100%;
  }

  .writing-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .writing-toolbar label,
  .writing-toolbar select,
  .more-settings,
  .more-settings summary {
    width: 100%;
  }

  .more-settings-menu {
    position: static;
    margin-top: 8px;
  }
}
</style>
