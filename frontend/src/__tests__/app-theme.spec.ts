import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import {
  APP_THEME_STORAGE_KEY,
  type AppTheme,
  applyAppTheme,
  getInitialAppTheme,
  isAppTheme,
  readAppTheme,
  writeAppTheme,
} from '../shared/theme/appTheme'

describe('appTheme', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  afterEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute('data-theme')
  })

  describe('isAppTheme', () => {
    it('returns true for valid themes', () => {
      expect(isAppTheme('default')).toBe(true)
      expect(isAppTheme('eye-care')).toBe(true)
      expect(isAppTheme('dark')).toBe(true)
    })

    it('returns false for invalid values', () => {
      expect(isAppTheme('light')).toBe(false)
      expect(isAppTheme('')).toBe(false)
      expect(isAppTheme(null)).toBe(false)
      expect(isAppTheme(undefined)).toBe(false)
      expect(isAppTheme(42)).toBe(false)
    })
  })

  describe('readAppTheme', () => {
    it('returns stored theme when valid', () => {
      localStorage.setItem(APP_THEME_STORAGE_KEY, 'dark')
      expect(readAppTheme()).toBe('dark')
    })

    it('returns default when storage is empty', () => {
      expect(readAppTheme()).toBe('default')
    })

    it('returns default when stored value is invalid', () => {
      localStorage.setItem(APP_THEME_STORAGE_KEY, 'invalid-theme')
      expect(readAppTheme()).toBe('default')
    })
  })

  describe('writeAppTheme', () => {
    it('persists theme to localStorage', () => {
      writeAppTheme('eye-care')
      expect(localStorage.getItem(APP_THEME_STORAGE_KEY)).toBe('eye-care')
    })

    it('overwrites previous value', () => {
      writeAppTheme('dark')
      writeAppTheme('default')
      expect(localStorage.getItem(APP_THEME_STORAGE_KEY)).toBe('default')
    })
  })

  describe('applyAppTheme', () => {
    it('removes data-theme attribute for default theme', () => {
      document.documentElement.dataset.theme = 'dark'
      applyAppTheme('default')
      expect(document.documentElement.hasAttribute('data-theme')).toBe(false)
    })

    it('sets data-theme attribute for eye-care theme', () => {
      applyAppTheme('eye-care')
      expect(document.documentElement.dataset.theme).toBe('eye-care')
    })

    it('sets data-theme attribute for dark theme', () => {
      applyAppTheme('dark')
      expect(document.documentElement.dataset.theme).toBe('dark')
    })
  })

  describe('getInitialAppTheme', () => {
    it('returns stored theme on initialization', () => {
      localStorage.setItem(APP_THEME_STORAGE_KEY, 'eye-care')
      expect(getInitialAppTheme()).toBe('eye-care')
    })

    it('returns default when no theme is stored', () => {
      expect(getInitialAppTheme()).toBe('default')
    })
  })

  describe('full theme cycle', () => {
    it('write → read → apply round-trips correctly', () => {
      const themes: AppTheme[] = ['default', 'eye-care', 'dark']

      for (const theme of themes) {
        writeAppTheme(theme)
        const read = readAppTheme()
        expect(read).toBe(theme)
        applyAppTheme(read)

        if (theme === 'default') {
          expect(document.documentElement.hasAttribute('data-theme')).toBe(false)
        } else {
          expect(document.documentElement.dataset.theme).toBe(theme)
        }
      }
    })
  })
})
