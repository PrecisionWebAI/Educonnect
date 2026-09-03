'use client'
import { useState } from 'react'
import { PageHeader, Tabs, Input, Select, Spinner, Button } from '@/components/ui'
import { useExams, type ExamsTab } from './useExams'
import AiPaperGenerator from './AiPaperGenerator'
import QuestionBank from './QuestionBank'
import PapersView from './PapersView'
import ConductMarking from './ConductMarking'
import ScheduleSeating from './ScheduleSeating'

const TABS: ExamsTab[] = ['AI Paper Generator', 'Question Bank', 'My Papers', 'Conduct & Marking', 'Schedule & Seating']

export default function ExamsPage() {
  const [tab, setTab] = useState<ExamsTab>('AI Paper Generator')
  const e = useExams()

  return (
    <div>
      <PageHeader
        title="Exams & AI Papers"
        subtitle="Generate question papers with AI, manage question bank, conduct & schedule."
        actions={<Button variant="primary">+ New Paper</Button>}
      />

      {e.loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-tiles">
            <div className="stat-tile"><b>{e.questions.length}</b><span>Bank Questions</span></div>
            <div className="stat-tile"><b>{e.questionTypes.length}</b><span>Question Types</span></div>
            <div className="stat-tile"><b>{e.papers.length}</b><span>Drafts / Papers</span></div>
            <div className="stat-tile"><b>{e.schedule.length}</b><span>Exams Scheduled</span></div>
          </div>

          <Tabs tabs={TABS} active={tab} onChange={(t) => setTab(t as ExamsTab)} />

          {tab === 'AI Paper Generator' && <AiPaperGenerator />}

          {tab === 'Question Bank' && (
            <>
              <div className="toolbar">
                <div className="toolbar-search">
                  <Input placeholder="Search question or chapter…" value={e.query} onChange={(ev) => e.setQuery(ev.target.value)} />
                </div>
                <Select value={e.subject} onChange={(ev) => e.setSubject(ev.target.value)}>
                  {e.subjects.map((s) => <option key={s} value={s}>{s}</option>)}
                </Select>
              </div>
              <QuestionBank rows={e.filteredQuestions} />
            </>
          )}

          {tab === 'My Papers' && <PapersView papers={e.papers} reviews={e.reviews} />}
          {tab === 'Conduct & Marking' && <ConductMarking rows={e.markings} />}
          {tab === 'Schedule & Seating' && <ScheduleSeating rows={e.schedule} />}
        </>
      )}
    </div>
  )
}