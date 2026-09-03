'use client'
import { PageHeader, Card, Badge, Spinner, Table, type BadgeTone } from '@/components/ui'
import { useReports } from './useReports'
import type { DataQualityRow } from '@/types'

const qTone: Record<DataQualityRow['status'], BadgeTone> = { Healthy: 'green', Attention: 'amber', Critical: 'red' }

export default function ReportsPage() {
  const r = useReports()

  const cols = [
    { key: 'area', header: 'Data area', render: (row: DataQualityRow) => <b>{row.area}</b> },
    { key: 'score', header: 'Quality score', render: (row: DataQualityRow) => `${row.score}%` },
    { key: 'issue', header: 'Open issue' },
    { key: 'status', header: 'Status', render: (row: DataQualityRow) => <Badge tone={qTone[row.status]}>{row.status}</Badge> },
  ]

  return (
    <div>
      <PageHeader title="Reports & Analytics" subtitle="School-wide health metrics and data quality monitoring." />

      {r.loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-tiles">
            <div className="stat-tile"><b>{r.avgScore}%</b><span>Avg data quality</span></div>
            <div className="stat-tile"><b>{r.attentionCount}</b><span>Needs attention</span></div>
            <div className="stat-tile"><b>{r.criticalCount}</b><span>Critical</span></div>
          </div>

          <div className="kpi-grid">
            {r.cards.map((c) => (
              <Card key={c.id} title={c.title}>
                <p className="muted">{c.metric}</p>
                <h3>{c.value}</h3>
                <Badge tone={c.tone}>{c.trend}</Badge>
              </Card>
            ))}
          </div>

          <h3 style={{ margin: '24px 0 12px' }}>Data quality report</h3>
          <Table columns={cols} rows={r.quality} rowKey={(row) => row.id} empty="No data quality issues found." />
        </>
      )}
    </div>
  )
}