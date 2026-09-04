'use client'

import { useEffect, useState } from 'react'
import { getApprovals, getClassAttendance, getOperationsBoard } from '@/db_demo/school-data'
import type { ApprovalItem, OperationsBoard } from '@/types'
import { Badge, Card, PageHeader, Button, Spinner } from '@/components/ui'
import { useToast } from '@/components/ui/toast'
import Icon from '@/components/ui/Icon'
import AttendanceChart from './AttendanceChart'

// Tab D.2 — Principal Dashboard (purple)
export default function PrincipalDashboard() {
  const toast = useToast()
  const [board, setBoard] = useState<OperationsBoard | null>(null)
  const [approvals, setApprovals] = useState<ApprovalItem[]>([])
  const [trend, setTrend] = useState([{ label: 'Mon', value: 90 }, { label: 'Tue', value: 94 }, { label: 'Wed', value: 92 }, { label: 'Thu', value: 96 }, { label: 'Fri', value: 93 }])

  useEffect(() => {
    void Promise.all([getOperationsBoard(), getApprovals()]).then(([b, a]) => {
      setBoard(b)
      setApprovals(a)
    })
  }, [])

  if (!board) return <Spinner />

  const ops = [
    { icon: 'book' as const, label: 'Running Classes', value: String(board.runningClasses) },
    { icon: 'guardian' as const, label: 'Teachers Present', value: `${board.presentTeachers}/${board.teachersTotal}` },
    { icon: 'check' as const, label: 'Substitutes', value: String(board.substitutes) },
  ]

  const toneOf = (k: ApprovalItem['kind']) => k === 'Leave' ? 'amber' : k === 'Paper approval' ? 'violet' : k === 'Fee waiver' ? 'teal' : 'red'

  return (
    <div className="page">
      <PageHeader title="Principal Overview" subtitle="Today's operations & approvals" />

      <div className="kpi-grid">
        {ops.map((o) => (
          <div key={o.label} className="stat">
            <span className="stat-ico"><Icon name={o.icon} size={20} /></span>
            <div className="stat-value">{o.value}</div>
            <div className="stat-label">{o.label}</div>
          </div>
        ))}
      </div>

      <div className="dash-grid" style={{ marginTop: '1rem' }}>
        <Card title="School-wide Attendance" className="dash-span-2" action={<Badge tone="green">93% avg</Badge>}>
          <AttendanceChart trend={trend} />
        </Card>

        <Card title="Approval Queue" className="dash-span-2">
          {approvals.length === 0 ? (
            <p style={{ color: 'var(--muted)' }}>All caught up.</p>
          ) : (
            <ul className="feed">
              {approvals.map((a) => (
                <li key={a.id} className="feed-item">
                  <Badge tone={toneOf(a.kind)}>{a.kind}</Badge>
                  <div className="feed-body">
                    <span className="feed-title">{a.summary}</span>
                    <span className="feed-sub">{a.requester} · {a.time}</span>
                  </div>
                  <Button size="sm" variant="success" onClick={() => { setApprovals((p) => p.filter((x) => x.id !== a.id)); toast.push('success', 'Approved') }}>Approve</Button>
                  <Button size="sm" variant="ghost" onClick={() => { setApprovals((p) => p.filter((x) => x.id !== a.id)); toast.push('info', 'Rejected') }}>Reject</Button>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Upcoming Events">
          <ul className="feed">
            {board.upcomingEvents.map((e) => (
              <li key={e.title} className="feed-item">
                <div className="feed-body">
                  <span className="feed-title">{e.title}</span>
                  <span className="feed-sub">{e.when}</span>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}