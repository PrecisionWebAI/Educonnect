'use client'
import {
  useEffect,
  type ButtonHTMLAttributes,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react'

// ============================================================
// EduConnect UI kit — small, dependency-free primitives built on
// the dark design tokens in index.css. Plain CSS in styles/ui.css.
// ============================================================

/* ---------- Button ---------- */

type ButtonVariant = 'primary' | 'outline' | 'ghost' | 'danger' | 'success'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: 'sm' | 'md'
  icon?: string
  loading?: boolean
}

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  loading,
  children,
  className = '',
  disabled,
  ...rest
}: ButtonProps) {
  const cls = ['btn', `btn-${variant}`, size === 'sm' ? 'btn-sm' : '', className]
    .filter(Boolean)
    .join(' ')
  return (
    <button className={cls} disabled={disabled || loading} {...rest}>
      {loading ? <span className="spinner-btn" /> : icon ? <span className="btn-ico">{icon}</span> : null}
      {children}
    </button>
  )
}

/* ---------- Badge ---------- */
export type BadgeTone = 'accent' | 'green' | 'red' | 'amber' | 'muted' | 'teal' | 'violet'

export function Badge({ tone = 'accent', children }: { tone?: BadgeTone; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}

/* ---------- Card ---------- */
export function Card({
  title,
  action,
  children,
  className = '',
}: {
  title?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={`card ${className}`}>
      {title !== undefined && (
        <header className="card-head">
          <h3>{title}</h3>
          {action}
        </header>
      )}
      <div className="card-body">{children}</div>
    </section>
  )
}

/* ---------- StatCard ---------- */
export function StatCard({ icon, label, value, delta, hint }: {
  icon?: ReactNode
  label: string
  value: string
  delta: number
  hint?: string
}) {
  const up = delta >= 0
  return (
    <div className="stat">
      <div className="stat-top">
        {icon && <span className="stat-ico">{icon}</span>}
        <Badge tone={up ? 'green' : 'red'}>
          {up ? '▲' : '▼'} {Math.abs(delta).toFixed(1)}%
        </Badge>
      </div>
      <div className="stat-value">{value}</div>
      <div className="stat-label">{label}</div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  )
}

/* ---------- Inputs ---------- */
interface FieldProps {
  label?: string
  hint?: string
  error?: string
}

export function Input({ label, hint, error, id, ...rest }: FieldProps & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <div className="field">
      {label && <label htmlFor={id}>{label}</label>}
      <input id={id} className={error ? 'input input-err' : 'input'} {...rest} />
      {error ? <span className="field-err">{error}</span> : hint ? <span className="field-hint">{hint}</span> : null}
    </div>
  )
}

export function Select({ label, hint, id, children, ...rest }: FieldProps & SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <div className="field">
      {label && <label htmlFor={id}>{label}</label>}
      <select id={id} className="input" {...rest}>
        {children}
      </select>
      {hint && <span className="field-hint">{hint}</span>}
    </div>
  )
}

export function Textarea({ label, hint, id, ...rest }: FieldProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <div className="field">
      {label && <label htmlFor={id}>{label}</label>}
      <textarea id={id} className="input" {...rest} />
      {hint && <span className="field-hint">{hint}</span>}
    </div>
  )
}

/* ---------- PageHeader ---------- */
export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: ReactNode }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  )
}

/* ---------- Table ---------- */
export interface Column<T> {
  key: string
  header: string
  render?: (row: T) => ReactNode
  align?: 'left' | 'right'
}

export function Table<T>({ columns, rows, rowKey, empty }: {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => React.Key
  empty?: string
}) {
  if (rows.length === 0) {
    return <div className="empty-state">{empty ?? 'No records yet.'}</div>
  }
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} className={c.align === 'right' ? 'right' : ''}>{c.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={rowKey(r)}>
              {columns.map((c) => (
                <td key={c.key} className={c.align === 'right' ? 'right' : ''}>
                  {c.render ? c.render(r) : String((r as Record<string, unknown>)[c.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ---------- Tabs ---------- */
export function Tabs({ tabs, active, onChange }: { tabs: string[]; active: string; onChange: (tab: string) => void }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button key={t} role="tab" aria-selected={t === active} className={t === active ? 'tab tab-active' : 'tab'} onClick={() => onChange(t)}>
          {t}
        </button>
      ))}
    </div>
  )
}

/* ---------- Modal ---------- */
export function Modal({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="overlay" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <header className="modal-head">
          <h3>{title}</h3>
          <button className="btn-ghost-link" onClick={onClose} aria-label="Close">✕</button>
        </header>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}

/* ---------- Spinner ---------- */
export function Spinner() {
  return (
    <div className="spinner-wrap" aria-label="Loading">
      <span className="spinner" />
    </div>
  )
}

/* ---------- Empty state ---------- */
export function EmptyState({ icon = '🗂️', title, body }: { icon?: string; title: string; body?: string }) {
  return (
    <div className="empty-state empty-state-lg">
      <div className="empty-ico">{icon}</div>
      <h3>{title}</h3>
      {body && <p>{body}</p>}
    </div>
  )
}
