'use client'
import { Card, Button, Badge } from '@/components/ui'
import type { ClassroomItem } from '@/types'

export default function MyClasses({ rows }: { rows: ClassroomItem[] }) {
  return (
    <div className="kpi-grid">
      {rows.map((c) => (
        <Card key={c.id} title={c.className} action={<Badge tone="accent">{c.subject}</Badge>}>
          <div style={{ display: 'grid', gap: '0.4rem', color: 'var(--muted)', fontSize: '0.88rem' }}>
            <div><b style={{ color: 'var(--text)' }}>{c.title}</b></div>
            <div>Teacher: {c.teacher}</div>
            <div>Students: {c.students}</div>
            <div>Next: {c.nextLesson}</div>
          </div>
          <div className="modal-actions" style={{ marginTop: '0.9rem' }}>
            <Button variant="outline" size="sm">Open Class</Button>
          </div>
        </Card>
      ))}
    </div>
  )
}