const NON_RETRYABLE_CODES = new Set(['INVALID_REQUEST', 'LLM_CONTENT_BLOCKED'])

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string | null
  readonly retryAfterSeconds: number | null

  constructor(
    message: string,
    options: {
      status?: number
      code: string
      requestId?: string | null
      retryAfterSeconds?: number | null
    },
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = options.status ?? 0
    this.code = options.code
    this.requestId = options.requestId ?? null
    this.retryAfterSeconds = options.retryAfterSeconds ?? null
  }

  get isRetryable(): boolean {
    return !NON_RETRYABLE_CODES.has(this.code)
  }
}
