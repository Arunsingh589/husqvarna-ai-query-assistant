import { ApiError } from './ApiError'
import { clearAccessToken, getAccessToken } from './authApi'
import { request } from './httpClient'
import type { QueryResponse } from './types'

export async function askQuestion(query: string, signal?: AbortSignal): Promise<QueryResponse> {
  const send = async () =>
    request<QueryResponse>('/api/query', {
      method: 'POST',
      body: { query },
      token: await getAccessToken(),
      signal,
    })

  try {
    return await send()
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      clearAccessToken()
      return send()
    }
    throw error
  }
}
