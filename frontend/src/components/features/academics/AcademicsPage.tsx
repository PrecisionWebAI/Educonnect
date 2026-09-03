'use client'

import { useEffect, useState } from 'react'
import { Badge, Button, PageHeader, Select, Spinner, Table, Tabs } from '@/components/ui'
import { useToast } from '@/components/ui/toast'
import { getResults, getDisputes } from '@/temp/school-data'
import type { ResultRow, DisputeRow } from '@/types'
import { useAcademics } from './useAcademics'
import MarksEntryTab from './MarksEntryTab'
import GradebookTab from './GradebookTab'

// PAGE 05 — Academics & Marks. Container: tabs + shared filters.
export default function AcademicsPage() {
  const toast = useToast()
  const ac = useAcademics()
  const [tab, setTab] = useState<'Marks entry' | 'Gradebook' | 'Results & Analytics' | 'Marks Dispute'>('Marks entry')
  const [results, setResults] = useState<ResultRow[]>([])
  const [disputes, setDisputes] = useState<DisputeRow[]>([])

  useEffect(() => {
    let alive = true
    Promise.all([getResults(), getDisputes()]).then(([rs, ds]) => {
      if (!alive) return
      setResults(rs)
      setDisputes(ds)
    })
    return () => {
      alive = false
    }
  }, [])

  function handleSave() {
    // Mock save — scores already live in state; backend will POST here.
    toast.push('success', `Marks saved for ${ac.entries.length} students`)
  }

  return (
    <div className="page">
      <PageHeader
        title="Academics & Marks"
        subtitle="Spreadsheet-grade marks entry and gradebook"
        actions={tab === 'Marks entry' && <Button onClick={handleSave}>Save marks</Button>}
      />

      <Tabs tabs={['Marks entry', 'Gradebook', 'Results & Analytics', 'Marks Dispute']} active={tab} onChange={(t) => setTab(t as typeof tab)} />

      <div className="toolbar">
        <Select value={ac.exam} onChange={(e) => ac.setExam(e.target.value)} aria-label="Exam">
          <option value="all">All exams</option>
          {ac.exams.map((x) => <option key={x} value={x}>{x}</option>)}
        </Select>
        <Select value={ac.className} onChange={(e) => ac.setClassName(e.target.value)} aria-label="Class">
          <option value="all">All classes</option>
          {ac.classNames.map((c) => <option key={c} value={c}>{c}</option>)}
        </Select>
      </div>

      {ac.loading ? (
        <Spinner />
      ) : tab === 'Marks entry' ? (
        <MarksEntryTab entries={ac.entries} subjects={ac.subjects} onScoreChange={ac.updateScore} />
      ) : tab === 'Gradebook' ? (
        <GradebookTab entries={ac.entries} />
      ) : tab === 'Results & Analytics' ? (
        <Table
          columns={[
            { key: 'exam', header: 'Exam', render: (r: ResultRow) => <b>{r.exam}</b> },
            { key: 'className', header: 'Class' },
            { key: 'passRate', header: 'Pass rate', render: (r: ResultRow) => `${r.passRate}%` },
            { key: 'avgScore', header: 'Avg score', render: (r: ResultRow) => `${r.avgScore}%` },
            { key: 'topper', header: 'Topper' },
          ]}
          rows={results}
          rowKey={(r) => r.id}
          empty="No exam results yet."
        />
      ) : (
        <>
          <p style={{ color: 'var(--muted)', marginBottom: '0.6rem' }}>
            Students can challenge marks; disputes route to the subject teacher, then HOD.
          </p>
          <Table
            columns={[
              { key: 'student', header: 'Student', render: (r: DisputeRow) => <b>{r.student}</b> },
              { key: 'exam', header: 'Exam' },
              { key: 'subject', header: 'Subject' },
              { key: 'reason', header: 'Reason' },
              { key: 'status', header: 'Status', render: (r: DisputeRow) => <Badge tone={r.status === 'Resolved' ? 'green' : r.status === 'Open' ? 'red' : 'amber'}>{r.status}</Badge> },
            ]}
            rows={disputes}
            rowKey={(r) => r.id}
            empty="No mark disputes."
          />
        </>
      )}
    </div>
  )
}