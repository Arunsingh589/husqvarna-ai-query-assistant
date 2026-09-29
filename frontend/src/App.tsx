import { useEffect, useState } from 'react'
import { getAccessToken } from './api/authApi'
import styles from './App.module.css'
import { AppHeader } from './components/AppHeader/AppHeader'
import { QueryForm } from './components/QueryForm/QueryForm'
import { QueryResult } from './components/QueryResult/QueryResult'
import { SplashScreen } from './components/SplashScreen/SplashScreen'
import { WelcomeState } from './components/WelcomeState/WelcomeState'
import { config } from './config'
import { useAskQuestion } from './hooks/useAskQuestion'
import { delay } from './utils/delay'

type SplashPhase = 'visible' | 'leaving' | 'done'

export default function App() {
  const [splash, setSplash] = useState<SplashPhase>('visible')
  const { result, isBusy, ask } = useAskQuestion()

  useEffect(() => {
    const warmUp = getAccessToken().catch(() => undefined)
    Promise.all([warmUp, delay(config.splashMinDurationMs)]).then(() => setSplash('leaving'))
  }, [])

  return (
    <>
      {splash !== 'done' && (
        <SplashScreen isLeaving={splash === 'leaving'} onExited={() => setSplash('done')} />
      )}

      <div className={styles.layout}>
        <AppHeader />
        <main className={styles.main}>
          {result ? (
            <QueryResult key={result.id} result={result} onRetry={() => ask(result.query)} />
          ) : (
            <WelcomeState />
          )}
        </main>
        <div className={styles.composer}>
          <QueryForm onSubmit={ask} isBusy={isBusy} />
          <p className={styles.disclaimer}>AI-generated answers can be inaccurate.</p>
        </div>
      </div>
    </>
  )
}
