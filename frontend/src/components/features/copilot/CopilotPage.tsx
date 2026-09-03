'use client'
import { useEffect, useState } from 'react'
import { PageHeader, Tabs, Spinner, Table, Badge, Card, Button, Input } from '@/components/ui'
import { getPaletteCommands } from '@/temp/school-data'
import type { PaletteCommand } from '@/types'
import { useCopilot, type CopilotTab } from './useCopilot'
import type { CopilotAutomation } from '@/types'

const TABS: CopilotTab[] = ['Ask AI', 'Command Palette', 'Genius Assistant', 'Automations']

export default function CopilotPage() {
  const c = useCopilot()
  const [commands, setCommands] = useState<PaletteCommand[]>([])

  useEffect(() => {
    let alive = true
    getPaletteCommands().then((cmds) => {
      if (alive) setCommands(cmds)
    })
    return () => {
      alive = false
    }
  }, [])

  const autoCols = [
    { key: 'title', header: 'Automation', render: (a: CopilotAutomation) => <b>{a.title}</b> },
    { key: 'schedule', header: 'Schedule' },
    { key: 'lastRun', header: 'Last run' },
    { key: 'active', header: 'Status', render: (a: CopilotAutomation) => <Badge tone={a.active ? 'green' : 'red'}>{a.active ? 'Active' : 'Paused'}</Badge> },
  ]

  return (
    <div>
      <PageHeader title="AI Copilot" subtitle="Your school assistant for insights, drafts and automation." />

      {c.loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-tiles">
            <div className="stat-tile"><b>{c.automations.length}</b><span>Automations</span></div>
            <div className="stat-tile"><b>{c.activeCount}</b><span>Running</span></div>
          </div>

          <Tabs tabs={TABS} active={c.tab} onChange={(t) => c.setTab(t as CopilotTab)} />

          {c.tab === 'Command Palette' && (
            <>
              <p style={{ color: 'var(--muted)', margin: '16px 0 8px' }}>
                Press <b>Ctrl-K</b> anywhere in the app to open the palette. Top commands:
              </p>
              <Table
                columns={[
                  { key: 'label', header: 'Command', render: (x: PaletteCommand) => <b>{x.label}</b> },
                  { key: 'shortcut', header: 'Shortcut', render: (x: PaletteCommand) => <Badge tone="accent">{x.shortcut}</Badge> },
                  { key: 'category', header: 'Category' },
                ]}
                rows={commands}
                rowKey={(x) => x.id}
                empty="No commands registered."
              />
            </>
          )}

          {c.tab === 'Genius Assistant' && (
            <>
              <p style={{ color: 'var(--muted)', margin: '16px 0 8px' }}>
                Contextual suggestions based on what you were last doing.
              </p>
              <div className="kpi-grid">
                {c.suggestions.map((s) => (
                  <div key={s.id} onClick={() => { c.setTab('Ask AI'); c.setPrompt(s.prompt) }} style={{ cursor: 'pointer' }}>
                    <Card className="clickable">
                      <Badge tone="teal">{s.tag}</Badge>
                      <p style={{ marginTop: 8 }}>{s.prompt}</p>
                    </Card>
                  </div>
                ))}
              </div>
            </>
          )}

          {c.tab === 'Ask AI' && (
            <div style={{ marginTop: 16 }}>
              <div className="toolbar">
                <Input
                  placeholder="Ask anything about your school..."
                  value={c.prompt}
                  onChange={(e) => c.setPrompt(e.target.value)}
                />
                <Button variant="primary">Ask</Button>
              </div>

              <h3 style={{ margin: '24px 0 12px' }}>Suggested prompts</h3>
              <div className="kpi-grid">
                {c.suggestions.map((s) => (
                  <Card key={s.id} className="clickable" >
                    <Badge tone="violet">{s.tag}</Badge>
                    <p style={{ marginTop: 8 }}>{s.prompt}</p>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {c.tab === 'Automations' && (
            <div style={{ marginTop: 16 }}>
              <Table columns={autoCols} rows={c.automations} rowKey={(a) => a.id} empty="No automations yet." />
            </div>
          )}
        </>
      )}
    </div>
  )
}