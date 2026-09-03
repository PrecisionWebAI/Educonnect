'use client'
import { Table, Badge } from '@/components/ui'
import { currency } from './PayrollPage'
import type { PayrollEntry } from '@/types'

export default function MonthProcessingTable({
  rows,
  statusTone,
}: {
  rows: PayrollEntry[]
  statusTone: (s: string) => 'amber' | 'accent' | 'green' | 'muted'
}) {
  const columns = [
    { key: 'staffCode', header: 'ID', render: (r: PayrollEntry) => <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{r.staffCode}</span> },
    { key: 'name', header: 'Name' },
    { key: 'basic', header: 'Basic', render: (r: PayrollEntry) => currency(r.basic) },
    { key: 'allowances', header: 'Allowances', render: (r: PayrollEntry) => currency(r.allowances) },
    { key: 'deductions', header: 'Deductions', render: (r: PayrollEntry) => '-' + currency(r.deductions) },
    { key: 'net', header: 'Net Pay', render: (r: PayrollEntry) => <b>{currency(r.net)}</b> },
    { key: 'status', header: 'Status', render: (r: PayrollEntry) => <Badge tone={statusTone(r.status)}>{r.status}</Badge> },
  ]
  return (
    <Table
      columns={columns}
      rows={rows}
      rowKey={(r) => r.id}
      empty="No payroll entries match the filters."
    />
  )
}