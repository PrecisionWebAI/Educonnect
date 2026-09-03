'use client'
import { Table, Badge } from '@/components/ui'
import type { BookIssue } from '@/types'

export default function IssueTable({ rows }: { rows: BookIssue[] }) {
  const tone: Record<BookIssue['status'], 'green' | 'accent' | 'red'> = {
    Borrowed: 'accent',
    Returned: 'green',
    Overdue: 'red',
  }
  const columns = [
    { key: 'book', header: 'Book' },
    { key: 'student', header: 'Student' },
    { key: 'issued', header: 'Issued' },
    { key: 'due', header: 'Due' },
    { key: 'status', header: 'Status', render: (r: BookIssue) => <Badge tone={tone[r.status]}>{r.status}</Badge> },
  ]
  return (
    <Table
      columns={columns}
      rows={rows}
      rowKey={(r) => r.id}
      empty="No book issues found."
    />
  )
}