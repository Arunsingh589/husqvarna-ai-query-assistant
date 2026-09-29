import { cx } from '../../utils/cx'
import { SparkleIcon, UserIcon } from '../icons'
import styles from './Avatar.module.css'

export function Avatar({ variant }: { variant: 'user' | 'assistant' }) {
  return (
    <span className={cx(styles.avatar, styles[variant])} aria-hidden="true">
      {variant === 'user' ? (
        <UserIcon width={15} height={15} />
      ) : (
        <SparkleIcon width={15} height={15} />
      )}
    </span>
  )
}
