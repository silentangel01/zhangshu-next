export function formatNumber(value: number): string {
  if (value === 0) {
    return '0'
  }

  const absValue = Math.abs(value)
  if (absValue >= 10000) {
    return `${(value / 10000).toFixed(1)}万`
  }

  return value.toLocaleString('zh-CN')
}

export function formatSignedWords(value: number): string {
  if (value === 0) {
    return '0'
  }

  const prefix = value > 0 ? '+' : ''
  return `${prefix}${formatNumber(value)}`
}

export function formatPercent(value: number | null): string {
  if (value === null || value === undefined) {
    return '—'
  }

  return `${value.toFixed(1)}%`
}

export function formatMinutes(value: number): string {
  if (value <= 0) {
    return '0 分钟'
  }

  if (value < 60) {
    return `${value} 分钟`
  }

  const hours = Math.floor(value / 60)
  const minutes = value % 60
  if (minutes === 0) {
    return `${hours} 小时`
  }

  return `${hours} 小时 ${minutes} 分钟`
}

export function getHeatmapLevel(netWords: number): 0 | 1 | 2 | 3 | 4 {
  if (netWords <= 0) {
    return 0
  }

  if (netWords < 500) {
    return 1
  }

  if (netWords < 2000) {
    return 2
  }

  if (netWords < 5000) {
    return 3
  }

  return 4
}

export function formatWordsPerHour(value: number): string {
  if (value <= 0) {
    return '—'
  }

  return `${Math.round(value)}`
}
