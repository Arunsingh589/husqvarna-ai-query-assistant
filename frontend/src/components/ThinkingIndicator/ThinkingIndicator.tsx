import { Avatar } from '../Avatar/Avatar'
import styles from './ThinkingIndicator.module.css'

export function ThinkingIndicator() {
  return (
    <div className={styles.row} role="status">
      <span className={styles.avatar}>
        <Avatar variant="assistant" />
      </span>
      <span className={styles.label}>Thinking</span>
      <span className={styles.dots} aria-hidden="true">
        <span />
        <span />
        <span />
      </span>
    </div>
  )
}
