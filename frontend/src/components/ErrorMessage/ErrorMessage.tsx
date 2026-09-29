import type { ApiError } from '../../api/ApiError'
import { AlertIcon, RetryIcon } from '../icons'
import styles from './ErrorMessage.module.css'

interface ErrorMessageProps {
  error: ApiError
  onRetry: () => void
}

export function ErrorMessage({ error, onRetry }: ErrorMessageProps) {
  const waitHint = error.retryAfterSeconds
    ? ` You can try again in ${error.retryAfterSeconds} seconds.`
    : ''

  return (
    <div className={styles.alert} role="alert">
      <AlertIcon className={styles.icon} />
      <div className={styles.body}>
        <p className={styles.message}>
          {error.message}
          {waitHint}
        </p>
        {error.requestId && <p className={styles.reference}>Reference: {error.requestId}</p>}
      </div>
      {error.isRetryable && (
        <button type="button" className={styles.retry} onClick={onRetry}>
          <RetryIcon width={16} height={16} />
          Retry
        </button>
      )}
    </div>
  )
}
