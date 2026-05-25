import { describe, expect, it } from 'vitest'

import {
  formatMinutes,
  formatNumber,
  formatPercent,
  formatSignedWords,
  formatWordsPerHour,
  getHeatmapLevel,
} from '../features/stats/statsFormatters'

describe('formatNumber', () => {
  it('formats zero', () => {
    expect(formatNumber(0)).toBe('0')
  })

  it('formats small numbers', () => {
    expect(formatNumber(42)).toBe('42')
    expect(formatNumber(999)).toBe('999')
  })

  it('formats thousands with locale', () => {
    const result = formatNumber(5000)
    expect(result).toContain('5')
  })

  it('formats ten-thousands with 万 suffix', () => {
    expect(formatNumber(10000)).toBe('1.0万')
    expect(formatNumber(56789)).toBe('5.7万')
    expect(formatNumber(123456)).toBe('12.3万')
  })

  it('handles negative numbers', () => {
    expect(formatNumber(-500)).toBe('-500')
    expect(formatNumber(-15000)).toBe('-1.5万')
  })
})

describe('formatSignedWords', () => {
  it('formats zero without sign', () => {
    expect(formatSignedWords(0)).toBe('0')
  })

  it('formats positive with + prefix', () => {
    expect(formatSignedWords(100)).toBe('+100')
    expect(formatSignedWords(5000)).toBe('+5,000')
  })

  it('formats negative with - prefix', () => {
    expect(formatSignedWords(-100)).toBe('-100')
    expect(formatSignedWords(-5000)).toBe('-5,000')
  })
})

describe('formatPercent', () => {
  it('returns dash for null', () => {
    expect(formatPercent(null)).toBe('—')
  })

  it('formats zero', () => {
    expect(formatPercent(0)).toBe('0.0%')
  })

  it('formats with one decimal', () => {
    expect(formatPercent(42.56)).toBe('42.6%')
    expect(formatPercent(100)).toBe('100.0%')
  })
})

describe('formatMinutes', () => {
  it('formats zero', () => {
    expect(formatMinutes(0)).toBe('0 分钟')
  })

  it('formats minutes only', () => {
    expect(formatMinutes(45)).toBe('45 分钟')
  })

  it('formats hours only', () => {
    expect(formatMinutes(120)).toBe('2 小时')
  })

  it('formats hours and minutes', () => {
    expect(formatMinutes(95)).toBe('1 小时 35 分钟')
  })

  it('handles negative values', () => {
    expect(formatMinutes(-5)).toBe('0 分钟')
  })
})

describe('getHeatmapLevel', () => {
  it('returns 0 for zero or negative', () => {
    expect(getHeatmapLevel(0)).toBe(0)
    expect(getHeatmapLevel(-100)).toBe(0)
    expect(getHeatmapLevel(-5000)).toBe(0)
  })

  it('returns 1 for 1-499', () => {
    expect(getHeatmapLevel(1)).toBe(1)
    expect(getHeatmapLevel(499)).toBe(1)
  })

  it('returns 2 for 500-1999', () => {
    expect(getHeatmapLevel(500)).toBe(2)
    expect(getHeatmapLevel(1999)).toBe(2)
  })

  it('returns 3 for 2000-4999', () => {
    expect(getHeatmapLevel(2000)).toBe(3)
    expect(getHeatmapLevel(4999)).toBe(3)
  })

  it('returns 4 for 5000+', () => {
    expect(getHeatmapLevel(5000)).toBe(4)
    expect(getHeatmapLevel(10000)).toBe(4)
    expect(getHeatmapLevel(50000)).toBe(4)
  })

  it('handles boundary values correctly', () => {
    expect(getHeatmapLevel(499)).toBe(1)
    expect(getHeatmapLevel(500)).toBe(2)
    expect(getHeatmapLevel(1999)).toBe(2)
    expect(getHeatmapLevel(2000)).toBe(3)
    expect(getHeatmapLevel(4999)).toBe(3)
    expect(getHeatmapLevel(5000)).toBe(4)
  })
})

describe('formatWordsPerHour', () => {
  it('returns dash for zero', () => {
    expect(formatWordsPerHour(0)).toBe('—')
  })

  it('returns dash for negative', () => {
    expect(formatWordsPerHour(-100)).toBe('—')
  })

  it('formats positive as rounded integer', () => {
    expect(formatWordsPerHour(1136.8)).toBe('1137')
    expect(formatWordsPerHour(500)).toBe('500')
  })
})
