import type { TransitionEvent } from 'react'
import { cx } from '../../utils/cx'
import { SparkleIcon } from '../icons'
import styles from './SplashScreen.module.css'

interface SplashScreenProps {
  isLeaving: boolean
  onExited: () => void
}

export function SplashScreen({ isLeaving, onExited }: SplashScreenProps) {
  const handleTransitionEnd = (event: TransitionEvent<HTMLDivElement>) => {
    if (isLeaving && event.target === event.currentTarget) onExited()
  }

  return (
    <div
      className={cx(styles.splash, isLeaving && styles.leaving)}
      onTransitionEnd={handleTransitionEnd}
      role="status"
      aria-label="Loading AI Query Assistant"
    >
      <div className={styles.logo}>
        <SparkleIcon width={36} height={36} />
      </div>
      <p className={styles.title}>AI Query Assistant</p>
      <div className={styles.progress} aria-hidden="true">
        <span />
      </div>
    </div>
  )
}
