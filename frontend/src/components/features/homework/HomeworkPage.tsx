'use client'
import { useState } from 'react'
import { PageHeader, Tabs, Input, Spinner } from '@/components/ui'
import { useHomework, type HomeworkTab } from './useHomework'
import AssignHomework from './AssignHomework'
import SubmissionsReview from './SubmissionsReview'
import ClassDiary from './ClassDiary'

const TABS: HomeworkTab[] = ['Assign Homework', 'Submissions & Review', 'Class Diary']

export default function HomeworkPage() {
  const [tab, setTab] = useState<HomeworkTab>('Assign Homework')
  const h = useHomework()

  return (
    <div>
      <PageHeader title="Homework & Class Diary" subtitle="Assign homework, review submissions and manage the class diary." />

      {h.loading ? (
        <Spinner />
      ) : (
        <>
          <div className="stat-tiles">
            <div className="stat-tile"><b>{h.homeworks.length}</b><span>Active Tasks</span></div>
            <div className="stat-tile"><b>{h.submittedCount}</b><span>Submitted</span></div>
            <div className="stat-tile"><b>{h.pendingCount}</b><span>Pending</span></div>
            <div className="stat-tile"><b>{h.diary.length}</b><span>Diary Days</span></div>
          </div>

          <Tabs tabs={TABS} active={tab} onChange={(t) => setTab(t as HomeworkTab)} />

          {tab === 'Assign Homework' && <AssignHomework />}

          {(tab === 'Submissions & Review' || tab === 'Class Diary') && (
            <div className="toolbar">
              <div className="toolbar-search">
                <Input placeholder={tab === 'Class Diary' ? 'Search diary by topic or subject…' : 'Search student or homework…'} value={h.query} onChange={(e) => h.setQuery(e.target.value)} />
              </div>
            </div>
          )}

          {tab === 'Submissions & Review' && <SubmissionsReview rows={h.filteredSubmissions} />}
          {tab === 'Class Diary' && <ClassDiary rows={h.diary.filter((d) => !h.query || d.topic.toLowerCase().includes(h.query.toLowerCase()) || d.subject.toLowerCase().includes(h.query.toLowerCase()))} />}
        </>
      )}
    </div>
  )
}