export function safeReadJson<T>(key: string, fallback: T): T {
  try {
    const value = window.localStorage.getItem(key)
    if (!value) {
      return fallback
    }
    return JSON.parse(value) as T
  } catch {
    return fallback
  }
}

export function safeWriteJson(key: string, value: unknown) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // localStorage may be unavailable in private or restricted browser contexts.
  }
}

export function removeStorageKey(key: string) {
  try {
    window.localStorage.removeItem(key)
  } catch {
    // localStorage may be unavailable in private or restricted browser contexts.
  }
}
