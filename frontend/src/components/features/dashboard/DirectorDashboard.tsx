'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getAttendance, getDashboard, getMarks } from '@/db_demo/school-data'
import type { AttendanceRecord, DashboardData, MarksEntry } from '@/types'
import { Badge, Button, Card, PageHeader, Spinner } from '@/components/ui'
import Icon from '@/components/ui/Icon'
import KpiGrid from './KpiGrid'
import AttendanceChart from './AttendanceChart'
import DashboardFeeds from './DashboardFeeds'
import AiInsightsCard from './AiInsightsCard'
import QuickActions from './QuickActions'
import RecentActivity from './RecentActivity'

// Tab D.1 — Director Dashboard (purple). Admin overview widgets.
export default function DirectorDashboard() {
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

  const today = new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })
  const absentToday = attendance.filter((a) => a.status === 'Absent').length
  const maxMarks = Math.max(...data.classReport.map((c) => c.marks))

  return (
    <div className="page">
      <PageHeader
        title="Director Overview"
        subtitle={today}
        actions={
          <>
            <Button variant="outline" size="sm"><Icon name="download" size={16} /> Export</Button>
            <Link className="btn btn-outline btn-sm" href="/dashboard/ai-copilot"><Icon name="ai" size={16} /> Ask EduConnect AI</Link>
          </>
        }
      />

      <KpiGrid kpis={data.kpis} />

      <div className="dash-grid">
        <Card
          title="Attendance this week"
          className="dash-span-2"
          action={<Badge tone="green">{attendance.length - absentToday}/{attendance.length} present</Badge>}
        >
          <AttendanceChart trend={data.attendanceTrend} />
        </Card>

        <AiInsightsCard />

        <Card title="Class-wise · attending vs marks">
          <div className="cls-report">
            {data.classReport.map((c) => (
              <div key={c.name} className="cls-row">
                <span className="cls-name">{c.name}</span>
                <div className="cls-bars">
                  <div className="cls-bar"><div className="cls-fill cls-fill-teal" style={{ width: `${c.attending}%` }} /></div>
                  <div className="cls-bar"><div className="cls-fill cls-fill-acc" style={{ width: `${(c.marks / maxMarks) * 100}%` }} /></div>
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

        <QuickActions />

        <DashboardFeeds upcoming={data.upcoming} marks={marks} notices={data.notices} />

        <RecentActivity />
      </div>
    </div>
  )
}