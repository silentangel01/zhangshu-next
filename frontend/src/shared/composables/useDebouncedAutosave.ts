import { ref } from 'vue'

export type AutosaveStatus = 'idle' | 'dirty' | 'saving' | 'saved' | 'error'

export interface UseDebouncedAutosaveOptions {
  delayMs: number
  canSave: () => boolean
  hasChanges: () => boolean
  save: () => Promise<void>
}

export interface UseDebouncedAutosaveReturn {
  status: ReturnType<typeof ref<AutosaveStatus>>
  errorMessage: ReturnType<typeof ref<string>>
  schedule: () => void
  cancel: () => void
  flush: () => Promise<boolean>
  markSaved: () => void
  markDirty: () => void
}

export function useDebouncedAutosave(
  options: UseDebouncedAutosaveOptions,
): UseDebouncedAutosaveReturn {
  const status = ref<AutosaveStatus>('idle')
  const errorMessage = ref('')

  let timer: ReturnType<typeof setTimeout> | null = null

  function clearTimer() {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
  }

  async function executeSave() {
    if (!options.canSave() || !options.hasChanges()) {
      return
    }

    status.value = 'saving'
    errorMessage.value = ''

    try {
      await options.save()
      status.value = 'saved'
    } catch (e) {
      status.value = 'error'
      errorMessage.value = e instanceof Error ? e.message : '自动保存失败'
    }
  }

  function schedule() {
    clearTimer()

    if (!options.canSave() || !options.hasChanges()) {
      return
    }

    status.value = 'dirty'

    timer = setTimeout(() => {
      timer = null
      void executeSave()
    }, options.delayMs)
  }

  function cancel() {
    clearTimer()
  }

  async function flush(): Promise<boolean> {
    clearTimer()

    if (!options.canSave() || !options.hasChanges()) {
      return true
    }

    status.value = 'saving'
    errorMessage.value = ''

    try {
      await options.save()
      status.value = 'saved'
      return true
    } catch (e) {
      status.value = 'error'
      errorMessage.value = e instanceof Error ? e.message : '自动保存失败'
      return false
    }
  }

  function markSaved() {
    status.value = 'saved'
    errorMessage.value = ''
  }

  function markDirty() {
    status.value = 'dirty'
  }

  return {
    status,
    errorMessage,
    schedule,
    cancel,
    flush,
    markSaved,
    markDirty,
  }
}
