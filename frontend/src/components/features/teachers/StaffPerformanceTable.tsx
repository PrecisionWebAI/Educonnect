'use client'
import { Table, Badge } from '@/components/ui'
import type { StaffPerfRows } from './useStaff'

export default function StaffPerformanceTable({ rows }: { rows: StaffPerfRows }) {
  const trendTone: Record<string, 'green' | 'muted' | 'amber'> = { up: 'green', flat: 'muted', down: 'amber' }
  const columns = [
    { key: 'staff', header: 'Teacher' },
    {
      key: 'rating',
      header: 'Rating',
      render: (r: (typeof rows)[0]) => (
        <span>
          {r.rating} <span style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>/ 5</span>
        </span>
      ),
    },
    { key: 'reviews', header: 'Reviews' },
    {
      key: 'score',
      header: 'Score',
      render: (r: (typeof rows)[0]) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <div className="cls-bar" style={{ flex: 1, height: 8, maxWidth: 110 }}>
            <div className="bar-fill" style={{ width: `${r.score}%` }} />
          </div>
          <span style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>{r.score}</span>
        </div>
      ),
    },
    {
      key: 'trend',
      header: 'Trend',
      render: (r: (typeof rows)[0]) => <Badge tone={trendTone[r.trend]}>{r.trend}</Badge>,
    },
  ]

  return (
    <Table
      columns={columns}
      rows={rows}
      rowKey={(r) => r.id}
      empty="No performance records."
    />
  )
}