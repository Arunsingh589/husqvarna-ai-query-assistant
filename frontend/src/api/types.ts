export interface TokenUsage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

export interface QueryResponse {
  answer: string
  model: string
  truncated: boolean
  usage: TokenUsage | null
  request_id: string
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_in: number
}

export interface ApiErrorBody {
  error: {
    code: string
    message: string
    request_id: string | null
  }
}
