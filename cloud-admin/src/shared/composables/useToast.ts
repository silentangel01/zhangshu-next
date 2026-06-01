import { reactive, readonly } from 'vue'

export interface Toast {
  id: number
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
}

const toasts = reactive<Toast[]>([])
let nextId = 0

function addToast(type: Toast['type'], message: string, duration: number) {
  const id = nextId++
  toasts.push({ id, type, message })
  if (duration > 0) {
    setTimeout(() => removeToast(id), duration)
  }
}

function removeToast(id: number) {
  const idx = toasts.findIndex((t) => t.id === id)
  if (idx !== -1) toasts.splice(idx, 1)
}

export function useToast() {
  return {
    toasts: readonly(toasts),
    remove: removeToast,
    success: (msg: string) => addToast('success', msg, 4000),
    error: (msg: string) => addToast('error', msg, 6000),
    warning: (msg: string) => addToast('warning', msg, 5000),
    info: (msg: string) => addToast('info', msg, 4000),
  }
}
