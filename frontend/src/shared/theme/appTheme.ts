export type AppTheme = 'default' | 'eye-care' | 'dark'

export const APP_THEME_STORAGE_KEY = 'zhangshu:app:theme'

const VALID_THEMES: ReadonlySet<AppTheme> = new Set(['default', 'eye-care', 'dark'])

export function isAppTheme(value: unknown): value is AppTheme {
  return typeof value === 'string' && VALID_THEMES.has(value as AppTheme)
}

export function readAppTheme(): AppTheme {
  try {
    const raw = localStorage.getItem(APP_THEME_STORAGE_KEY)
    if (isAppTheme(raw)) {
      return raw
    }
  } catch {
    // localStorage may be unavailable in private browsing or test environments.
  }
  return 'default'
}

export function writeAppTheme(theme: AppTheme): void {
  try {
    localStorage.setItem(APP_THEME_STORAGE_KEY, theme)
  } catch {
    // Silently ignore write failures.
  }
}

export function applyAppTheme(theme: AppTheme): void {
  if (theme === 'default') {
    document.documentElement.removeAttribute('data-theme')
  } else {
    document.documentElement.dataset.theme = theme
  }
}

export function getInitialAppTheme(): AppTheme {
  return readAppTheme()
}
