'use client'

import { useEffect, useState } from 'react'
import type { Student, ClassMatrixRow } from '@/types'
import { Button, PageHeader, Select, Spinner, Table, Tabs } from '@/components/ui'
import { useToast } from '@/components/ui/toast'
import Icon from '@/components/ui/Icon'
import { getClassMatrix } from '@/db_demo/school-data'
import { useStudents } from './useStudents'
import StudentTable from './StudentTable'
import StudentFormModal from './StudentFormModal'
import StudentProfileModal from './StudentProfileModal'

// Students master data — container (stitch: students_master_data_desktop).
export default function StudentsPage() {
  const toast = useToast()
  const {
    students, filtered, classes,
    query, setQuery,
    classFilter, setClassFilter,
    statusFilter, setStatusFilter,
    nextAdmissionNo, toForm,
    addStudent, updateStudent, toggleStatus,
  } = useStudents()

  const [editing, setEditing] = useState<Student | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [profile, setProfile] = useState<Student | null>(null)
  const [view, setView] = useState<'Directory' | 'Class Matrix'>('Directory')
  const [matrix, setMatrix] = useState<ClassMatrixRow[]>([])

  useEffect(() => {
    let alive = true
    getClassMatrix().then((m) => {
      if (alive) setMatrix(m)
    })
    return () => {
      alive = false
    }
  }, [])

  if (!students) return <Spinner />

  // stitch stat tiles (SVG icons, no emoji)
  const stats = [
    { icon: 'groups' as const, label: 'Total Students', value: String(students.length) },
    { icon: 'guardian' as const, label: 'Guardians', value: String(new Set(students.map((s) => s.guardian)).size) },
    { icon: 'school' as const, label: 'Classes', value: String(classes.length) },
    { icon: 'active' as const, label: 'Active', value: String(students.filter((s) => s.status === 'Active').length) },
  ]

  function handleEdit(s: Student) {
    setEditing(s)
    setFormOpen(true)
  }

  function handleSubmit(values: Parameters<typeof addStudent>[0]) {
    if (editing) {
      updateStudent(editing.id, values)
      toast.push('success', `${values.name} updated`)
    } else {
      addStudent(values)
      toast.push('success', `${values.name} admitted 🎉`)
    }
    setFormOpen(false)
    setEditing(null)
  }

  function handleToggle(s: Student) {
    toggleStatus(s)
    toast.push('info', `${s.name} marked ${s.status === 'Active' ? 'Inactive' : 'Active'}`)
  }

  return (
    <div className="page">
      <PageHeader
        title="Students Directory"
        subtitle={`${filtered.length} of ${students.length} students`}
        actions={
          <>
            <Button variant="outline" size="sm" icon="⬇">Download CSV</Button>
            <Button icon="＋" onClick={() => { setEditing(null); setFormOpen(true) }}>
              Add student
            </Button>
          </>
        }
      />

      <Tabs tabs={['Directory', 'Class Matrix']} active={view} onChange={(v) => setView(v as typeof view)} />

      {/* stat tiles */}
      <div className="kpi-grid" style={{ marginBottom: '1.2rem' }}>
        {stats.map((st) => (
          <div key={st.label} className="stat">
            <span className="stat-ico"><Icon name={st.icon} size={20} /></span>
            <div className="stat-value">{st.value}</div>
            <div className="stat-label">{st.label}</div>
          </div>
        ))}
      </div>

      {view === 'Class Matrix' ? (
        <Table
          columns={[
            { key: 'className', header: 'Class', render: (r: ClassMatrixRow) => <b>{r.className}</b> },
            { key: 'strength', header: 'Strength' },
            { key: 'boys', header: 'Boys' },
            { key: 'girls', header: 'Girls' },
            { key: 'avgAttendance', header: 'Avg attendance', render: (r: ClassMatrixRow) => `${r.avgAttendance}%` },
          ]}
          rows={matrix}
          rowKey={(r) => r.id}
          empty="No classes yet."
        />
      ) : (
        <>
      <div className="toolbar">
        <div className="toolbar-search">
          <input className="input" placeholder="Search name, admission no, guardian…"
            value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        <Select value={classFilter} onChange={(e) => setClassFilter(e.target.value)} aria-label="Filter by class">
          <option value="all">All classes</option>
          {classes.map((c) => <option key={c} value={c}>Class {c}</option>)}
        </Select>
        <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} aria-label="Filter by status">
          <option value="all">All statuses</option>
          <option value="Active">Active</option>
          <option value="Inactive">Inactive</option>
        </Select>
      </div>

      <StudentTable rows={filtered} onView={setProfile} onEdit={handleEdit} onToggleStatus={handleToggle} />
        </>
      )}

      <StudentFormModal
        open={formOpen}
        editing={editing}
        defaultAdmissionNo={nextAdmissionNo()}
        onClose={() => { setFormOpen(false); setEditing(null) }}
        onSubmit={handleSubmit}
      />

      <StudentProfileModal student={profile} onClose={() => setProfile(null)} />
    </div>
  )
}