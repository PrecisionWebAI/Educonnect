'use client'

import { useEffect, useState, type FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/providers/auth-context'
import { Button } from '@/components/ui'

// ============================================================
// PAGE 03 — Login (Next.js port). Mock auth via AuthProvider;
// quick demo role chips for UI-first development.
// ============================================================

const DEMO_ACCOUNTS = [
  { label: 'Director', identifier: 'director', icon: '🏛️' },
  { label: 'Principal', identifier: 'principal', icon: '👔' },
  { label: 'HOD', identifier: 'hod', icon: '🧪' },
  { label: 'Class Teacher', identifier: 'ct', icon: '👩‍🏫' },
  { label: 'Student', identifier: 'student', icon: '🎓' },
  { label: 'Parent', identifier: 'parent', icon: '👨‍👩‍👧' },
]

export default function AuthPage() {
  const { isAuthed, login } = useAuth()
  const router = useRouter()
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(id: string, pwd: string) {
    setError('')
    setIsSubmitting(true)
    try {
      await login(id, pwd)
      router.replace('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    void submit(identifier.trim(), password)
  }

  useEffect(() => {
    if (isAuthed) router.replace('/dashboard')
  }, [isAuthed, router])

  return (
    <div className="section auth-wrap">
      <div className="auth-card">
        <div className="auth-tabs">
          <button type="button" className={tab === 'login' ? 'active' : ''} onClick={() => setTab('login')}>
            Log in
          </button>
          <button type="button" className={tab === 'register' ? 'active' : ''} onClick={() => setTab('register')}>
            Register
          </button>
        </div>

        {tab === 'register' ? (
          <p className="auth-note">🚧 Registration is coming soon — accounts are created by the school admin.</p>
        ) : (
          <>
            {error !== '' && <p className="auth-error">{error}</p>}
            <form onSubmit={handleSubmit}>
              <div className="field">
                <label htmlFor="identifier">Email or username</label>
                <input
                  id="identifier"
                  type="text"
                  placeholder="you@school.edu"
                  value={identifier}
                  onChange={(e) => setIdentifier(e.target.value)}
                  required
                  disabled={isSubmitting}
                />
              </div>
              <div className="field">
                <label htmlFor="password">Password</label>
                <input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={isSubmitting}
                />
              </div>
              <Button type="submit" loading={isSubmitting} style={{ width: '100%' }}>
                {isSubmitting ? 'Logging in…' : 'Log in'}
              </Button>
            </form>

            <div className="demo-block">
              <p className="auth-hint">🎁 Quick demo — pick a role (no password needed)</p>
              <div className="demo-grid">
                {DEMO_ACCOUNTS.map((d) => (
                  <button key={d.identifier} type="button" className="demo-chip" disabled={isSubmitting} onClick={() => void submit(d.identifier, '11111')}>
                    <span>{d.icon}</span> {d.label}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
