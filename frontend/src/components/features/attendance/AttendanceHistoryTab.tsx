'use client'

import type { AttendanceRecord } from '@/types'
import { Badge, Table, type Column } from '@/components/ui'

// Read-only attendance history table.
export default function AttendanceHistoryTab({ rows }: { rows: AttendanceRecord[] }) {
  const columns: Column<AttendanceRecord>[] = [
    { key: 'date', header: 'Date' },
    { key: 'studentName', header: 'Student', render: (r) => <strong>{r.studentName}</strong> },
    { key: 'className', header: 'Class' },
    {
      key: 'status',
      header: 'Status',
      render: (r) => (
        <Badge tone={r.status === 'Present' ? 'green' : r.status === 'Absent' ? 'red' : r.status === 'Late' ? 'amber' : 'violet'}>
          {r.status}
        </Badge>
      ),
    },
  ]

  return <Table columns={columns} rows={rows} rowKey={(r) => r.id} empty="No attendance records yet." />
}