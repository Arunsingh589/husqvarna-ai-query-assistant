import { useCallback, useEffect, useRef, useState } from 'react'
import { ApiError } from '../api/ApiError'
import { askQuestion } from '../api/queryApi'
import type { QueryResponse } from '../api/types'

export type QueryResult = { id: number; query: string } & (
  | { status: 'loading' }
  | { status: 'success'; response: QueryResponse }
  | { status: 'error'; error: ApiError }
)

export function useAskQuestion() {
  const [result, setResult] = useState<QueryResult | null>(null)
  const controllerRef = useRef<AbortController | null>(null)
  const nextIdRef = useRef(1)

  useEffect(() => () => controllerRef.current?.abort(), [])

  const ask = useCallback(async (query: string) => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    const id = nextIdRef.current++

    setResult({ id, query, status: 'loading' })
    try {
      const response = await askQuestion(query, controller.signal)
      setResult({ id, query, status: 'success', response })
    } catch (error) {
      if (controller.signal.aborted) return
      setResult({ id, query, status: 'error', error: toApiError(error) })
    }
  }, [])

  return { result, isBusy: result?.status === 'loading', ask }
}

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error
  return new ApiError('Something went wrong. Please try again.', { code: 'UNKNOWN_ERROR' })
}
