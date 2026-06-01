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
import { formatChapterContent } from './chapterFormatting'
import type { FirstLineIndentSpaces, ParagraphSpacingLines } from './chapterFormatting'
import { safeReadJson, safeWriteJson } from '@/shared/storage/localWorkspaceState'
import { formatDateTimeFull } from '@/shared/utils/formatDateTime'
import { cloudSyncManager } from '@/features/cloud/cloudSyncManager'

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
type EditorLineHeight = 1.0 | 1.5 | 2.0 | 2.5 | 3.0
type EditorTextAlign = 'left' | 'center' | 'right' | 'justify'
type EditorTheme = 'plain' | 'eye' | 'dark'

interface EditorAppearanceSettings {
  firstLineIndentSpaces: FirstLineIndentSpaces
  lineHeight: EditorLineHeight
  selectedFontPreset: EditorFontPreset
  customFontFamily: string
  fontSize: EditorFontSize
  editorWidth: EditorWidth
  paragraphSpacingLines: ParagraphSpacingLines
  textAlign: EditorTextAlign
  theme: EditorTheme
}

interface FormatUndoSnapshot {
  content: string
  selectionStart: number
  selectionEnd: number
  createdAt: number
}

// 粗体、下划线、颜色等逐字格式需要先决定富文本存储方案，本轮仅做显示设置。
const EDITOR_APPEARANCE_STORAGE_KEY = 'zhangshu:editor:appearance'
const WRITING_IDLE_TIMEOUT_MS = 3 * 60 * 1000
const SESSION_SPEED_MIN_ACTIVE_MS = 10 * 1000
const defaultAppearanceSettings: EditorAppearanceSettings = {
  firstLineIndentSpaces: 2,
  lineHeight: 1.0,
  selectedFontPreset: 'system',
  customFontFamily: '',
  fontSize: 16,
  editorWidth: 'wide',
  paragraphSpacingLines: 1,
  textAlign: 'left',
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
const editorTextareaRef = ref<HTMLTextAreaElement | null>(null)
const formatUndoSnapshot = ref<FormatUndoSnapshot | null>(null)
const autoFormatMessage = ref('')
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
const formattedLastSavedAt = computed(() => formatDateTimeFull(lastSavedAt.value))
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
  lineHeight: String(appearanceSettings.value.lineHeight),
  textAlign: appearanceSettings.value.textAlign,
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
    autoFormatMessage.value = ''

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

// Auto-apply formatting when the user changes indent or spacing settings.
// Skips the initial value — only fires on subsequent user-initiated changes.
watch(
  () => appearanceSettings.value.firstLineIndentSpaces,
  (indent) => {
    if (localContent.value.trim()) {
      applyFormatToContent(indent, appearanceSettings.value.paragraphSpacingLines)
    }
  },
)
watch(
  () => appearanceSettings.value.paragraphSpacingLines,
  (spacing) => {
    if (localContent.value.trim()) {
      applyFormatToContent(appearanceSettings.value.firstLineIndentSpaces, spacing)
    }
  },
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

async function saveNow() {
  if (hasUnsavedChanges.value) {
    cancelPendingAutosave()
    await saveCurrentContent('manual')
  }
}

defineExpose({
  cancelPendingAutosave,
  saveNow,
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
    clearFormattingUndo()
    emit('dirtyChange', false)
    emit('saved', savedChapter)
    saveStatus.value = source === 'autosave' ? 'autosaved' : 'manual-saved'
    cloudSyncManager.notifyDirty(props.chapter.project_id)
    return
  }

  originalContent.value = savedChapter.content
  saveStatus.value = 'dirty'
  scheduleAutosave()
}

async function applyLoadedChapter(chapter: Chapter) {
  cancelPendingAutosave()
  clearFormattingUndo()
  if (chapter.id !== sessionChapterId.value) {
    sessionChapterId.value = chapter.id
    resetWritingSession(chapter.content)
  }
  isApplyingLoadedContent = true
  errorMessage.value = ''
  recoveryMessage.value = ''
  autoFormatMessage.value = ''
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
  clearFormattingUndo()
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
  clearFormattingUndo()
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

function isNetworkLikeError(error: unknown): boolean {
  return error instanceof TypeError || (error instanceof Error && error.message.includes('Failed to fetch'))
}

function readEditorAppearanceSettings(): EditorAppearanceSettings {
  const settings = safeReadJson<(Partial<EditorAppearanceSettings> & {
    fontFamily?: unknown
    firstLineIndent?: unknown
    lineHeight?: unknown
    paragraphSpacing?: unknown
  }) | null>(EDITOR_APPEARANCE_STORAGE_KEY, null)

  const legacyFontPreset = normalizeLegacyFontPreset(settings?.fontFamily)

  // Migrate firstLineIndent
  let firstLineIndentSpaces: FirstLineIndentSpaces = defaultAppearanceSettings.firstLineIndentSpaces
  if (settings?.firstLineIndent === '2em') {
    firstLineIndentSpaces = 2
  } else if (isFirstLineIndentSpaces(settings?.firstLineIndentSpaces)) {
    firstLineIndentSpaces = settings.firstLineIndentSpaces
  }

  // Migrate lineHeight
  let lineHeight: EditorLineHeight = defaultAppearanceSettings.lineHeight
  if (isEditorLineHeight(settings?.lineHeight)) {
    lineHeight = settings.lineHeight
  } else if (settings?.lineHeight === '1.4' || settings?.lineHeight === '1.6') {
    lineHeight = 1.5
  } else if (settings?.lineHeight === '1.8' || settings?.lineHeight === '2.0') {
    lineHeight = 2.0
  }

  // Migrate paragraphSpacing
  let paragraphSpacingLines: ParagraphSpacingLines = defaultAppearanceSettings.paragraphSpacingLines
  if (isParagraphSpacingLines(settings?.paragraphSpacingLines)) {
    paragraphSpacingLines = settings.paragraphSpacingLines
  } else if (settings?.paragraphSpacing === 'comfortable') {
    paragraphSpacingLines = 1
  }

  return {
    firstLineIndentSpaces,
    lineHeight,
    selectedFontPreset: isEditorFontPreset(settings?.selectedFontPreset)
      ? settings.selectedFontPreset
      : legacyFontPreset ?? defaultAppearanceSettings.selectedFontPreset,
    customFontFamily: typeof settings?.customFontFamily === 'string' ? settings.customFontFamily : '',
    fontSize: isEditorFontSize(settings?.fontSize) ? settings.fontSize : defaultAppearanceSettings.fontSize,
    editorWidth: isEditorWidth(settings?.editorWidth) ? settings.editorWidth : defaultAppearanceSettings.editorWidth,
    paragraphSpacingLines,
    textAlign: isEditorTextAlign(settings?.textAlign) ? settings.textAlign : defaultAppearanceSettings.textAlign,
    theme: isEditorTheme(settings?.theme) ? settings.theme : defaultAppearanceSettings.theme,
  }
}

function isFirstLineIndentSpaces(value: unknown): value is FirstLineIndentSpaces {
  return value === 0 || value === 2 || value === 4
}

function isEditorLineHeight(value: unknown): value is EditorLineHeight {
  return value === 1.0 || value === 1.5 || value === 2.0 || value === 2.5 || value === 3.0
}

function isParagraphSpacingLines(value: unknown): value is ParagraphSpacingLines {
  return value === 0 || value === 1 || value === 2
}

function isEditorTextAlign(value: unknown): value is EditorTextAlign {
  return value === 'left' || value === 'center' || value === 'right' || value === 'justify'
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
    full: 'min(100%, 920px)',
  }
  return widths[width]
}

function handleAutoFormat() {
  applyFormatToContent(
    appearanceSettings.value.firstLineIndentSpaces,
    appearanceSettings.value.paragraphSpacingLines,
  )
}

/**
 * Core formatting logic — applies indent and spacing to the current content.
 * Shared by the manual button and the settings-change watcher.
 */
function applyFormatToContent(
  indent: FirstLineIndentSpaces,
  spacing: ParagraphSpacingLines,
) {
  const textarea = editorTextareaRef.value
  const result = formatChapterContent(localContent.value, {
    firstLineIndentSpaces: indent,
    paragraphSpacingLines: spacing,
  })

  if (!result.changed) {
    autoFormatMessage.value = '内容无需排版，未做更改。'
    return
  }

  // Save undo snapshot before modifying content
  formatUndoSnapshot.value = {
    content: localContent.value,
    selectionStart: textarea?.selectionStart ?? 0,
    selectionEnd: textarea?.selectionEnd ?? 0,
    createdAt: Date.now(),
  }

  // Apply formatted content
  localContent.value = result.content

  // Save recovery draft (but don't autosave to backend)
  saveLocalDraft()

  autoFormatMessage.value = `已自动排版（${result.paragraphCount} 个段落），可撤销或保存。`
}

function handleUndoFormat() {
  const snapshot = formatUndoSnapshot.value
  if (!snapshot) {
    return
  }

  cancelPendingAutosave()

  // Restore content
  localContent.value = snapshot.content

  // Restore cursor position after DOM update
  nextTick(() => {
    const textarea = editorTextareaRef.value
    if (textarea) {
      textarea.selectionStart = snapshot.selectionStart
      textarea.selectionEnd = snapshot.selectionEnd
    }
  })

  // Clear undo snapshot
  formatUndoSnapshot.value = null

  // Save recovery draft
  saveLocalDraft()

  autoFormatMessage.value = '已撤销本次自动排版。'
}

function clearFormattingUndo() {
  formatUndoSnapshot.value = null
}
</script>

<template>
  <section class="chapter-editor" aria-label="章节编辑器">
    <header class="editor-toolbar">
      <div class="editor-title">
        <h2>{{ chapter.title }}</h2>
        <div class="writing-status-line" aria-label="写作状态">
          <span>当前字数 {{ localWordCount }}</span>
          <span aria-hidden="true">｜</span>
          <span>今日字数 --</span>
          <span aria-hidden="true">｜</span>
          <span>本小时 --</span>
          <span aria-hidden="true">｜</span>
          <span>本次写作 {{ sessionWritingMinutes }} 分钟</span>
          <span aria-hidden="true">｜</span>
          <span>速度 {{ sessionSpeedText }}<template v-if="sessionSpeedText !== '--'"> 字/小时</template></span>
          <span aria-hidden="true">｜</span>
          <span>上次保存 {{ formattedLastSavedAt }}</span>
          <span aria-hidden="true">｜</span>
          <span :class="{ warning: hasUnsavedChanges || errorMessage }">{{ saveStatusText }}</span>
        </div>
      </div>
    </header>

    <section v-if="pendingDraft" class="recovery-banner">
      <div>
        <h3>检测到未恢复的草稿</h3>
        <p>草稿更新时间：{{ formatDateTimeFull(pendingDraft.updated_at) }}，字数：{{ pendingDraft.word_count }}</p>
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
          <span>宽度</span>
          <select v-model="appearanceSettings.editorWidth">
            <option value="standard">标准</option>
            <option value="wide">宽</option>
            <option value="full">舒展</option>
          </select>
        </label>
        <div class="align-group" role="group" aria-label="对齐方式">
          <button
            type="button"
            :class="{ active: appearanceSettings.textAlign === 'left' }"
            title="左对齐"
            @click="appearanceSettings.textAlign = 'left'"
          >
            <svg width="16" height="14" viewBox="0 0 16 14" aria-hidden="true">
              <rect x="0" y="0" width="16" height="2" rx="0.5" fill="currentColor"/>
              <rect x="0" y="4" width="10" height="2" rx="0.5" fill="currentColor"/>
              <rect x="0" y="8" width="14" height="2" rx="0.5" fill="currentColor"/>
              <rect x="0" y="12" width="8" height="2" rx="0.5" fill="currentColor"/>
            </svg>
          </button>
          <button
            type="button"
            :class="{ active: appearanceSettings.textAlign === 'center' }"
            title="居中"
            @click="appearanceSettings.textAlign = 'center'"
          >
            <svg width="16" height="14" viewBox="0 0 16 14" aria-hidden="true">
              <rect x="0" y="0" width="16" height="2" rx="0.5" fill="currentColor"/>
              <rect x="3" y="4" width="10" height="2" rx="0.5" fill="currentColor"/>
              <rect x="1" y="8" width="14" height="2" rx="0.5" fill="currentColor"/>
              <rect x="4" y="12" width="8" height="2" rx="0.5" fill="currentColor"/>
            </svg>
          </button>
          <button
            type="button"
            :class="{ active: appearanceSettings.textAlign === 'right' }"
            title="右对齐"
            @click="appearanceSettings.textAlign = 'right'"
          >
            <svg width="16" height="14" viewBox="0 0 16 14" aria-hidden="true">
              <rect x="0" y="0" width="16" height="2" rx="0.5" fill="currentColor"/>
              <rect x="6" y="4" width="10" height="2" rx="0.5" fill="currentColor"/>
              <rect x="2" y="8" width="14" height="2" rx="0.5" fill="currentColor"/>
              <rect x="8" y="12" width="8" height="2" rx="0.5" fill="currentColor"/>
            </svg>
          </button>
          <button
            type="button"
            :class="{ active: appearanceSettings.textAlign === 'justify' }"
            title="两端对齐"
            @click="appearanceSettings.textAlign = 'justify'"
          >
            <svg width="16" height="14" viewBox="0 0 16 14" aria-hidden="true">
              <rect x="0" y="0" width="16" height="2" rx="0.5" fill="currentColor"/>
              <rect x="0" y="4" width="16" height="2" rx="0.5" fill="currentColor"/>
              <rect x="0" y="8" width="16" height="2" rx="0.5" fill="currentColor"/>
              <rect x="0" y="12" width="10" height="2" rx="0.5" fill="currentColor"/>
            </svg>
          </button>
        </div>
        <button
          class="primary-outline-button"
          type="button"
          @click="handleAutoFormat"
        >
          自动排版
        </button>
        <button
          v-if="formatUndoSnapshot"
          class="secondary-button"
          type="button"
          @click="handleUndoFormat"
        >
          撤销排版
        </button>
        <details ref="moreSettingsRef" class="more-settings" @toggle="handleMoreSettingsToggle">
          <summary>更多设置</summary>
          <div class="more-settings-menu">
            <label>
              <span>行间距</span>
              <select v-model.number="appearanceSettings.lineHeight">
                <option :value="1.0">1</option>
                <option :value="1.5">1.5</option>
                <option :value="2.0">2</option>
                <option :value="2.5">2.5</option>
                <option :value="3.0">3</option>
              </select>
            </label>
            <label>
              <span>首行缩进</span>
              <select v-model.number="appearanceSettings.firstLineIndentSpaces">
                <option :value="0">无</option>
                <option :value="2">2 空格</option>
                <option :value="4">4 空格</option>
              </select>
            </label>
            <label>
              <span>段落间距</span>
              <select v-model.number="appearanceSettings.paragraphSpacingLines">
                <option :value="0">无空行</option>
                <option :value="1">1 空行</option>
                <option :value="2">2 空行</option>
              </select>
            </label>
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
        ref="editorTextareaRef"
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
      <p v-if="autoFormatMessage" class="format-message">{{ autoFormatMessage }}</p>
    </footer>
  </section>
</template>

<style scoped>
.chapter-editor {
  display: grid;
  gap: var(--zs-space-3);
  min-width: 0;
}

.editor-toolbar {
  display: block;
}

.editor-title {
  display: grid;
  gap: var(--zs-space-1);
}

.editor-title h2 {
  margin: 0;
  color: var(--zs-color-text);
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.35;
}

.writing-status-line {
  margin: 0;
  color: var(--zs-color-text-muted);
  font-size: 0.78rem;
  display: flex;
  flex-wrap: wrap;
  gap: 2px var(--zs-space-2);
  align-items: center;
  line-height: 1.45;
}

.writing-status-line .warning {
  color: var(--zs-color-warning);
  font-weight: 700;
}

.recovery-banner {
  display: grid;
  gap: var(--zs-space-2);
  border: 1px solid var(--zs-color-warning);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-3);
  background: var(--zs-color-warning-soft);
}

.recovery-banner h3,
.recovery-banner p {
  margin: 0;
}

.recovery-banner h3 {
  color: var(--zs-color-warning);
  font-size: 1rem;
}

.recovery-banner p {
  color: var(--zs-color-text-muted);
  font-size: 0.88rem;
}

.recovery-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--zs-space-2);
}

.draft-preview {
  max-height: 220px;
  overflow: auto;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: var(--zs-space-3);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  white-space: pre-wrap;
}

.save-button,
.secondary-button,
.primary-outline-button {
  min-height: 30px;
  border-radius: var(--zs-radius-sm);
  padding: 0 var(--zs-space-2);
  font: inherit;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
}

.save-button {
  border: 1px solid var(--zs-color-primary);
  background: var(--zs-color-primary);
  color: var(--zs-color-on-primary);
}

.secondary-button {
  border: 1px solid var(--zs-color-border);
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
}

.primary-outline-button {
  border: 1px solid var(--zs-color-primary);
  background: var(--zs-color-primary-soft);
  color: var(--zs-color-primary);
}

.save-button:disabled {
  cursor: wait;
  opacity: 0.65;
}

.editor-textarea-shell {
  width: 100%;
  justify-self: center;
  min-width: 0;
}

.writing-toolbar {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  gap: var(--zs-space-1) var(--zs-space-2);
  align-items: center;
  margin-bottom: var(--zs-space-2);
  padding-bottom: var(--zs-space-2);
  border-bottom: 1px solid var(--zs-color-border-soft);
  color: var(--zs-color-text-faint);
  font-size: 0.78rem;
}

.writing-toolbar label {
  display: inline-flex;
  align-items: center;
  gap: var(--zs-space-1);
}

.writing-toolbar select {
  min-height: 26px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 6px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  font-size: 0.8rem;
}

.writing-toolbar input {
  min-height: 30px;
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 8px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
}

.align-group {
  display: inline-flex;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  overflow: hidden;
}

.align-group button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  min-width: 30px;
  border: none;
  border-right: 1px solid var(--zs-color-border-soft);
  padding: 0 var(--zs-space-2);
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  cursor: pointer;
}

.align-group button:last-child {
  border-right: none;
}

.align-group button.active {
  background: var(--zs-color-surface-soft);
  color: var(--zs-color-primary);
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
  min-height: 26px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-sm);
  padding: 0 8px;
  background: var(--zs-color-surface);
  color: var(--zs-color-text-muted);
  font-size: 0.8rem;
  font-weight: 600;
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
  gap: var(--zs-space-2);
  min-width: 240px;
  border: 1px solid var(--zs-color-border);
  border-radius: var(--zs-radius-md);
  padding: var(--zs-space-3);
  background: var(--zs-color-surface);
  box-shadow: var(--zs-shadow-md);
}

.more-settings-menu label {
  align-items: stretch;
  justify-content: space-between;
}

.editor-textarea {
  width: 100%;
  min-height: clamp(420px, calc(100vh - 270px), 760px);
  box-sizing: border-box;
  border: 1px solid var(--zs-color-border-soft);
  border-radius: var(--zs-radius-sm);
  padding: 24px 28px;
  resize: vertical;
  background: var(--zs-color-surface);
  color: var(--zs-color-text);
  font: inherit;
  white-space: pre-wrap;
  line-height: 1.8;
}

.editor-textarea:focus {
  border-color: var(--zs-color-border-strong);
  outline: none;
}

.editor-messages {
  min-height: 22px;
}

.error-message,
.recovery-message {
  margin: 0;
  font-size: 0.86rem;
  font-weight: 600;
}

.error-message {
  color: var(--zs-color-danger);
}

.recovery-message {
  color: var(--zs-color-success);
}

.format-message {
  margin: 0;
  color: var(--zs-color-info);
  font-size: 0.84rem;
  font-weight: 600;
}

@media (max-width: 1320px) {
  .writing-toolbar {
    gap: var(--zs-space-1) var(--zs-space-2);
  }

  .writing-toolbar label span {
    font-size: 0.76rem;
  }
}

@media (max-width: 1099px) {
  .save-button,
  .secondary-button,
  .primary-outline-button {
    width: auto;
  }

  .writing-toolbar {
    align-items: center;
  }

  .writing-status-line {
    font-size: 0.72rem;
  }

  .editor-textarea {
    min-height: clamp(380px, calc(100vh - 280px), 680px);
    padding: 20px 22px;
  }
}

@media (max-width: 720px) {
  .more-settings-menu {
    position: static;
    margin-top: 8px;
  }
}
</style>
