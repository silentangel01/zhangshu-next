export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown
}

export class ApiError extends Error {
  status: number
  suggestion?: string
  errorKind?: string

  constructor(message: string, status: number, suggestion?: string, errorKind?: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.suggestion = suggestion
    this.errorKind = errorKind
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)

  if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })

  if (!response.ok) {
    let message = `API request failed: ${response.status}`
    let suggestion: string | undefined
    let errorKind: string | undefined

    try {
      const payload = (await response.json()) as { detail?: unknown }
      if (typeof payload.detail === 'string') {
        message = payload.detail
      } else if (payload.detail && typeof payload.detail === 'object') {
        const d = payload.detail as Record<string, unknown>
        if (typeof d.detail === 'string') message = d.detail
        if (typeof d.suggestion === 'string') suggestion = d.suggestion
        if (typeof d.error_kind === 'string') errorKind = d.error_kind
      }
    } catch {
      // Keep the status-based message when the API does not return JSON.
    }

    throw new ApiError(message, response.status, suggestion, errorKind)
  }

  const text = await response.text()

  if (!text) {
    return undefined as T
  }

  return JSON.parse(text) as T
}

export async function getHealth() {
  return apiRequest('/health')
}

export async function apiUpload<T>(
  path: string,
  formData: FormData,
  options: Omit<RequestInit, 'body'> = {},
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    let message = `API upload failed: ${response.status}`
    let suggestion: string | undefined
    let errorKind: string | undefined

    try {
      const payload = (await response.json()) as { detail?: unknown }
      if (typeof payload.detail === 'string') {
        message = payload.detail
      } else if (payload.detail && typeof payload.detail === 'object') {
        const d = payload.detail as Record<string, unknown>
        if (typeof d.detail === 'string') message = d.detail
        if (typeof d.suggestion === 'string') suggestion = d.suggestion
        if (typeof d.error_kind === 'string') errorKind = d.error_kind
      }
    } catch {
      // Keep the status-based message when the API does not return JSON.
    }

    throw new ApiError(message, response.status, suggestion, errorKind)
  }

  const text = await response.text()

  if (!text) {
    return undefined as T
  }

  return JSON.parse(text) as T
}
