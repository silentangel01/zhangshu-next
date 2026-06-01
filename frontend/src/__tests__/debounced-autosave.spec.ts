/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useDebouncedAutosave } from '@/shared/composables/useDebouncedAutosave'

const DELAY = 3000

describe('useDebouncedAutosave', () => {
  let saveMock: ReturnType<typeof vi.fn>
  let canSave: boolean
  let hasChanges: boolean

  beforeEach(() => {
    vi.useFakeTimers()
    saveMock = vi.fn().mockResolvedValue(undefined)
    canSave = true
    hasChanges = true
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  function create(options?: Partial<{ delayMs: number }>) {
    return useDebouncedAutosave({
      delayMs: options?.delayMs ?? DELAY,
      canSave: () => canSave,
      hasChanges: () => hasChanges,
      save: saveMock as () => Promise<void>,
    })
  }

  describe('schedule', () => {
    it('triggers save after delay', async () => {
      const { schedule } = create()
      schedule()

      expect(saveMock).not.toHaveBeenCalled()

      await vi.advanceTimersByTimeAsync(DELAY)

      expect(saveMock).toHaveBeenCalledTimes(1)
    })

    it('multiple schedules within delay only trigger one save', async () => {
      const { schedule } = create()
      schedule()
      schedule()
      schedule()

      await vi.advanceTimersByTimeAsync(DELAY)

      expect(saveMock).toHaveBeenCalledTimes(1)
    })

    it('does not save when canSave returns false', async () => {
      canSave = false
      const { schedule } = create()
      schedule()

      await vi.advanceTimersByTimeAsync(DELAY)

      expect(saveMock).not.toHaveBeenCalled()
    })

    it('does not save when hasChanges returns false', async () => {
      hasChanges = false
      const { schedule } = create()
      schedule()

      await vi.advanceTimersByTimeAsync(DELAY)

      expect(saveMock).not.toHaveBeenCalled()
    })

    it('sets status to dirty when scheduled', () => {
      const { schedule, status } = create()
      schedule()
      expect(status.value).toBe('dirty')
    })

    it('sets status to saving during save', async () => {
      let resolveSave!: () => void
      saveMock.mockImplementationOnce(
        () => new Promise<void>((resolve) => { resolveSave = resolve }),
      )

      const { schedule, status } = create()
      schedule()

      await vi.advanceTimersByTimeAsync(DELAY)
      expect(status.value).toBe('saving')

      resolveSave()
      await vi.runAllTimersAsync()
      expect(status.value).toBe('saved')
    })

    it('sets status to saved after successful save', async () => {
      const { schedule, status } = create()
      schedule()

      await vi.advanceTimersByTimeAsync(DELAY)
      await vi.runAllTimersAsync()

      expect(status.value).toBe('saved')
    })
  })

  describe('cancel', () => {
    it('prevents pending save from executing', async () => {
      const { schedule, cancel } = create()
      schedule()
      cancel()

      await vi.advanceTimersByTimeAsync(DELAY)

      expect(saveMock).not.toHaveBeenCalled()
    })
  })

  describe('flush', () => {
    it('immediately saves pending change', async () => {
      const { schedule, flush } = create()
      schedule()

      const result = await flush()

      expect(saveMock).toHaveBeenCalledTimes(1)
      expect(result).toBe(true)
    })

    it('returns true when canSave is false', async () => {
      canSave = false
      const { schedule, flush } = create()
      schedule()

      const result = await flush()

      expect(saveMock).not.toHaveBeenCalled()
      expect(result).toBe(true)
    })

    it('returns true when hasChanges is false', async () => {
      hasChanges = false
      const { schedule, flush } = create()
      schedule()

      const result = await flush()

      expect(saveMock).not.toHaveBeenCalled()
      expect(result).toBe(true)
    })

    it('returns false and sets error status on save failure', async () => {
      saveMock.mockRejectedValueOnce(new Error('网络错误'))
      const { schedule, flush, status, errorMessage } = create()
      schedule()

      const result = await flush()

      expect(result).toBe(false)
      expect(status.value).toBe('error')
      expect(errorMessage.value).toBe('网络错误')
    })

    it('cancels pending timer before saving', async () => {
      const { schedule, flush } = create()
      schedule()

      await flush()

      // Advance past the original delay — should not trigger a second save
      await vi.advanceTimersByTimeAsync(DELAY)

      expect(saveMock).toHaveBeenCalledTimes(1)
    })
  })

  describe('save failure', () => {
    it('sets status to error on scheduled save failure', async () => {
      saveMock.mockRejectedValueOnce(new Error('服务器错误'))
      const { schedule, status, errorMessage } = create()
      schedule()

      await vi.advanceTimersByTimeAsync(DELAY)
      await vi.runAllTimersAsync()

      expect(status.value).toBe('error')
      expect(errorMessage.value).toBe('服务器错误')
    })

    it('uses fallback message for non-Error throws', async () => {
      saveMock.mockRejectedValueOnce('unknown error')
      const { schedule, status, errorMessage } = create()
      schedule()

      await vi.advanceTimersByTimeAsync(DELAY)
      await vi.runAllTimersAsync()

      expect(status.value).toBe('error')
      expect(errorMessage.value).toBe('自动保存失败')
    })
  })

  describe('markSaved / markDirty', () => {
    it('markSaved sets status to saved and clears error', () => {
      const { markSaved, status, errorMessage } = create()
      status.value = 'error'
      errorMessage.value = 'some error'

      markSaved()

      expect(status.value).toBe('saved')
      expect(errorMessage.value).toBe('')
    })

    it('markDirty sets status to dirty', () => {
      const { markDirty, status } = create()
      markDirty()
      expect(status.value).toBe('dirty')
    })
  })
})
