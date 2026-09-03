'use client'
import { PageHeader, Tabs, Spinner, Table, Badge, type BadgeTone } from '@/components/ui'
import { useMeetings, type MeetingTab } from './useMeetings'
import type { MeetingItem } from '@/types'

const TABS: MeetingTab[] = ['Upcoming', 'Pending', 'History']

const typeTone: Record<MeetingItem['type'], BadgeTone> = { Scheduled: 'accent', Pending: 'amber', Done: 'green' }

export default function MeetingsPage() {
  const m = useMeetings()

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

          <Table columns={cols} rows={m.filtered} rowKey={(r) => r.id} empty="No meetings in this view." />
        </>
      )}
    </div>
  )
}