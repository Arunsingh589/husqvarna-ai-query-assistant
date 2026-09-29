import { SparkleIcon } from '../icons'
import styles from './AppHeader.module.css'

export function AppHeader() {
  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <span className={styles.logo}>
          <SparkleIcon width={16} height={16} />
        </span>
        <span className={styles.title}>AI Query Assistant</span>
      </div>
    </header>
  )
}
