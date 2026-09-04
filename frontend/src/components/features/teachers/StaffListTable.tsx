'use client'
import { Table, Badge } from '@/components/ui'
import type { StaffMember } from '@/types'

export default function StaffListTable({
  rows,
}: {
  rows: StaffMember[]
}) {
  const columns = [
    { key: 'staffCode', header: 'ID', render: (r: StaffMember) => <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{r.staffCode}</span> },
    { key: 'name', header: 'Name', render: (r: StaffMember) => (
        <div className="cell-name">
          <span className="cell-avatar">{r.name.split(' ').map((n) => n[0]).join('')}</span>
          <div style={{ lineHeight: 1.2 }}>
            <div>{r.name}</div>
            <div style={{ color: 'var(--muted)', fontSize: '0.74rem' }}>{r.subject}</div>
          </div>
        </div>
      ) },
    { key: 'department', header: 'Department' },
    { key: 'classes', header: 'Classes', render: (r: StaffMember) => r.classes.join(', ') },
    { key: 'workload', header: 'Workload', render: (r: StaffMember) => <span>{r.workload} <span style={{ color: 'var(--muted)', fontSize: '0.74rem' }}>/ wk</span></span> },
    { key: 'status', header: 'Status', render: (r: StaffMember) => (
        <Badge tone={r.status === 'Active' ? 'green' : 'amber'}>{r.status}</Badge>
      ) },
  ]

  return <Table columns={columns} rows={rows} rowKey={(r) => r.id} empty="No staff found for the current filters." />
}