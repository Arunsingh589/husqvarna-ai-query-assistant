import Markdown, { type Components } from 'react-markdown'
import type { QueryResponse } from '../../api/types'
import { useTypewriter } from '../../hooks/useTypewriter'
import { cx } from '../../utils/cx'
import { Avatar } from '../Avatar/Avatar'
import styles from './AnswerCard.module.css'

const markdownComponents: Components = {
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
}

export function AnswerCard({ response }: { response: QueryResponse }) {
  const { visibleText, isTyping } = useTypewriter(response.answer)

  return (
    <article className={styles.answer}>
      <Avatar variant="assistant" />
      <div className={styles.content}>
        <div
          className={cx(styles.markdown, isTyping && styles.typing)}
          aria-live="polite"
          aria-busy={isTyping}
        >
          <Markdown components={markdownComponents}>{visibleText}</Markdown>
        </div>

        {!isTyping && response.truncated && (
          <p className={styles.truncated}>
            The answer was cut short because it reached the length limit.
          </p>
        )}
      </div>
    </article>
  )
}
