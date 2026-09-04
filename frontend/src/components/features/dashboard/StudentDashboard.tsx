'use client'

import { useEffect, useState } from 'react'
import { getStudentPortal } from '@/db_demo/school-data'
import type { StudentPortalData } from '@/types'
import { Badge, Card, PageHeader, Spinner } from '@/components/ui'
import Icon from '@/components/ui/Icon'

// Tab D.6 — Student Dashboard (stitch: student_portal_dark_mode)
export default function StudentDashboard() {
  const [data, setData] = useState<StudentPortalData | null>(null)
  useEffect(() => { void getStudentPortal().then(setData) }, [])
  if (!data) return <Spinner />

  const perf = [
    { icon: 'attendance' as const, label: 'Attendance', value: `${data.attendancePct}%` },
    { icon: 'trending' as const, label: 'Avg Marks', value: `${data.avgMarks}%` },
    { icon: 'groups' as const, label: 'Class Rank', value: `#${data.rank}` },
    { icon: 'book' as const, label: 'Pending HW', value: String(data.homework.filter((h) => !h.done).length) },
  ]

  return (
    <div className="page">
      <PageHeader title={`Hi, ${data.name}`} subtitle={`Class ${data.className}-${data.section}`} />

      {/* performance cards */}
      <div className="kpi-grid">
        {perf.map((p) => (
          <div key={p.label} className="stat">
            <span className="stat-ico"><Icon name={p.icon} size={20} /></span>
            <div className="stat-value">{p.value}</div>
            <div className="stat-label">{p.label}</div>
          </div>
        ))}
      </div>

      <div className="dash-grid">
        {/* today's schedule */}
        <Card title="Today's Schedule" className="dash-span-2">
          <ul className="feed">
            {data.todaySchedule.map((c) => (
              <li key={c.id} className="feed-item">
                <span className="feed-avatar">{c.period}</span>
                <div className="feed-body">
                  <span className="feed-title">{c.subject}</span>
                  <span className="feed-sub">{c.className} · {c.room}</span>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        {/* homework */}
        <Card title="Homework & Diary">
          <ul className="feed">
            {data.homework.map((h) => (
              <li key={h.id} className="feed-item">
                <Badge tone={h.done ? 'green' : h.due === 'Today' ? 'red' : 'amber'}>{h.done ? 'Done' : h.due}</Badge>
                <div className="feed-body">
                  <span className="feed-title">{h.title}</span>
                  <span className="feed-sub">{h.subject}</span>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        {/* recent grades */}
        <Card title="Recent Grades" className="dash-col-2">
          <div className="feed">
            {data.recentGrades.map((g) => (
              <li key={g.subject} className="feed-item">
                <div className="feed-body">
                  <span className="feed-title">{g.subject}</span>
                  <span className="feed-sub">Score: {g.score}/{g.max}</span>
                </div>
              </li>
            ))}
          </div>
        </Card>

        {/* leaves + tickets */}
        <Card title="My Leaves">
          <ul className="feed">
            {data.leaves.map((l) => (
              <li key={l.id} className="feed-item">
                <Badge tone={l.status === 'Approved' ? 'green' : l.status === 'Rejected' ? 'red' : 'amber'}>{l.status}</Badge>
                <div className="feed-body">
                  <span className="feed-title">{l.type}</span>
                  <span className="feed-sub">{l.range}</span>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="My Tickets">
          <ul className="feed">
            {data.tickets.map((t) => (
              <li key={t.id} className="feed-item">
                <Badge tone={t.status === 'Open' ? 'red' : t.status === 'In Progress' ? 'amber' : 'green'}>{t.status}</Badge>
                <span className="feed-title" style={{ fontWeight: 400 }}>{t.title}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  )
}