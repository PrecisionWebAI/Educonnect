'use client'
import { PageHeader, Tabs, Spinner, Table, Badge, type BadgeTone } from '@/components/ui'
import { useTickets, type TicketTab } from './useTickets'
import type { TicketItem } from '@/types'

const TABS: TicketTab[] = ['My Tickets', 'Inbox']

const prioTone: Record<TicketItem['priority'], BadgeTone> = { Low: 'green', Medium: 'amber', High: 'red' }
const statusTone: Record<TicketItem['status'], BadgeTone> = { Open: 'red', 'In Progress': 'amber', Resolved: 'teal', Closed: 'green' }

export default function TicketsPage() {
  const t = useTickets()

  const cols = [
    { key: 'subject', header: 'Ticket', render: (r: TicketItem) => <b>{r.subject}</b> },
    { key: 'category', header: 'Category', render: (r: TicketItem) => <Badge tone="violet">{r.category}</Badge> },
    { key: 'priority', header: 'Priority', render: (r: TicketItem) => <Badge tone={prioTone[r.priority]}>{r.priority}</Badge> },
    { key: 'status', header: 'Status', render: (r: TicketItem) => <Badge tone={statusTone[r.status]}>{r.status}</Badge> },
    { key: 'assignee', header: 'Assignee' },
    { key: 'updated', header: 'Updated' },
  ]

  const rows = t.tab === 'Inbox' ? t.tickets.filter((r) => r.status === 'Open' || r.status === 'In Progress') : t.tickets

  return (
    <div>
      <PageHeader title="Tickets & Support" subtitle="Raise and track IT, accounts and facility help requests." />

      {t.loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-tiles">
            <div className="stat-tile"><b>{t.openCount}</b><span>Open</span></div>
            <div className="stat-tile"><b>{t.inProgressCount}</b><span>In Progress</span></div>
            <div className="stat-tile"><b>{t.resolvedCount}</b><span>Resolved</span></div>
          </div>

          <Tabs tabs={TABS} active={t.tab} onChange={(x) => t.setTab(x as TicketTab)} />

          <Table columns={cols} rows={rows} rowKey={(r) => r.id} empty="No tickets in this view." />
        </>
      )}
    </div>
  )
}