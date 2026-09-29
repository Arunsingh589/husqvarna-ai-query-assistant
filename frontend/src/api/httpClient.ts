import { config } from '../config'
import { ApiError } from './ApiError'
import type { ApiErrorBody } from './types'

interface RequestOptions {
  method?: 'GET' | 'POST'
  body?: unknown
  token?: string
  signal?: AbortSignal
  timeoutMs?: number
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, token, signal, timeoutMs = config.requestTimeoutMs } = options

  const timeoutSignal = AbortSignal.timeout(timeoutMs)
  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`

  let response: Response
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: signal ? AbortSignal.any([signal, timeoutSignal]) : timeoutSignal,
    })
  } catch (error) {
    if (timeoutSignal.aborted) {
      throw new ApiError('The request timed out. Please try again.', { code: 'CLIENT_TIMEOUT' })
    }
    if (signal?.aborted) throw error
    throw new ApiError('Unable to reach the server. Check your connection and try again.', {
      code: 'NETWORK_ERROR',
    })
  }

  if (!response.ok) throw await toApiError(response)

  return (await response.json()) as T
}

async function toApiError(response: Response): Promise<ApiError> {
  const retryAfter = Number(response.headers.get('Retry-After'))
  const base = {
    status: response.status,
    requestId: response.headers.get('X-Request-ID'),
    retryAfterSeconds: Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : null,
  }

  try {
    const { error } = (await response.json()) as ApiErrorBody
    return new ApiError(error.message, { ...base, code: error.code, requestId: error.request_id })
  } catch {
    if (response.status >= 502 && response.status <= 504) {
      return new ApiError('The server is not reachable right now. Please try again shortly.', {
        ...base,
        code: 'SERVER_UNREACHABLE',
      })
    }
    return new ApiError('Something went wrong. Please try again.', {
      ...base,
      code: 'UNKNOWN_ERROR',
    })
  }
}
