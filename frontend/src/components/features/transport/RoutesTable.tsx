'use client'
import { Table, Badge } from '@/components/ui'
import type { TransportRoute } from '@/types'

export default function RoutesTable({ rows }: { rows: TransportRoute[] }) {
  const columns = [
    { key: 'name', header: 'Route' },
    { key: 'busId', header: 'Bus' },
    { key: 'driver', header: 'Driver' },
    { key: 'stops', header: 'Stops' },
    { key: 'students', header: 'Students' },
    { key: 'status', header: 'Status', render: (r: TransportRoute) => <Badge tone={r.status === 'Active' ? 'green' : 'muted'}>{r.status}</Badge> },
  ]
  return (
    <Table
      columns={columns}
      rows={rows}
      rowKey={(r) => r.id}
      empty="No transport routes configured."
    />
  )
}