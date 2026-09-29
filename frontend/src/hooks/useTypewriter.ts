import { useEffect, useState } from 'react'

const MIN_CHARS_PER_SECOND = 80
const MAX_DURATION_SECONDS = 10

const prefersReducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

export function useTypewriter(text: string) {
  const [visibleCount, setVisibleCount] = useState(() =>
    prefersReducedMotion() ? text.length : 0,
  )

  useEffect(() => {
    if (prefersReducedMotion()) return

    const charsPerSecond = Math.max(MIN_CHARS_PER_SECOND, text.length / MAX_DURATION_SECONDS)
    const startedAt = performance.now()
    let frameId = 0

    const tick = (now: number) => {
      const next = Math.min(text.length, Math.floor(((now - startedAt) / 1000) * charsPerSecond))
      setVisibleCount(next)
      if (next < text.length) frameId = requestAnimationFrame(tick)
    }

    frameId = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frameId)
  }, [text])

  return {
    visibleText: text.slice(0, visibleCount),
    isTyping: visibleCount < text.length,
  }
}
