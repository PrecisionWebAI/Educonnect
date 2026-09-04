'use client'
import { Table, Badge } from '@/components/ui'
import type { Bus } from '@/types'

export default function BusesTable({ rows }: { rows: Bus[] }) {
  const tone: Record<Bus['status'], 'green' | 'muted' | 'amber'> = {
    'En route': 'green',
    Parked: 'muted',
    Service: 'amber',
  }
  const columns = [
    { key: 'name', header: 'Bus' },
    { key: 'plate', header: 'Plate No.' },
    { key: 'route', header: 'Route' },
    {
      key: 'occupancy',
      header: 'Occupancy',
      render: (r: Bus) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', minWidth: 130 }}>
          <div className="cls-bar" style={{ flex: 1, height: 8, maxWidth: 100 }}>
            <div className="bar-fill" style={{ width: `${Math.round((r.occupied / r.capacity) * 100)}%` }} />
          </div>
          <span style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>{r.occupied}/{r.capacity}</span>
        </div>
      ),
    },
    { key: 'status', header: 'Status', render: (r: Bus) => <Badge tone={tone[r.status]}>{r.status}</Badge> },
  ]
  return (
    <Table
      columns={columns}
      rows={rows}
      rowKey={(r) => r.id}
      empty="No buses available."
    />
  )
}