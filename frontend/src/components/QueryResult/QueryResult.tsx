import type { QueryResult as QueryResultState } from '../../hooks/useAskQuestion'
import { AnswerCard } from '../AnswerCard/AnswerCard'
import { Avatar } from '../Avatar/Avatar'
import { ErrorMessage } from '../ErrorMessage/ErrorMessage'
import { ThinkingIndicator } from '../ThinkingIndicator/ThinkingIndicator'
import styles from './QueryResult.module.css'

interface QueryResultProps {
  result: QueryResultState
  onRetry: () => void
}

export function QueryResult({ result, onRetry }: QueryResultProps) {
  return (
    <section className={styles.result} aria-label="Question and answer">
      <div className={styles.question}>
        <Avatar variant="user" />
        <p className={styles.questionText}>{result.query}</p>
      </div>

      {result.status === 'loading' && <ThinkingIndicator />}
      {result.status === 'success' && <AnswerCard response={result.response} />}
      {result.status === 'error' && <ErrorMessage error={result.error} onRetry={onRetry} />}
    </section>
  )
}
