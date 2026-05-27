export const API_BASE_URL = import.meta.env.VITE_CLOUD_ADMIN_API_BASE_URL ?? ''

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })

  if (response.status === 401) {
    // Redirect to login on auth failure
    sessionStorage.removeItem('zs_admin_logged_in')
    window.location.href = '/login'
    throw new ApiError('未授权，请重新登录。', 401)
  }

  if (!response.ok) {
    let message = `请求失败 (${response.status})`
    try {
      const payload = (await response.json()) as { detail?: unknown }
      if (typeof payload.detail === 'string') message = payload.detail
    } catch {
      /* keep default */
    }
    throw new ApiError(message, response.status)
  }

  const text = await response.text()
  if (!text) return undefined as T
  return JSON.parse(text) as T
}
