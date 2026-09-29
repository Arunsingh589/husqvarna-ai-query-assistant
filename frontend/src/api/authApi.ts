import { request } from './httpClient'
import type { TokenResponse } from './types'

const EXPIRY_BUFFER_MS = 30_000

let cached: { token: string; expiresAt: number } | null = null
let pending: Promise<string> | null = null

export function getAccessToken(): Promise<string> {
  if (cached && cached.expiresAt > Date.now()) return Promise.resolve(cached.token)

  pending ??= request<TokenResponse>('/api/auth/token', {
    method: 'POST',
    body: { subject: 'web-user' },
    timeoutMs: 10_000,
  })
    .then(({ access_token, expires_in }) => {
      cached = { token: access_token, expiresAt: Date.now() + expires_in * 1000 - EXPIRY_BUFFER_MS }
      return access_token
    })
    .finally(() => {
      pending = null
    })

  return pending
}

export function clearAccessToken(): void {
  cached = null
}
