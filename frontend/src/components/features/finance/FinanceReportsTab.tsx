'use client'
import { useEffect, useState } from 'react'
import { Spinner, Table, Badge } from '@/components/ui'
import { getCollectionReports } from '@/db_demo/school-data'
import type { CollectionReportRow } from '@/types'

// Tab 11.4 — director's collection reports (period-wise, cash vs digital split).
export default function FinanceReportsTab() {
  const [rows, setRows] = useState<CollectionReportRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    getCollectionReports().then((r) => {
      if (!alive) return
      setRows(r)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [])

  if (loading) return <Spinner />

  return (
    <>
      <p style={{ color: 'var(--muted)', marginBottom: '0.6rem' }}>
        Collection reports — daily, weekly and term-wise; per head and per class drill-down available in exports.
      </p>
      <Table
        columns={[
          { key: 'period', header: 'Period', render: (r: CollectionReportRow) => <b>{r.period}</b> },
          { key: 'billed', header: 'Billed' },
          { key: 'collected', header: 'Collected' },
          { key: 'variance', header: 'Variance', render: (r: CollectionReportRow) => <Badge tone={r.variance.startsWith('-') ? 'amber' : 'green'}>{r.variance}</Badge> },
          { key: 'mode', header: 'Cash vs digital' },
        ]}
        rows={rows}
        rowKey={(r) => r.id}
        empty="No collection reports yet."
      />
    </>
  )
}