'use client'

import { useState } from 'react'
import { Button, PageHeader, Select, Spinner, Tabs } from '@/components/ui'
import { useToast } from '@/components/ui/toast'
import { useAcademics } from './useAcademics'
import MarksEntryTab from './MarksEntryTab'
import GradebookTab from './GradebookTab'

// PAGE 05 — Academics & Marks. Container: tabs + shared filters.
export default function AcademicsPage() {
  const toast = useToast()
  const ac = useAcademics()
  const [tab, setTab] = useState<'Marks entry' | 'Gradebook'>('Marks entry')

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

      <Tabs tabs={['Marks entry', 'Gradebook']} active={tab} onChange={(t) => setTab(t as typeof tab)} />

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
      ) : (
        <GradebookTab entries={ac.entries} />
      )}
    </div>
  )
}