'use client'
import { useCallback, useEffect, useState, type ReactNode } from 'react'
import type { Session, User } from '../types'
import { mockLogin, mockLogout } from '@/lib/api/mock'
import { AuthContext, STORAGE_KEY, type AuthContextValue } from './auth-context'

// ============================================================
// AuthProvider — holds the current session. UI-first build: it
// calls the mock layer. When the backend is ready, swap the
// mockLogin/mockLogout imports for the real client.ts calls
// (one-line change at the top of this file).
// ============================================================

function readStoredSession(): Session | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as Session) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(() => readStoredSession())

  useEffect(() => {
    if (session) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
    } else {
      localStorage.removeItem(STORAGE_KEY)
    }
  }, [session])

  const login = useCallback(async (identifier: string, password: string): Promise<User> => {
    const s = await mockLogin(identifier, password)
    setSession(s)
    return s.user
  }, [])

  const logout = useCallback(async () => {
    if (session) {
      try {
        await mockLogout(session.refreshToken)
      } catch {
        /* best effort */
      }
    }
    setSession(null)
  }, [session])

  const setUser = useCallback((user: User) => {
    setSession((prev) => (prev ? { ...prev, user } : prev))
  }, [])

  const value: AuthContextValue = {
    session,
    user: session?.user ?? null,
    isAuthed: session !== null,
    login,
    logout,
    setUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
