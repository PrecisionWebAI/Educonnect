'use client'
import { PageHeader, Tabs, Spinner, Table, Badge, Card, Input, Select, Button, type BadgeTone } from '@/components/ui'
import { useToast } from '@/components/ui/toast'
import { useMeetings, type MeetingTab } from './useMeetings'
import type { MeetingItem } from '@/types'

const TABS: MeetingTab[] = ['Upcoming', 'Book', 'Pending', 'History']

const typeTone: Record<MeetingItem['type'], BadgeTone> = { Scheduled: 'accent', Pending: 'amber', Done: 'green' }

export default function MeetingsPage() {
  const m = useMeetings()
  const toast = useToast()

  const cols = [
    { key: 'title', header: 'Meeting', render: (r: MeetingItem) => <b>{r.title}</b> },
    { key: 'with', header: 'With' },
    { key: 'date', header: 'Date' },
    { key: 'time', header: 'Time' },
    { key: 'room', header: 'Room' },
    { key: 'type', header: 'Status', render: (r: MeetingItem) => <Badge tone={typeTone[r.type]}>{r.type}</Badge> },
  ]

  return (
    <div>
      <PageHeader title="Meetings" subtitle="Book and manage parent-teacher meetings, staff syncs and reviews." />

      {m.loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-tiles">
            <div className="stat-tile"><b>{m.meetings.length}</b><span>Meetings</span></div>
            <div className="stat-tile"><b>{m.pendingCount}</b><span>Pending</span></div>
            <div className="stat-tile"><b>{m.doneCount}</b><span>Completed</span></div>
          </div>

          <Tabs tabs={TABS} active={m.tab} onChange={(t) => m.setTab(t as MeetingTab)} />

          {m.tab === 'Book' ? (
            <Card title="Book a parent-teacher meeting">
              <div className="form-grid">
                <Input label="Parent name" placeholder="e.g. Mrs. Sharma" />
                <Input label="Date" type="date" />
                <Select label="Slot">
                  <option>09:00 - 09:15</option>
                  <option>09:15 - 09:30</option>
                  <option>10:00 - 10:15</option>
                  <option>14:00 - 14:15</option>
                </Select>
                <Select label="Mode">
                  <option>In person</option>
                  <option>Video call</option>
                </Select>
              </div>
              <div className="modal-actions">
                <Button variant="primary" onClick={() => toast.push('success', 'Slot booked — parent notified.')}>Book slot</Button>
              </div>
            </Card>
          ) : (
            <Table columns={cols} rows={m.filtered} rowKey={(r) => r.id} empty="No meetings in this view." />
          )}
        </>
      )}
    </div>
  )
}