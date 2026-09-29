export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
  requestTimeoutMs: 65_000,
  maxQueryLength: 4000,
  splashMinDurationMs: 1400,
} as const
