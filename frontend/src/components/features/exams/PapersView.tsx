'use client'
import { Table, Badge, type BadgeTone } from '@/components/ui'
import type { PaperDraftFull, PaperReviewItem } from '@/types'

const statusTone: Record<PaperDraftFull['status'], BadgeTone> = { Draft: 'amber', Submitted: 'accent', Approved: 'green' }

export default function PapersView({ papers, reviews }: { papers: PaperDraftFull[]; reviews: PaperReviewItem[] }) {
  const cols = [
    { key: 'title', header: 'Paper', render: (r: PaperDraftFull) => <b>{r.title}</b> },
    { key: 'subject', header: 'Subject' },
    { key: 'questions', header: 'Questions' },
    { key: 'totalMarks', header: 'Marks' },
    { key: 'status', header: 'Status', render: (r: PaperDraftFull) => <Badge tone={statusTone[r.status]}>{r.status}</Badge> },
    { key: 'updated', header: 'Updated' },
  ]
  return (
    <div style={{ display: 'grid', gap: '1rem' }}>
      <Table columns={cols} rows={papers} rowKey={(r) => r.id} empty="No papers yet." />
      <div className="card">
        <div className="card-head"><h3>Pending Reviews</h3></div>
        <div className="card-body">
          {reviews.length === 0 ? (
            <p style={{ color: 'var(--muted)' }}>Nothing awaiting review.</p>
          ) : (
            <ul style={{ display: 'grid', gap: '0.5rem', padding: 0, listStyle: 'none' }}>
              {reviews.map((r) => (
                <li key={r.id} style={{ display: 'flex', justifyContent: 'space-between', gap: '0.5rem' }}>
                  <span>{r.title} <span style={{ color: 'var(--muted)', fontSize: '0.8rem' }}>({r.subject} · {r.author})</span></span>
                  <Badge tone="red">{r.due}</Badge>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}