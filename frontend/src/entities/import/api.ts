import { API_BASE_URL } from '@/shared/api/client'

import type { ConfirmImportPayload, ImportPreview, ImportReport, ImportType } from './types'

async function parseResponse<T>(response: Response): Promise<T> {
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

export async function previewImport(file: File, importType: ImportType): Promise<ImportPreview> {
  const formData = new FormData()
  formData.append('import_type', importType)
  formData.append('file', file)

  const response = await fetch(`${API_BASE_URL}/api/imports/preview`, {
    method: 'POST',
    body: formData,
  })

  return parseResponse<ImportPreview>(response)
}

export async function previewProjectImport(files: File[]): Promise<ImportPreview> {
  const formData = new FormData()
  files.forEach((file) => {
    const relativePath = (file as File & { webkitRelativePath?: string }).webkitRelativePath
    formData.append('files', file, relativePath || file.name)
  })

  const response = await fetch(`${API_BASE_URL}/api/projects/import/preview`, {
    method: 'POST',
    body: formData,
  })

  return parseResponse<ImportPreview>(response)
}

export async function commitProjectImport(payload: ConfirmImportPayload): Promise<ImportReport> {
  const response = await fetch(`${API_BASE_URL}/api/projects/import/commit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  return parseResponse<ImportReport>(response)
}

export async function confirmImport(
  importId: string,
  payload: ConfirmImportPayload,
): Promise<ImportReport> {
  const response = await fetch(`${API_BASE_URL}/api/imports/${importId}/confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  return parseResponse<ImportReport>(response)
}
