import { describe, expect, it } from 'vitest'

import { ApiError, formatApiErrorMessage, parseApiErrorPayload } from '@/shared/api/client'

describe('parseApiErrorPayload', () => {
  const fallback = 'API request failed: 400'

  it('extracts message from structured detail object', () => {
    const payload = {
      detail: {
        message: '邮箱已被注册',
        error_kind: 'http_status_error',
        suggestion: '请使用其他邮箱或尝试登录。',
      },
    }
    const result = parseApiErrorPayload(payload, fallback)
    expect(result.message).toBe('邮箱已被注册')
    expect(result.errorKind).toBe('http_status_error')
    expect(result.suggestion).toBe('请使用其他邮箱或尝试登录。')
  })

  it('extracts plain string detail', () => {
    const payload = { detail: '请求参数无效' }
    const result = parseApiErrorPayload(payload, fallback)
    expect(result.message).toBe('请求参数无效')
    expect(result.suggestion).toBeUndefined()
    expect(result.errorKind).toBeUndefined()
  })

  it('preserves suggestion and error_kind from structured detail', () => {
    const payload = {
      detail: {
        message: '连接被重置',
        error_kind: 'tls_reset_or_sni_filtered',
        suggestion: '可尝试兼容模式。',
      },
    }
    const result = parseApiErrorPayload(payload, fallback)
    expect(result.message).toBe('连接被重置')
    expect(result.errorKind).toBe('tls_reset_or_sni_filtered')
    expect(result.suggestion).toBe('可尝试兼容模式。')
  })

  it('falls back to top-level message when detail is missing', () => {
    const payload = { message: '服务器内部错误' }
    const result = parseApiErrorPayload(payload, fallback)
    expect(result.message).toBe('服务器内部错误')
  })

  it('falls back to top-level error when detail and message are missing', () => {
    const payload = { error: '未经授权' }
    const result = parseApiErrorPayload(payload, fallback)
    expect(result.message).toBe('未经授权')
  })

  it('returns fallback when payload is null', () => {
    const result = parseApiErrorPayload(null, fallback)
    expect(result.message).toBe(fallback)
    expect(result.suggestion).toBeUndefined()
    expect(result.errorKind).toBeUndefined()
  })

  it('returns fallback when payload is not an object', () => {
    const result = parseApiErrorPayload('some string', fallback)
    expect(result.message).toBe(fallback)
  })

  it('returns fallback when JSON body has no recognized keys', () => {
    const payload = { foo: 'bar', count: 42 }
    const result = parseApiErrorPayload(payload, fallback)
    expect(result.message).toBe(fallback)
  })

  it('handles nested detail.detail edge case', () => {
    const payload = { detail: { detail: '嵌套错误信息' } }
    const result = parseApiErrorPayload(payload, fallback)
    expect(result.message).toBe('嵌套错误信息')
  })

  it('handles structured detail without suggestion or error_kind', () => {
    const payload = { detail: { message: '密码太短' } }
    const result = parseApiErrorPayload(payload, fallback)
    expect(result.message).toBe('密码太短')
    expect(result.suggestion).toBeUndefined()
    expect(result.errorKind).toBeUndefined()
  })

  it('prefers detail.message over top-level message', () => {
    const payload = {
      detail: { message: '详细错误' },
      message: '泛化错误',
    }
    const result = parseApiErrorPayload(payload, fallback)
    expect(result.message).toBe('详细错误')
  })

  it('supports camelCase errorKind alongside snake_case error_kind', () => {
    const payload = {
      detail: { message: 'test', errorKind: 'timeout' },
    }
    const result = parseApiErrorPayload(payload, fallback)
    expect(result.errorKind).toBe('timeout')
  })

  it('ignores array detail', () => {
    const payload = { detail: ['error1', 'error2'] }
    const result = parseApiErrorPayload(payload, fallback)
    // Array detail is not a recognized format, falls through
    expect(result.message).toBe(fallback)
  })
})

describe('formatApiErrorMessage', () => {
  const fallback = '操作失败，请稍后重试。'

  it('returns ApiError message', () => {
    const error = new ApiError('云端连接失败', 503)
    expect(formatApiErrorMessage(error, fallback)).toBe('云端连接失败')
  })

  it('appends suggestion when present', () => {
    const error = new ApiError('连接被重置', 503, '请切换兼容模式。')
    const result = formatApiErrorMessage(error, fallback)
    expect(result).toContain('连接被重置')
    expect(result).toContain('请切换兼容模式。')
  })

  it('returns plain Error message', () => {
    const error = new Error('普通错误')
    expect(formatApiErrorMessage(error, fallback)).toBe('普通错误')
  })

  it('returns fallback for non-Error values', () => {
    expect(formatApiErrorMessage('some string', fallback)).toBe(fallback)
    expect(formatApiErrorMessage(42, fallback)).toBe(fallback)
    expect(formatApiErrorMessage(null, fallback)).toBe(fallback)
    expect(formatApiErrorMessage(undefined, fallback)).toBe(fallback)
  })

  it('returns fallback when ApiError has empty message', () => {
    const error = new ApiError('', 500)
    expect(formatApiErrorMessage(error, fallback)).toBe(fallback)
  })
})
