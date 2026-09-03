'use client'
import { useState } from 'react'
import { PageHeader, Tabs, Spinner, Table, Badge, Card, Input, Select, Textarea, Button, type BadgeTone } from '@/components/ui'
import { useToast } from '@/components/ui/toast'
import { useTickets, type TicketTab } from './useTickets'
import type { TicketItem } from '@/types'

const TABS: TicketTab[] = ['My Tickets', 'Raise', 'Inbox', 'Oversight']

const prioTone: Record<TicketItem['priority'], BadgeTone> = { Low: 'green', Medium: 'amber', High: 'red' }
const statusTone: Record<TicketItem['status'], BadgeTone> = { Open: 'red', 'In Progress': 'amber', Resolved: 'teal', Closed: 'green' }

export default function TicketsPage() {
  const t = useTickets()
  const { push } = useToast()
  const [subject, setSubject] = useState('')
  const [category, setCategory] = useState<TicketItem['category']>('IT')
  const [priority, setPriority] = useState<TicketItem['priority']>('Medium')
  const [detail, setDetail] = useState('')

  function raise() {
    if (!subject.trim()) {
      push('error', 'Subject is required.')
      return
    }
    push('success', `Ticket raised to ${category === 'IT' ? 'Tech Desk' : category === 'Accounts' ? 'Finance' : 'Principal'} — you will be notified.`)
    setSubject(''); setDetail('')
  }

  const cols = [
    { key: 'subject', header: 'Ticket', render: (r: TicketItem) => <b>{r.subject}</b> },
    { key: 'category', header: 'Category', render: (r: TicketItem) => <Badge tone="violet">{r.category}</Badge> },
    { key: 'priority', header: 'Priority', render: (r: TicketItem) => <Badge tone={prioTone[r.priority]}>{r.priority}</Badge> },
    { key: 'status', header: 'Status', render: (r: TicketItem) => <Badge tone={statusTone[r.status]}>{r.status}</Badge> },
    { key: 'assignee', header: 'Assignee' },
    { key: 'updated', header: 'Updated' },
  ]

  const rows =
    t.tab === 'Inbox'
      ? t.tickets.filter((r) => r.status === 'Open' || r.status === 'In Progress')
      : t.tickets

  const slaCols = [
    { key: 'subject', header: 'Ticket', render: (r: TicketItem) => <b>{r.subject}</b> },
    { key: 'category', header: 'Category', render: (r: TicketItem) => <Badge tone="violet">{r.category}</Badge> },
    { key: 'priority', header: 'Priority', render: (r: TicketItem) => <Badge tone={prioTone[r.priority]}>{r.priority}</Badge> },
    { key: 'status', header: 'Status', render: (r: TicketItem) => <Badge tone={statusTone[r.status]}>{r.status}</Badge> },
    { key: 'reporter', header: 'Reporter' },
    { key: 'assignee', header: 'Assignee' },
    { key: 'updated', header: 'SLA', render: (r: TicketItem) => <Badge tone={r.priority === 'High' ? 'red' : 'muted'}>{r.priority === 'High' ? 'Breaching soon' : 'On track'}</Badge> },
  ]

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

          {t.tab === 'Raise' && (
            <Card title="Raise a ticket">
              <div className="form-grid">
                <Input label="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Short summary" />
                <Select label="Category" value={category} onChange={(e) => setCategory(e.target.value as TicketItem['category'])}>
                  {['IT', 'Accounts', 'Facility', 'Academic', 'Other'].map((c) => <option key={c}>{c}</option>)}
                </Select>
                <Select label="Priority" value={priority} onChange={(e) => setPriority(e.target.value as TicketItem['priority'])}>
                  <option>Low</option>
                  <option>Medium</option>
                  <option>High</option>
                </Select>
                <div style={{ gridColumn: '1 / -1' }}>
                  <Textarea label="Details" value={detail} onChange={(e) => setDetail(e.target.value)} placeholder="Describe the issue; attach proofs from the mobile app." />
                </div>
              </div>
              <div className="modal-actions">
                <Button variant="primary" onClick={raise}>Submit ticket</Button>
              </div>
            </Card>
          )}

          {(t.tab === 'My Tickets' || t.tab === 'Inbox') && (
            <Table columns={cols} rows={rows} rowKey={(r) => r.id} empty="No tickets in this view." />
          )}

          {t.tab === 'Oversight' && (
            <>
              <p style={{ color: 'var(--muted)', marginBottom: '0.6rem' }}>
                Principal / Director oversight — all tickets with SLA health across the escalation chain.
              </p>
              <Table columns={slaCols} rows={t.tickets} rowKey={(r) => r.id} empty="No tickets across the chain." />
            </>
          )}
        </>
      )}
    </div>
  )
}