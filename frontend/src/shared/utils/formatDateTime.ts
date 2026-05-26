const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
})

const dateFormatterFull = new Intl.DateTimeFormat(undefined, {
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
})

/**
 * 格式化日期时间为本地化短格式（如 "2026年5月26日 14:30"）
 * 适用于列表、卡片等常规时间展示
 */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  return dateFormatter.format(new Date(value))
}

/**
 * 格式化日期时间为本地化完整格式（如 "2026/05/26 14:30:00"）
 * 适用于版本历史、日志等需要精确到秒的场景
 */
export function formatDateTimeFull(value: string | null | undefined): string {
  if (!value) return '—'
  return dateFormatterFull.format(new Date(value))
}
