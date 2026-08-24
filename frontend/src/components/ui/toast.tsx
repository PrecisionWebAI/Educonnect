'use client'
import { createContext, useCallback, useContext, useState, type ReactNode } from 'react'

// ============================================================
// Toast system — separate file so the component file satisfies
// react-refresh (only-export-components).
// ============================================================

export interface ToastMsg {
  id: number
  kind: 'success' | 'error' | 'info'
  text: string
}

interface ToastCtx {
  push: (kind: ToastMsg['kind'], text: string) => void
}

const ToastContext = createContext<ToastCtx>({ push: () => {} })

// eslint-disable-next-line react-refresh/only-export-components
export function useToast() {
  return useContext(ToastContext)
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMsg[]>([])

  const push = useCallback((kind: ToastMsg['kind'], text: string) => {
    const id = Date.now() + Math.random()
    setToasts((prev) => [...prev, { id, kind, text }])
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 3200)
  }, [])

  const remove = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  return (
    <ToastContext.Provider value={{ push }}>
      {children}
      <div className="toast-region">
        {toasts.map((t) => (
          <button key={t.id} className={`toast toast-${t.kind}`} onClick={() => remove(t.id)}>
            {t.kind === 'success' ? '✅' : t.kind === 'error' ? '⚠️' : 'ℹ️'} {t.text}
          </button>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
