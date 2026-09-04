'use client'
import { useEffect, useState } from 'react'
import { PageHeader, Card, Badge, Spinner, Table, Tabs, Button, Select, Input, type BadgeTone } from '@/components/ui'
import { getEducationReports } from '@/db_demo/school-data'
import type { DataQualityRow, EducationReportRow } from '@/types'
import { useReports } from './useReports'

type ReportTab = 'Report Builder' | 'Director Center' | 'Education' | 'Data Quality'
const TABS: ReportTab[] = ['Report Builder', 'Director Center', 'Education', 'Data Quality']

const qTone: Record<DataQualityRow['status'], BadgeTone> = { Healthy: 'green', Attention: 'amber', Critical: 'red' }

export default function ReportsPage() {
  const r = useReports()
  const [tab, setTab] = useState<ReportTab>('Director Center')
  const [edu, setEdu] = useState<EducationReportRow[]>([])

  useEffect(() => {
    let alive = true
    getEducationReports().then((e) => {
      if (alive) setEdu(e)
    })
    return () => {
      alive = false
    }
  }, [])

  const qualityCols = [
    { key: 'area', header: 'Data area', render: (row: DataQualityRow) => <b>{row.area}</b> },
    { key: 'score', header: 'Quality score', render: (row: DataQualityRow) => `${row.score}%` },
    { key: 'issue', header: 'Open issue' },
    { key: 'status', header: 'Status', render: (row: DataQualityRow) => <Badge tone={qTone[row.status]}>{row.status}</Badge> },
  ]

  return (
    <div>
      <PageHeader title="Reports & Analytics" subtitle="School-wide health metrics, report builder and data quality monitoring." />

      {r.loading ? (
        <Spinner />
      ) : (
        <>
          <Tabs tabs={TABS} active={tab} onChange={(t) => setTab(t as ReportTab)} />

          {tab === 'Director Center' && (
            <>
              <div className="stat-tiles">
                <div className="stat-tile"><b>{r.avgScore}%</b><span>Avg data quality</span></div>
                <div className="stat-tile"><b>{r.attentionCount}</b><span>Needs attention</span></div>
                <div className="stat-tile"><b>{r.criticalCount}</b><span>Critical</span></div>
              </div>
              <div className="kpi-grid" style={{ marginTop: 16 }}>
                {r.cards.map((c) => (
                  <Card key={c.id} title={c.title}>
                    <p className="muted">{c.metric}</p>
                    <h3>{c.value}</h3>
                    <Badge tone={c.tone}>{c.trend}</Badge>
                  </Card>
                ))}
              </div>
            </>
          )}

          {tab === 'Report Builder' && (
            <Card title="Build a custom report">
              <div className="form-grid">
                <Select label="Dataset">
                  <option>Fee collection</option>
                  <option>Attendance</option>
                  <option>Exam results</option>
                  <option>Payroll</option>
                </Select>
                <Select label="Group by">
                  <option>Class</option>
                  <option>Fee head</option>
                  <option>Month</option>
                </Select>
                <Input label="From date" type="date" />
                <Input label="To date" type="date" />
              </div>
              <div className="modal-actions">
                <Button variant="primary" onClick={() => alert('Report generated (mock) — backend will stream Excel/PDF.')}>Generate</Button>
                <Button variant="outline" onClick={() => alert('Scheduled — will email every Monday (mock).')}>Schedule weekly</Button>
              </div>
            </Card>
          )}

          {tab === 'Education' && (
            <Table
              columns={[
                { key: 'metric', header: 'Metric', render: (row: EducationReportRow) => <b>{row.metric}</b> },
                { key: 'className', header: 'Scope' },
                { key: 'value', header: 'Value' },
                { key: 'trend', header: 'Trend', render: (row: EducationReportRow) => <Badge tone={row.trend.includes('-') ? 'amber' : 'green'}>{row.trend}</Badge> },
              ]}
              rows={edu}
              rowKey={(row) => row.id}
              empty="No education reports yet."
            />
          )}

          {tab === 'Data Quality' && (
            <Table columns={qualityCols} rows={r.quality} rowKey={(row) => row.id} empty="No data quality issues found." />
          )}
        </>
      )}
    </div>
  )
}