'use client'

import { useEffect, useState } from 'react'
import { getPaperReviews, getQbHealth, getSubjectPerf } from '@/db_demo/school-data'
import type { PaperReviewItem, QbHealthItem, SubjectPerf } from '@/types'
import { Badge, Button, Card, PageHeader, Spinner } from '@/components/ui'
import { useToast } from '@/components/ui/toast'

// Tab D.3 — HOD Academic Dashboard (purple)
export default function HodDashboard() {
  const toast = useToast()
  const [perf, setPerf] = useState<SubjectPerf[]>([])
  const [qb, setQb] = useState<QbHealthItem[]>([])
  const [papers, setPapers] = useState<PaperReviewItem[]>([])
  const [ready, setReady] = useState(false)

  useEffect(() => {
    void Promise.all([getSubjectPerf(), getQbHealth(), getPaperReviews()]).then(([p, q, pr]) => {
      setPerf(p); setQb(q); setPapers(pr); setReady(true)
    })
  }, [])

  if (!ready) return <Spinner />

  return (
    <div className="page">
      <PageHeader title="Academic HOD Overview" subtitle="Science department" />

      <div className="dash-grid">
        <Card title="Subject Performance" className="dash-span-2">
          <div className="feed">
            {perf.map((p) => (
              <li key={p.subject + p.className} className="feed-item">
                <div className="feed-body">
                  <span className="feed-title">{p.subject} · {p.className}</span>
                  <span className="feed-sub">Avg {p.average}% — weak topic: {p.weakTopic}</span>
                </div>
                <Badge tone={p.average >= 85 ? 'green' : p.average >= 75 ? 'teal' : 'amber'}>{p.average}%</Badge>
              </li>
            ))}
          </div>
        </Card>

        <Card title="Question-Bank Health">
          <ul className="feed">
            {qb.map((q) => (
              <li key={q.subject} className="feed-item">
                <Badge tone={q.flagged ? 'red' : 'green'}>{q.flagged ? 'Needs work' : 'Healthy'}</Badge>
                <div className="feed-body">
                  <span className="feed-title">{q.subject}</span>
                  <span className="feed-sub">{q.mcq} MCQ · {q.theory} theory</span>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Paper Review Queue" className="dash-span-2">
          {papers.length === 0 ? (
            <p style={{ color: 'var(--muted)' }}>No papers awaiting review.</p>
          ) : (
            <ul className="feed">
              {papers.map((p) => (
                <li key={p.id} className="feed-item">
                  <div className="feed-body">
                    <span className="feed-title">{p.title}</span>
                    <span className="feed-sub">{p.author} · due {p.due}</span>
                  </div>
                  <Button size="sm" variant="success" onClick={() => { setPapers((x) => x.filter((y) => y.id !== p.id)); toast.push('success', 'Paper approved') }}>Approve</Button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  )
}