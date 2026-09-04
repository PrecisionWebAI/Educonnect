'use client'
import { Table, Badge } from '@/components/ui'
import type { WorkloadMatrixRows } from './useStaff'

export default function WorkloadMatrixTable({
  rows,
}: {
  rows: WorkloadMatrixRows
}) {
  const columns = [
    { key: 'staff', header: 'Teacher' },
    { key: 'subject', header: 'Subject' },
    { key: 'classes', header: 'Classes', render: (r: (typeof rows)[0]) => r.classes.join(', ') },
    { key: 'periods', header: 'Periods / wk' },
    {
      key: 'utilisation',
      header: 'Utilisation',
      render: (r: (typeof rows)[0]) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 120 }}>
          <div className="cls-bar" style={{ flex: 1, height: 8, maxWidth: 110 }}>
            <div className="bar-fill" style={{ width: `${r.utilisation}%` }} />
          </div>
          <span style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>{r.utilisation}%</span>
        </div>
      ),
    },
  ]

  return (
    <Table
      columns={columns}
      rows={rows}
      rowKey={(r) => r.staff}
      empty="No workload data yet."
    />
  )
}