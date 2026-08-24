'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getDashboard, getAttendance, getMarks } from '@/lib/api/mock'
import type { AttendanceRecord, DashboardData, MarksEntry } from '@/types'
import { useAuth } from '@/providers/auth-context'
import { Badge, Card, PageHeader, Spinner, StatCard } from '@/components/ui'

export default function Dashboard() {
  const { user } = useAuth()
  const [data, setData] = useState<DashboardData | null>(null)
  const [attendance, setAttendance] = useState<AttendanceRecord[]>([])
  const [marks, setMarks] = useState<MarksEntry[]>([])

  useEffect(() => {
    void Promise.all([getDashboard(), getAttendance(), getMarks()]).then(([d, a, m]) => {
      setData(d)
      setAttendance(a)
      setMarks(m)
    })
  }, [])

  if (!data) return <Spinner />

  const firstName = user?.fullName?.split(' ')[0] ?? 'there'
  const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })
  const absentToday = attendance.filter((a) => a.status === 'Absent').length
  const maxTrend = Math.max(...data.attendanceTrend.map((p) => p.value))
  const maxMarks = Math.max(...data.classReport.map((c) => c.marks))

  return (
    <div className="page">
      <PageHeader
        title={`${data.greeting}, ${firstName} 👋`}
        subtitle={today}
        actions={
          <Link href="/dashboard/ai-copilot" className="btn btn-outline btn-sm">🤖 Ask EduConnect AI</Link>
        }
      />

      {/* KPI row */}
      <div className="kpi-grid">
        {data.kpis.map((k) => (
          <StatCard key={k.label} icon={k.icon} label={k.label} value={k.value} delta={k.delta} />
        ))}
      </div>

      <div className="dash-grid">
        {/* Attendance trend (pure-CSS bars) */}
        <Card title="Attendance this week" className="dash-span-2"
          action={<Badge tone="green">{attendance.length - absentToday}/{attendance.length} present</Badge>}>
          <div className="bar-chart">
            {data.attendanceTrend.map((p) => (
              <div key={p.label} className="bar-col" title={`${p.label}: ${p.value}%`}>
                <div className="bar-track">
                  <div className="bar" style={{ height: `${(p.value / maxTrend) * 100}%` }} />
                </div>
                <span className="bar-label">{p.label}</span>
              </div>
            ))}
          </div>
        </Card>

        {/* Class report */}
        <Card title="Class-wise · attending vs marks">
          <div className="cls-report">
            {data.classReport.map((c) => (
              <div key={c.name} className="cls-row">
                <span className="cls-name">{c.name}</span>
                <div className="cls-bars">
                  <div className="cls-bar">
                    <div className="cls-fill cls-fill-teal" style={{ width: `${c.attending}%` }} />
                  </div>
                  <div className="cls-bar">
                    <div className="cls-fill cls-fill-acc" style={{ width: `${(c.marks / maxMarks) * 100}%` }} />
                  </div>
                </div>
                <span className="cls-val">{c.marks}%</span>
              </div>
            ))}
            <div className="cls-legend">
              <span><i className="dot dot-teal" /> Attending</span>
              <span><i className="dot dot-acc" /> Avg marks</span>
            </div>
          </div>
        </Card>

        <Card title="Upcoming" className="dash-col-2">
          <ul className="feed">
            {data.upcoming.map((u) => (
              <li key={u.title} className="feed-item">
                <Badge tone={u.type === 'Exam' ? 'violet' : u.type === 'Meeting' ? 'teal' : 'amber'}>{u.type}</Badge>
                <div className="feed-body">
                  <span className="feed-title">{u.title}</span>
                  <span className="feed-sub">{u.when}</span>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        {/* Marks summary */}
        <Card title="Recent marks entry" className="dash-col-2">
          <div className="feed">
            {marks.slice(0, 3).map((m) => (
              <li key={m.studentId} className="feed-item">
                <span className="feed-avatar">{m.studentName[0]}</span>
                <div className="feed-body">
                  <span className="feed-title">{m.studentName} · {m.className}</span>
                  <span className="feed-sub">
                    {m.rows.map((r) => `${r.subject}: ${r.obtained}`).join(' · ')}
                  </span>
                </div>
              </li>
            ))}
          </div>
        </Card>

        {/* Notices */}
        <Card title="Notices">
          <div className="feed">
            {data.notices.map((n) => (
              <li key={n.title} className="feed-item">
                <div className="feed-body">
                  <span className="feed-title">{n.title}</span>
                  <span className="feed-sub">{n.body}</span>
                  <span className="feed-time">{n.time}</span>
                </div>
              </li>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
