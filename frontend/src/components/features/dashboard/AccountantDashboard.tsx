'use client'

import { useEffect, useState } from 'react'
import { getAccountantSummary, getApprovals } from '@/temp/school-data'
import type { AccountantSummary, ApprovalItem } from '@/types'
import { Badge, Card, PageHeader, Button, Spinner } from '@/components/ui'
import { useToast } from '@/components/ui/toast'
import Icon from '@/components/ui/Icon'

// Tab D.8 — Accountant Dashboard (green)
export default function AccountantDashboard() {
  const toast = useToast()
  const [summary, setSummary] = useState<AccountantSummary | null>(null)
  const [approvals, setApprovals] = useState<ApprovalItem[]>([])

  useEffect(() => {
    void Promise.all([getAccountantSummary(), getApprovals()]).then(([s, a]) => {
      setSummary(s)
      setApprovals(a.filter((x) => x.kind === 'Fee waiver'))
    })
  }, [])

  if (!summary) return <Spinner />

  const cards = [
    { icon: 'wallet' as const, label: 'Collected Today', value: summary.collectedToday },
    { icon: 'trending' as const, label: 'Collected (Month)', value: summary.collectedMonth },
    { icon: 'warning' as const, label: 'Pending Dues', value: String(summary.pendingDues) },
    { icon: 'money' as const, label: 'Payroll Run', value: summary.payrollRun },
  ]

  return (
    <div className="page">
      <PageHeader title="Finance Overview" subtitle="Accountant dashboard" />

      <div className="kpi-grid">
        {cards.map((c) => (
          <div key={c.label} className="stat">
            <span className="stat-ico"><Icon name={c.icon} size={20} /></span>
            <div className="stat-value">{c.value}</div>
            <div className="stat-label">{c.label}</div>
          </div>
        ))}
      </div>

      <div className="dash-grid" style={{ marginTop: '1rem' }}>
        <Card title="Pending Fee Waiver Approvals" className="dash-span-2">
          {approvals.length === 0 ? (
            <p style={{ color: 'var(--muted)' }}>No pending fee waivers.</p>
          ) : (
            <ul className="feed">
              {approvals.map((a) => (
                <li key={a.id} className="feed-item">
                  <div className="feed-body">
                    <span className="feed-title">{a.summary}</span>
                    <span className="feed-sub">{a.requester} · {a.time}</span>
                  </div>
                  <Button size="sm" variant="success" onClick={() => { setApprovals((p) => p.filter((x) => x.id !== a.id)); toast.push('success', 'Waiver approved') }}>Approve</Button>
                  <Button size="sm" variant="ghost" onClick={() => { setApprovals((p) => p.filter((x) => x.id !== a.id)); toast.push('info', 'Waiver declined') }}>Decline</Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}