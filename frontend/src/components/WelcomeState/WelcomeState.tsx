import { SparkleIcon } from '../icons'
import styles from './WelcomeState.module.css'

export function WelcomeState() {
  return (
    <section className={styles.welcome}>
      <span className={styles.icon}>
        <SparkleIcon width={40} height={40} />
      </span>
      <h1 className={styles.title}>What would you like to know?</h1>
      <p className={styles.subtitle}>
        Type your question below and the assistant will answer it for you.
      </p>
    </section>
  )
}
