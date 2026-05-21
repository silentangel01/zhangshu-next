import { API_BASE_URL } from '@/shared/api/client'

import type { ManuscriptExportPayload } from './exportTypes'

export async function downloadManuscriptExport(
  projectId: string,
  payload: ManuscriptExportPayload,
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/export`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    let message = '导出失败，请稍后重试'
    try {
      const errorPayload = (await response.json()) as { detail?: unknown }
      if (typeof errorPayload.detail === 'string') {
        message = errorPayload.detail
      }
    } catch {
      // Keep fallback.
    }
    throw new Error(message)
  }

  const blob = await response.blob()
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const filenameMatch = disposition.match(/filename="([^"]+)"/)
  const extension = payload.format === 'md' ? 'md' : payload.format
  const filename = filenameMatch?.[1] ?? `zhangshu-manuscript.${extension}`
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
