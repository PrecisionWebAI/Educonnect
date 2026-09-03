'use client'
import { useState } from 'react'
import { PageHeader, Tabs, Button, Spinner } from '@/components/ui'
import { useTransport, type TransportTab } from './useTransport'
import RoutesTable from './RoutesTable'
import BusesTable from './BusesTable'

const TABS: TransportTab[] = ['Routes & Stops', 'Buses & GPS', 'Fees & Enforcement']

export default function TransportPage() {
  const [tab, setTab] = useState<TransportTab>('Routes & Stops')
  const t = useTransport()

  return (
    <div>
      <PageHeader
        title="Transport"
        subtitle="Routes & stops, buses & live status, and transport fees."
        actions={<Button variant="primary">+ Add Route</Button>}
      />

      {t.loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-tiles">
            <div className="stat-tile"><b>{t.routes.length}</b><span>Routes</span></div>
            <div className="stat-tile"><b>{t.totalStudents}</b><span>Students on Route</span></div>
            <div className="stat-tile"><b>{t.enRoute}</b><span>Buses En Route</span></div>
            <div className="stat-tile"><b>{t.avgOccupancy}%</b><span>Avg Occupancy</span></div>
          </div>

          <Tabs tabs={TABS} active={tab} onChange={(t2) => setTab(t2 as TransportTab)} />

          {tab === 'Routes & Stops' && <RoutesTable rows={t.routes} />}
          {tab === 'Buses & GPS' && <BusesTable rows={t.buses} />}
          {tab === 'Fees & Enforcement' && (
            <p style={{ color: 'var(--muted)' }}>Transport fee structures & route enforcement coming next.</p>
          )}
        </>
      )}
    </div>
  )
}