'use client'
import { useEffect, useState } from 'react'
import { PageHeader, Tabs, Spinner, Card, Badge, Table } from '@/components/ui'
import { getChatFiles } from '@/temp/school-data'
import type { ChatFile } from '@/types'
import { useChat, type ChatTab } from './useChat'

const TABS: ChatTab[] = ['Conversations', 'Groups', 'Files']

const totalTone = (n: number) => (n === 0 ? 'green' : 'red')

export default function ChatPage() {
  const c = useChat()
  const [files, setFiles] = useState<ChatFile[]>([])

  useEffect(() => {
    let alive = true
    getChatFiles().then((f) => {
      if (alive) setFiles(f)
    })
    return () => {
      alive = false
    }
  }, [])

  const fileCols = [
    { key: 'name', header: 'File', render: (f: ChatFile) => <b>{f.name}</b> },
    { key: 'sharedBy', header: 'Shared by' },
    { key: 'size', header: 'Size' },
    { key: 'when', header: 'When' },
  ]

  return (
    <div>
      <PageHeader title="Chat & Communication" subtitle="Direct and group conversations with students, parents and colleagues." />

      {c.loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-tiles">
            <div className="stat-tile"><b>{c.conversations.length}</b><span>Conversations</span></div>
            <div className="stat-tile"><b>{c.unreadTotal}</b><span>Unread</span></div>
            <div className="stat-tile"><b>{c.onlineCount}</b><span>Online</span></div>
          </div>

          <Tabs tabs={TABS} active={c.tab} onChange={(t) => c.setTab(t as ChatTab)} />

          {c.tab === 'Files' ? (
            <Table columns={fileCols} rows={files} rowKey={(f) => f.id} empty="No files shared yet." />
          ) : c.filtered.length === 0 ? (
            <div className="empty-state">No conversations here yet.</div>
          ) : (
            <div style={{ display: 'grid', gap: '0.6rem' }}>
              {c.filtered.map((conv) => (
                <Card key={conv.id}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                        <b>{conv.name}</b>
                        {conv.group ? <Badge tone="violet">Group</Badge> : conv.online ? <Badge tone="green">online</Badge> : null}
                      </div>
                      <p style={{ color: 'var(--muted)', fontSize: '0.85rem', margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{conv.lastMessage}</p>
                    </div>
                    <div style={{ textAlign: 'right', display: 'grid', gap: '0.3rem', justifyItems: 'end' }}>
                      <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>{conv.time}</span>
                      {conv.unread > 0 && <Badge tone="red">{conv.unread} new</Badge>}
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}