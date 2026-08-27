'use client'

import type { DashboardData, MarksEntry } from '@/types'
import { Badge, Card } from '@/components/ui'

// Right-side dashboard feed cards: upcoming, recent marks, notices.
export default function DashboardFeeds({
  upcoming,
  marks,
  notices,
}: {
  upcoming: DashboardData['upcoming']
  marks: MarksEntry[]
  notices: DashboardData['notices']
}) {
  return (
    <>
      <Card title="Upcoming" className="dash-col-2">
        <ul className="feed">
          {upcoming.map((u) => (
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

      <Card title="Notices">
        <div className="feed">
          {notices.map((n) => (
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
    </>
  )
}