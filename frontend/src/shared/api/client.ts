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

/**
 * Parse a FastAPI error payload into a user-readable message, suggestion, and
 * error kind.
 *
 * FastAPI wraps error details under the `detail` key. When the backend uses
 * `_build_error_detail()` with structured fields, `detail` is an object like:
 *   { "message": "...", "error_kind": "...", "suggestion": "..." }
 *
 * When it's a plain string error, `detail` is just a string.
 *
 * Priority for message extraction:
 * 1. `detail.message`  (structured backend error)
 * 2. `detail.detail`   (nested detail — rare edge case)
 * 3. `payload.message` (non-FastAPI error body)
 * 4. `payload.error`   (alternative error key)
 * 5. fallback          (`API request failed: <status>`)
 */
export function parseApiErrorPayload(
  payload: unknown,
  fallbackMessage: string,
): { message: string; suggestion?: string; errorKind?: string } {
  let message = fallbackMessage
  let suggestion: string | undefined
  let errorKind: string | undefined

  if (payload && typeof payload === 'object') {
    const p = payload as Record<string, unknown>
    const detail = p.detail

    if (typeof detail === 'string') {
      // Plain string error: {"detail": "some error message"}
      message = detail
    } else if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      const d = detail as Record<string, unknown>
      // Structured error: {"detail": {"message": "...", "error_kind": "...", "suggestion": "..."}}
      if (typeof d.message === 'string') message = d.message
      else if (typeof d.detail === 'string') message = d.detail
      if (typeof d.suggestion === 'string') suggestion = d.suggestion
      if (typeof d.error_kind === 'string') errorKind = d.error_kind
      else if (typeof d.errorKind === 'string') errorKind = d.errorKind
    }

    // Fallback to top-level message/error if detail didn't provide one
    if (message === fallbackMessage) {
      if (typeof p.message === 'string') message = p.message
      else if (typeof p.error === 'string') message = p.error
    }
  }

  return { message, suggestion, errorKind }
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
    const fallbackMessage = `API request failed: ${response.status}`
    let message = fallbackMessage
    let suggestion: string | undefined
    let errorKind: string | undefined

    try {
      const payload = await response.json()
      const parsed = parseApiErrorPayload(payload, fallbackMessage)
      message = parsed.message
      suggestion = parsed.suggestion
      errorKind = parsed.errorKind
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
    const fallbackMessage = `API upload failed: ${response.status}`
    let message = fallbackMessage
    let suggestion: string | undefined
    let errorKind: string | undefined

    try {
      const payload = await response.json()
      const parsed = parseApiErrorPayload(payload, fallbackMessage)
      message = parsed.message
      suggestion = parsed.suggestion
      errorKind = parsed.errorKind
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
