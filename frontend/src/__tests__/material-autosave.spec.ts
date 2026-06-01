/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useDebouncedAutosave } from '@/shared/composables/useDebouncedAutosave'

const DELAY = 3000

/**
 * These tests verify the autosave integration patterns used by
 * ProjectCharactersPage, ProjectSettingsPage, and ProjectCluesPage.
 *
 * Rather than mounting full page components (which require router + many API mocks),
 * we simulate each page's canSave/hasChanges/save callbacks to verify the composable
 * works correctly with each page's specific constraints.
 */

describe('material autosave integration patterns', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  describe('character page pattern', () => {
    it('existing entity edit triggers autosave after delay', async () => {
      const save = vi.fn().mockResolvedValue(undefined)
      let isCreating = false
      let selectedCharacter: { id: string } | null = { id: 'char-1' }
      let formName = '张三'
      let isSaving = false
      let baseline = JSON.stringify({ name: '张三' })

      const autosave = useDebouncedAutosave({
        delayMs: DELAY,
        canSave: () => !isCreating && selectedCharacter !== null && formName.trim() !== '' && !isSaving,
        hasChanges: () => JSON.stringify({ name: formName }) !== baseline,
        save,
      })

      // Simulate editing the name field
      formName = '李四'
      autosave.schedule()

      expect(save).not.toHaveBeenCalled()

      await vi.advanceTimersByTimeAsync(DELAY)

      expect(save).toHaveBeenCalledTimes(1)
    })

    it('blank new mode does NOT trigger autosave', async () => {
      const save = vi.fn().mockResolvedValue(undefined)
      let isCreating = true
      let selectedCharacter: { id: string } | null = null
      let formName = ''

      const autosave = useDebouncedAutosave({
        delayMs: DELAY,
        canSave: () => !isCreating && selectedCharacter !== null && formName.trim() !== '',
        hasChanges: () => true,
        save,
      })

      autosave.schedule()

      await vi.advanceTimersByTimeAsync(DELAY)

      expect(save).not.toHaveBeenCalled()
    })

    it('graph-created draft (existing entity with minimal data) triggers autosave', async () => {
      const save = vi.fn().mockResolvedValue(undefined)
      // Graph creates entity with just name and summary, then user opens character page
      const isCreating = false
      const selectedCharacter = { id: 'graph-created-char' }
      let formName = '新角色'
      const baseline = JSON.stringify({ name: '新角色', summary: '' })

      const autosave = useDebouncedAutosave({
        delayMs: DELAY,
        canSave: () => !isCreating && selectedCharacter !== null && formName.trim() !== '',
        hasChanges: () =>
          JSON.stringify({ name: formName, summary: 'edited summary' }) !== baseline,
        save,
      })

      // User edits summary
      autosave.schedule()

      await vi.advanceTimersByTimeAsync(DELAY)

      expect(save).toHaveBeenCalledTimes(1)
    })

    it('required name empty does NOT trigger autosave', async () => {
      const save = vi.fn().mockResolvedValue(undefined)
      const isCreating = false
      const selectedCharacter = { id: 'char-1' }
      const formName = '' // empty name

      const autosave = useDebouncedAutosave({
        delayMs: DELAY,
        canSave: () => !isCreating && selectedCharacter !== null && formName.trim() !== '',
        hasChanges: () => true,
        save,
      })

      autosave.schedule()

      await vi.advanceTimersByTimeAsync(DELAY)

      expect(save).not.toHaveBeenCalled()
    })

    it('manual save cancels pending autosave', async () => {
      const save = vi.fn().mockResolvedValue(undefined)

      const autosave = useDebouncedAutosave({
        delayMs: DELAY,
        canSave: () => true,
        hasChanges: () => true,
        save,
      })

      // Autosave is scheduled
      autosave.schedule()

      // User clicks save button — cancels pending autosave
      autosave.cancel()

      await vi.advanceTimersByTimeAsync(DELAY)

      // Autosave should NOT have fired
      expect(save).not.toHaveBeenCalled()
    })
  })

  describe('setting page pattern', () => {
    it('existing entity edit triggers autosave', async () => {
      const save = vi.fn().mockResolvedValue(undefined)
      const isCreating = false
      const selectedSetting = { id: 'set-1' }
      let formTitle = '原始标题'
      const baseline = JSON.stringify({ title: '原始标题' })

      const autosave = useDebouncedAutosave({
        delayMs: DELAY,
        canSave: () => !isCreating && selectedSetting !== null && formTitle.trim() !== '',
        hasChanges: () => JSON.stringify({ title: formTitle }) !== baseline,
        save,
      })

      formTitle = '修改后标题'
      autosave.schedule()

      await vi.advanceTimersByTimeAsync(DELAY)

      expect(save).toHaveBeenCalledTimes(1)
    })

    it('folder edit triggers autosave', async () => {
      const save = vi.fn().mockResolvedValue(undefined)
      const isCreating = false
      const selectedSetting = { id: 'folder-1' }
      let formTitle = '目录名'
      const baseline = JSON.stringify({ title: '目录名', node_kind: 'folder' })

      const autosave = useDebouncedAutosave({
        delayMs: DELAY,
        canSave: () => !isCreating && selectedSetting !== null && formTitle.trim() !== '',
        hasChanges: () =>
          JSON.stringify({ title: formTitle, node_kind: 'folder' }) !== baseline,
        save,
      })

      formTitle = '新目录名'
      autosave.schedule()

      await vi.advanceTimersByTimeAsync(DELAY)

      expect(save).toHaveBeenCalledTimes(1)
    })
  })

  describe('clue page pattern', () => {
    it('existing entity edit triggers autosave', async () => {
      const save = vi.fn().mockResolvedValue(undefined)
      const isCreating = false
      const selectedClue = { id: 'clue-1' }
      let formTitle = '伏笔名'
      let formStatus = 'planned'
      const baseline = JSON.stringify({ title: '伏笔名', status: 'planned' })

      const autosave = useDebouncedAutosave({
        delayMs: DELAY,
        canSave: () => !isCreating && selectedClue !== null && formTitle.trim() !== '',
        hasChanges: () =>
          JSON.stringify({ title: formTitle, status: formStatus }) !== baseline,
        save,
      })

      formStatus = 'planted'
      autosave.schedule()

      await vi.advanceTimersByTimeAsync(DELAY)

      expect(save).toHaveBeenCalledTimes(1)
    })
  })

  describe('cross-page patterns', () => {
    it('autosave failure does not clear form — error status is set', async () => {
      const save = vi.fn().mockRejectedValue(new Error('网络错误'))

      const autosave = useDebouncedAutosave({
        delayMs: DELAY,
        canSave: () => true,
        hasChanges: () => true,
        save,
      })

      autosave.schedule()

      await vi.advanceTimersByTimeAsync(DELAY)
      await vi.runAllTimersAsync()

      expect(autosave.status.value).toBe('error')
      expect(autosave.errorMessage.value).toBe('网络错误')
      // Form data is untouched — the composable never touches form data
    })

    it('switching entity flushes pending autosave', async () => {
      const save = vi.fn().mockResolvedValue(undefined)

      const autosave = useDebouncedAutosave({
        delayMs: DELAY,
        canSave: () => true,
        hasChanges: () => true,
        save,
      })

      autosave.schedule()

      // Before switching, flush
      const flushed = await autosave.flush()

      expect(flushed).toBe(true)
      expect(save).toHaveBeenCalledTimes(1)
    })

    it('flush failure blocks switch', async () => {
      const save = vi.fn().mockRejectedValue(new Error('保存失败'))

      const autosave = useDebouncedAutosave({
        delayMs: DELAY,
        canSave: () => true,
        hasChanges: () => true,
        save,
      })

      autosave.schedule()

      const flushed = await autosave.flush()

      expect(flushed).toBe(false)
      expect(autosave.status.value).toBe('error')
      // Page should check flushed === false and block the switch
    })

    it('no changes between entities — flush returns true without saving', async () => {
      const save = vi.fn().mockResolvedValue(undefined)

      const autosave = useDebouncedAutosave({
        delayMs: DELAY,
        canSave: () => true,
        hasChanges: () => false, // no pending changes
        save,
      })

      const flushed = await autosave.flush()

      expect(flushed).toBe(true)
      expect(save).not.toHaveBeenCalled()
    })
  })
})
