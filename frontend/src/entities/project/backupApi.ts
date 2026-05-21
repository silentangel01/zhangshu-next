import { API_BASE_URL } from '@/shared/api/client'

import type { RestoreReport } from './backupTypes'

async function parseJsonResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `请求失败：${response.status}`
    try {
      const payload = (await response.json()) as { detail?: unknown }
      if (typeof payload.detail === 'string') {
        message = payload.detail
      }
    } catch {
      // Keep status message.
    }
    throw new Error(message)
  }

  return response.json() as Promise<T>
}

export async function downloadProjectBackup(projectId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/projects/${projectId}/backup`, {
    method: 'POST',
  })

  if (!response.ok) {
    throw new Error('导出项目备份失败')
  }

  const blob = await response.blob()
  const disposition = response.headers.get('Content-Disposition') ?? ''
  const filenameMatch = disposition.match(/filename="([^"]+)"/)
  const filename = filenameMatch?.[1] ?? `zhangshu-project-backup-${projectId}.zip`
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export async function restoreProjectBackup(file: File): Promise<RestoreReport> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/projects/backup/restore`, {
    method: 'POST',
    body: formData,
  })

  return parseJsonResponse<RestoreReport>(response)
}
