import { useState, useEffect } from 'react'

/**
 * Non-intrusive notification banner for Render free-tier backend cold starts.
 * Displays a friendly message when the backend is waking up from sleep mode
 * instead of alarming the user with an immediate red error banner.
 */
export default function BackendHealthNotice() {
  const [wakingUp, setWakingUp] = useState(false)
  const [attempt, setAttempt] = useState(1)

  useEffect(() => {
    const handleWakingUp = (e) => {
      setWakingUp(true)
      if (e.detail?.attempt) {
        setAttempt(e.detail.attempt)
      }
    }

    window.addEventListener('backend-waking-up', handleWakingUp)
    return () => window.removeEventListener('backend-waking-up', handleWakingUp)
  }, [])

  if (!wakingUp) return null

  return (
    <div className="bg-amber-50 border-b border-amber-200 text-amber-900 px-4 py-2.5 text-xs font-medium flex items-center justify-between transition-all duration-300">
      <div className="flex items-center gap-2 max-w-4xl mx-auto w-full justify-center">
        <span className="inline-block w-2 h-2 rounded-full bg-amber-500 animate-ping" />
        <span>
          Backend server is spinning up from free-tier sleep (attempt {attempt}/3). Please wait a moment...
        </span>
      </div>
      <button
        onClick={() => setWakingUp(false)}
        className="text-amber-700 hover:text-amber-900 text-xs font-semibold px-2 py-0.5 rounded"
      >
        Dismiss
      </button>
    </div>
  )
}
