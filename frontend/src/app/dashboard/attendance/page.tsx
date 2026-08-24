'use client'

import { useEffect, useMemo, useState } from 'react'
import { getAttendance, getStudents } from '@/temp/school-data'
import type { AttendanceRecord, Student } from '@/types'
import {
  Badge,
  Button,
  PageHeader,
  Select,
  Spinner,
  Table,
  Tabs,
  type Column,
} from '@/components/ui'
import { useToast } from '@/components/ui/toast'

// ============================================================
// PAGE 05 — Attendance (stitch: attendance_management_desktop)
// Tab 1: mark-attendance roster grid (per-student status)
// Tab 2: history table with filters
// Mock data from @/temp — replaced by backend API later.
// ============================================================

const STATUSES = ['Present', 'Absent', 'Late', 'Leave'] as const
type Status = (typeof STATUSES)[number]

const STATUS_TONE = { Present: 'green', Absent: 'red', Late: 'amber', Leave: 'violet' } as const

export default function AttendancePage() {
  const toast = useToast()
  const [tab, setTab] = useState('Mark attendance')
  const [students, setStudents] = useState<Student[] | null>(null)
  const [history, setHistory] = useState<AttendanceRecord[]>([])
  const [className, setClassName] = useState('10')
  const [section, setSection] = useState('A')
  const [date, setDate] = useState('') // set after mount (avoids SSR/client timezone mismatch)
  const [marks, setMarks] = useState<Record<number, Status>>({})
  const [statusFilter, setStatusFilter] = useState('all')

  useEffect(() => {
    setDate(new Date().toISOString().slice(0, 10))
    void Promise.all([getStudents(), getAttendance()]).then(([s, a]) => {
      setStudents(s)
      setHistory(a)
    })
  }, [])

  const roster = useMemo(
    () => (students ?? []).filter((s) => s.className === className && s.section === section),
    [students, className, section],
  )

  function setAll(status: Status) {
    setMarks(Object.fromEntries(roster.map((s) => [s.id, status])))
  }

  function saveAttendance() {
    if (roster.length === 0) return
    const records: AttendanceRecord[] = roster.map((s, i) => ({
      id: Date.now() + i,
      studentName: s.name,
      className: `${s.className}-${s.section}`,
      date,
      status: marks[s.id] ?? 'Present',
    }))
    setHistory((prev) => [...records, ...prev])
    setMarks({})
    const present = records.filter((r) => r.status === 'Present').length
    toast.push('success', `Saved · ${present}/${records.length} present on ${date}`)
  }

  const historyColumns: Column<AttendanceRecord>[] = [
    { key: 'date', header: 'Date' },
    { key: 'studentName', header: 'Student', render: (r) => <strong>{r.studentName}</strong> },
    { key: 'className', header: 'Class' },
    {
      key: 'status',
      header: 'Status',
      render: (r) => <Badge tone={STATUS_TONE[r.status]}>{r.status}</Badge>,
    },
  ]

  const marked = roster.filter((s) => marks[s.id]).length

  const filteredHistory = useMemo(
    () =>
      history.filter((r) => {
        if (statusFilter !== 'all' && r.status !== statusFilter) return false
        if (className !== 'all' && !r.className.startsWith(className)) return false
        return true
      }),
    [history, statusFilter, className],
  )

  return (
    <div className="page">
      <PageHeader
        title="Attendance"
        subtitle="Mark and track daily attendance for your classes"
        actions={
          tab === 'Mark attendance' && (
            <Button icon="💾" onClick={saveAttendance} disabled={marked === 0}>
              Save ({marked}/{roster.length})
            </Button>
          )
        }
      />

      <Tabs tabs={['Mark attendance', 'History']} active={tab} onChange={setTab} />

      {/* shared filters */}
      <div className="toolbar">
        <Select value={className} onChange={(e) => setClassName(e.target.value)} aria-label="Class">
          <option value="all">All classes</option>
          {[...new Set((students ?? []).map((s) => s.className))].sort().map((c) => (
            <option key={c} value={c}>Class {c}</option>
          ))}
        </Select>

        {tab === 'Mark attendance' ? (
          <>
            <Select value={section} onChange={(e) => setSection(e.target.value)} aria-label="Section">
              {['A', 'B', 'C', 'D'].map((sec) => <option key={sec} value={sec}>Section {sec}</option>)}
            </Select>
            <input className="input" type="date" style={{ width: 'auto' }} value={date}
              onChange={(e) => setDate(e.target.value)} aria-label="Date" />
          </>
        ) : (
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Status">
            <option value="all">All statuses</option>
            {STATUSES.map((st) => <option key={st} value={st}>{st}</option>)}
          </Select>
        )}
      </div>

      {!students ? (
        <Spinner />
      ) : tab === 'Mark attendance' ? (
        roster.length === 0 ? (
          <p style={{ color: 'var(--muted)' }}>No students in Class {className}-{section}. Add students first.</p>
        ) : (
          <div className="roster">
            <div className="roster-actions">
              <Button size="sm" variant="success" onClick={() => setAll('Present')}>✓ Mark all present</Button>
              <Button size="sm" variant="ghost" onClick={() => setMarks({})}>Reset</Button>
            </div>
            {roster.map((s) => (
              <div key={s.id} className="roster-row">
                <span className="cell-avatar">{initials(s.name)}</span>
                <span className="roster-name">
                  <strong>{s.name}</strong>
                  <span style={{ color: 'var(--muted)', fontSize: '0.76rem' }}>{s.admissionNo}</span>
                </span>
                <div className="roster-status" role="radiogroup" aria-label={`Attendance for ${s.name}`}>
                  {STATUSES.map((st) => (
                    <button
                      key={st}
                      type="button"
                      role="radio"
                      aria-checked={marks[s.id] === st}
                      className={`chip chip-${(marks[s.id] ?? '').toLowerCase()}${marks[s.id] === st ? ' chip-on' : ''}`}
                      onClick={() => setMarks((prev) => ({ ...prev, [s.id]: st }))}
                    >
                      {st}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        <Table columns={historyColumns} rows={filteredHistory} rowKey={(r) => r.id}
          empty="No attendance records yet." />
      )}
    </div>
  )
}

function initials(name: string) {
  return name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()
}
