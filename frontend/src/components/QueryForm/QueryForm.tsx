import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { config } from '../../config'
import { cx } from '../../utils/cx'
import { SendIcon } from '../icons'
import styles from './QueryForm.module.css'

interface QueryFormProps {
  onSubmit: (query: string) => void
  isBusy: boolean
}

const WARNING_THRESHOLD = config.maxQueryLength * 0.9

export function QueryForm({ onSubmit, isBusy }: QueryFormProps) {
  const [value, setValue] = useState('')
  const trimmed = value.trim()
  const canSubmit = trimmed.length > 0 && !isBusy

  const submit = () => {
    if (!canSubmit) return
    onSubmit(trimmed)
    setValue('')
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    submit()
  }

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit}>
      <label htmlFor="query" className={styles.srOnly}>
        Your question
      </label>
      <textarea
        id="query"
        className={styles.input}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask anything..."
        maxLength={config.maxQueryLength}
        rows={2}
        autoFocus
      />
      <div className={styles.footer}>
        <span className={styles.hint}>
          <kbd>Enter</kbd> to send · <kbd>Shift</kbd> + <kbd>Enter</kbd> for a new line
        </span>
        <span
          className={cx(styles.counter, value.length > WARNING_THRESHOLD && styles.counterWarning)}
          aria-live="polite"
        >
          {value.length} / {config.maxQueryLength}
        </span>
        <button type="submit" className={styles.submit} disabled={!canSubmit} aria-label="Send">
          <SendIcon width={18} height={18} />
        </button>
      </div>
    </form>
  )
}
