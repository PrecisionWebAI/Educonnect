'use client'
import { useEffect, useState } from 'react'
import { PageHeader, Tabs, Spinner, Card, Input, Select, Textarea, Button, Table, Badge, type BadgeTone } from '@/components/ui'
import { useToast } from '@/components/ui/toast'
import { getStaffLeaveRequests } from '@/temp/school-data'
import { useLeave, type LeaveTab } from './useLeave'
import type { LeaveApplicationItem, StaffLeaveRow } from '@/types'

const TABS: LeaveTab[] = ['Apply', 'My Leaves', 'Approvals', 'Staff Leave']

const typeTone: Record<LeaveApplicationItem['type'], BadgeTone> = {
  Medical: 'teal',
  Personal: 'amber',
  OD: 'violet',
  Event: 'accent',
  Travel: 'green',
}

export default function LeavePage() {
  const l = useLeave()
  const { push } = useToast()
  const [staffLeaves, setStaffLeaves] = useState<StaffLeaveRow[]>([])

  useEffect(() => {
    let alive = true
    getStaffLeaveRequests().then((s) => {
      if (alive) setStaffLeaves(s)
    })
    return () => {
      alive = false
    }
  }, [])

  const [student, setStudent] = useState('Aarav Mehta')
  const [type, setType] = useState<LeaveApplicationItem['type']>('Medical')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [reason, setReason] = useState('')

  const submit = () => {
    if (!from || !to) {
      push('error', 'Select dates for the leave range.')
      return
    }
    push('success', 'Leave application submitted.')
    setFrom(''); setTo(''); setReason('')
  }

  const cols = [
    { key: 'student', header: 'Student' },
    { key: 'type', header: 'Type', render: (r: LeaveApplicationItem) => <Badge tone={typeTone[r.type]}>{r.type}</Badge> },
    { key: 'range', header: 'Range', render: (r: LeaveApplicationItem) => `${r.from} -> ${r.to}` },
    { key: 'days', header: 'Days' },
    { key: 'reason', header: 'Reason' },
    { key: 'status', header: 'Status', render: (r: LeaveApplicationItem) => <Badge tone={r.status === 'Approved' ? 'green' : r.status === 'Rejected' ? 'red' : 'amber'}>{r.status}</Badge> },
  ]

  const rows = l.tab === 'My Leaves' ? l.leaves.filter((r) => r.status !== 'Pending') : l.tab === 'Approvals' ? l.leaves.filter((r) => r.status === 'Pending') : l.leaves
  const title = l.tab === 'My Leaves' ? 'Leave History' : l.tab === 'Approvals' ? 'Pending Approvals' : 'Recent Applications'

  return (
    <div>
      <PageHeader title="Leave & Applications" subtitle="Apply for leave, track status and approve student applications." />

      {l.loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-tiles">
            <div className="stat-tile"><b>{l.leaves.length}</b><span>Applications</span></div>
            <div className="stat-tile"><b>{l.pendingCount}</b><span>Pending</span></div>
            <div className="stat-tile"><b>{l.approvedCount}</b><span>Approved</span></div>
          </div>

          <Tabs tabs={TABS} active={l.tab} onChange={(t) => l.setTab(t as LeaveTab)} />

          {l.tab === 'Apply' && (
            <Card title="New Leave Application">
              <div className="form-grid">
                <Input label="Student" value={student} onChange={(e) => setStudent(e.target.value)} />
                <Select label="Type" value={type} onChange={(e) => setType(e.target.value as LeaveApplicationItem['type'])}>
                  {['Medical', 'Personal', 'OD', 'Event', 'Travel'].map((t) => <option key={t}>{t}</option>)}
                </Select>
                <Input label="From" type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
                <Input label="To" type="date" value={to} onChange={(e) => setTo(e.target.value)} />
                <div style={{ gridColumn: '1 / -1' }}>
                  <Textarea label="Reason" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Why the leave is requested..." />
                </div>
              </div>
              <div className="modal-actions">
                <Button variant="primary" onClick={submit}>Submit Application</Button>
              </div>
            </Card>
          )}

          {(l.tab === 'My Leaves' || l.tab === 'Approvals') && (
            <>
              <div style={{ marginBottom: '0.7rem', fontSize: '0.9rem', fontWeight: 700 }}>{title}</div>
              {l.tab === 'Approvals' && (
              <div style={{ marginBottom: '0.7rem' }}>
                {rows.map((r) => r.status === 'Pending' ? (
                  <div key={r.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.88rem' }}>{r.student} - {r.type} ({r.from})</span>
                    <Button size="sm" variant="success" onClick={() => { l.approve(r.id); push('success', 'Approved') }}>Approve</Button>
                  </div>
                ) : null)}
              </div>
            )}
            <Table columns={cols} rows={rows} rowKey={(r) => r.id} empty="No leave applications." /></>
          )}

          {l.tab === 'Staff Leave' && (
            <>
              <p style={{ color: 'var(--muted)', marginBottom: '0.6rem' }}>
                Teacher & staff leave requests — principal approves long leaves; balances shown per person.
              </p>
              <Table
                columns={[
                  { key: 'name', header: 'Staff', render: (r: StaffLeaveRow) => <b>{r.name}</b> },
                  { key: 'role', header: 'Role' },
                  { key: 'type', header: 'Leave type' },
                  { key: 'from', header: 'From' },
                  { key: 'days', header: 'Days' },
                  { key: 'balance', header: 'Balance' },
                  { key: 'status', header: 'Status', render: (r: StaffLeaveRow) => <Badge tone={r.status === 'Approved' ? 'green' : r.status === 'Rejected' ? 'red' : 'amber'}>{r.status}</Badge> },
                ]}
                rows={staffLeaves}
                rowKey={(r) => r.id}
                empty="No staff leave requests."
              />
            </>
          )}
        </>
      )}
    </div>
  )
}
