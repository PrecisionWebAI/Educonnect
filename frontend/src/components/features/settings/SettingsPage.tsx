'use client'
import { PageHeader, Tabs, Spinner, Table, Badge, Card, Button, Input, type BadgeTone } from '@/components/ui'
import { useSettings, type SettingsTab } from './useSettings'
import type { SettingUser } from '@/types'

const TABS: SettingsTab[] = ['Users & Roles', 'School Profile', 'Security']
const roleTone: Record<SettingUser['role'], BadgeTone> = { Admin: 'red', Teacher: 'teal', Accountant: 'violet', Staff: 'accent' }
const statusTone: Record<SettingUser['status'], BadgeTone> = { Active: 'green', Invited: 'amber', Disabled: 'red' }

export default function SettingsPage() {
  const s = useSettings()

  const userCols = [
    { key: 'name', header: 'Name', render: (u: SettingUser) => <b>{u.name}</b> },
    { key: 'email', header: 'Email' },
    { key: 'role', header: 'Role', render: (u: SettingUser) => <Badge tone={roleTone[u.role]}>{u.role}</Badge> },
    { key: 'status', header: 'Status', render: (u: SettingUser) => <Badge tone={statusTone[u.status]}>{u.status}</Badge> },
  ]

  return (
    <div>
      <PageHeader title="Settings & Configuration" subtitle="Manage users, school profile and security." />

      {s.loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-tiles">
            <div className="stat-tile"><b>{s.activeCount}</b><span>Active users</span></div>
            <div className="stat-tile"><b>{s.pendingCount}</b><span>Pending invites</span></div>
            <div className="stat-tile"><b>{s.logs.length}</b><span>Security events</span></div>
          </div>

          <Tabs tabs={TABS} active={s.tab} onChange={(t) => s.setTab(t as SettingsTab)} />

          {s.tab === 'Users & Roles' && (
            <>
              <div className="toolbar" style={{ margin: '16px 0' }}>
                <Input placeholder="Search users..." />
                <Button variant="primary">Invite user</Button>
              </div>
              <Table columns={userCols} rows={s.users} rowKey={(u) => u.id} empty="No users yet." />
            </>
          )}

          {s.tab === 'School Profile' && (
            <div className="kpi-grid" style={{ marginTop: 16 }}>
              {s.info.map((i) => (
                <Card key={i.id} title={i.label}>
                  <p>{i.value}</p>
                </Card>
              ))}
              <div className="modal-actions">
                <Button variant="primary">Save changes</Button>
              </div>
            </div>
          )}

          {s.tab === 'Security' && (
            <div style={{ marginTop: 16 }}>
            <Table
              columns={[
                { key: 'event', header: 'Event', render: (l) => <b>{l.event}</b> },
                { key: 'user', header: 'User' },
                { key: 'when', header: 'When' },
              ]}
              rows={s.logs}
              rowKey={(l) => l.id}
              empty="No security events."
            />
            </div>
          )}
        </>
      )}
    </div>
  )
}