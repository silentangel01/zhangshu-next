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

const ADMIN_WRITE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
  }

  // Add CSRF custom header for admin write requests
  const method = (options.method ?? 'GET').toUpperCase()
  if (path.startsWith('/api/admin') && ADMIN_WRITE_METHODS.has(method)) {
    headers.set('X-Zhangshu-Admin-Request', '1')
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

  if (response.status === 403) {
    // Permission denied — do NOT redirect to login
    let message = '权限不足或请求来源未通过安全校验。'
    try {
      const payload = (await response.json()) as { detail?: unknown }
      if (typeof payload.detail === 'string') message = payload.detail
    } catch {
      /* keep default */
    }
    throw new ApiError(message, 403)
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
