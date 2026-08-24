'use client'

import { useEffect, useMemo, useState } from 'react'
import { getStudents } from '@/temp/school-data'
import type { Student } from '@/types'
import {
  Badge,
  Button,
  Input,
  Modal,
  PageHeader,
  Select,
  Spinner,
  Table,
  type Column,
} from '@/components/ui'
import { useToast } from '@/components/ui/toast'

// ============================================================
// PAGE 04 — Students Master Data (stitch: students_master_data)
// List + search + filters + Add/Edit modal + profile modal.
// ============================================================

const EMPTY_FORM = {
  name: '',
  admissionNo: '',
  className: '10',
  section: 'A',
  gender: 'Male' as Student['gender'],
  guardian: '',
  phone: '',
  email: '',
}

export default function StudentsPage() {
  const toast = useToast()
  const [students, setStudents] = useState<Student[] | null>(null)
  const [query, setQuery] = useState('')
  const [classFilter, setClassFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [editing, setEditing] = useState<Student | null>(null)
  const [formOpen, setFormOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [profile, setProfile] = useState<Student | null>(null)

  useEffect(() => {
    void getStudents().then(setStudents)
  }, [])

  const classes = useMemo(
    () => Array.from(new Set((students ?? []).map((s) => s.className))).sort(),
    [students],
  )

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return (students ?? []).filter((s) => {
      if (q && !`${s.name} ${s.admissionNo} ${s.guardian}`.toLowerCase().includes(q)) return false
      if (classFilter !== 'all' && s.className !== classFilter) return false
      if (statusFilter !== 'all' && s.status !== statusFilter) return false
      return true
    })
  }, [students, query, classFilter, statusFilter])

  function nextAdmissionNo() {
    const nums = (students ?? [])
      .map((s) => Number.parseInt(s.admissionNo.split('-').pop() ?? '0', 10))
      .filter((n) => !Number.isNaN(n))
    const next = (nums.length ? Math.max(...nums) : 0) + 1
    return `EV-2026-${String(next).padStart(3, '0')}`
  }

  function openAdd() {
    setEditing(null)
    setForm({ ...EMPTY_FORM, admissionNo: nextAdmissionNo() })
    setFormOpen(true)
  }

  function openEdit(s: Student) {
    setEditing(s)
    setForm({
      name: s.name, admissionNo: s.admissionNo, className: s.className,
      section: s.section, gender: s.gender, guardian: s.guardian,
      phone: s.phone, email: s.email,
    })
    setFormOpen(true)
  }

  function saveStudent(e: React.FormEvent) {
    e.preventDefault()
    if (editing) {
      setStudents((prev) => (prev ?? []).map((s) => (s.id === editing.id ? { ...s, ...form } : s)))
      toast.push('success', `${form.name} updated`)
    } else {
      const newStudent: Student = { id: Date.now(), ...form, status: 'Active' }
      setStudents((prev) => [newStudent, ...(prev ?? [])])
      toast.push('success', `${form.name} admitted 🎉`)
    }
    setFormOpen(false)
  }

  function toggleStatus(s: Student) {
    setStudents((prev) =>
      (prev ?? []).map((x) =>
        x.id === s.id ? { ...x, status: x.status === 'Active' ? 'Inactive' : 'Active' } : x,
      ),
    )
    toast.push('info', `${s.name} marked ${s.status === 'Active' ? 'Inactive' : 'Active'}`)
  }

  const columns: Column<Student>[] = [
    {
      key: 'name',
      header: 'Student',
      render: (s) => (
        <button type="button" className="cell-name" title="View profile"
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'inherit', padding: 0 }}
          onClick={() => setProfile(s)}>
          <span className="cell-avatar">{initials(s.name)}</span>
          <span>
            <strong>{s.name}</strong>
            <br />
            <span style={{ color: 'var(--muted)', fontSize: '0.78rem' }}>{s.admissionNo}</span>
          </span>
        </button>
      ),
    },
    { key: 'className', header: 'Class', render: (s) => `${s.className}-${s.section}` },
    { key: 'gender', header: 'Gender' },
    { key: 'guardian', header: 'Guardian' },
    { key: 'phone', header: 'Contact' },
    {
      key: 'status',
      header: 'Status',
      render: (s) => <Badge tone={s.status === 'Active' ? 'green' : 'muted'}>{s.status}</Badge>,
    },
    {
      key: 'actions',
      header: '',
      align: 'right',
      render: (s) => (
        <span style={{ display: 'inline-flex', gap: '0.4rem' }}>
          <Button size="sm" variant="outline" onClick={() => openEdit(s)}>Edit</Button>
          <Button size="sm" variant="ghost" onClick={() => toggleStatus(s)}>
            {s.status === 'Active' ? 'Deactivate' : 'Activate'}
          </Button>
        </span>
      ),
    },
  ]

  if (!students) return <Spinner />

  return (
    <div className="page">
      <PageHeader title="Students" subtitle={`${filtered.length} of ${students.length} students`}
        actions={<Button icon="＋" onClick={openAdd}>Add student</Button>} />

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

      <Table columns={columns} rows={filtered} rowKey={(s) => s.id} empty="No students match your filters." />

      {/* Add / Edit modal */}
      <Modal open={formOpen} title={editing ? `Edit — ${editing.name}` : 'Add new student'}
        onClose={() => setFormOpen(false)}>
        <form onSubmit={saveStudent}>
          <div className="form-grid">
            <Input label="Full name" id="f-name" value={form.name} required onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Input label="Admission no" id="f-adm" value={form.admissionNo} disabled hint="Auto-generated" />
            <Select label="Class" id="f-class" value={form.className} onChange={(e) => setForm({ ...form, className: e.target.value })}>
              {['6', '7', '8', '9', '10', '11', '12'].map((c) => <option key={c} value={c}>{c}</option>)}
            </Select>
            <Select label="Section" id="f-sec" value={form.section} onChange={(e) => setForm({ ...form, section: e.target.value })}>
              {['A', 'B', 'C', 'D'].map((sec) => <option key={sec} value={sec}>{sec}</option>)}
            </Select>
            <Select label="Gender" id="f-gen" value={form.gender} onChange={(e) => setForm({ ...form, gender: e.target.value as Student['gender'] })}>
              <option>Male</option>
              <option>Female</option>
            </Select>
            <Input label="Guardian" id="f-guard" value={form.guardian} required onChange={(e) => setForm({ ...form, guardian: e.target.value })} />
            <Input label="Phone" id="f-phone" value={form.phone} required onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            <Input label="Email" id="f-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          </div>
          <div className="modal-actions">
            <Button type="button" variant="ghost" onClick={() => setFormOpen(false)}>Cancel</Button>
            <Button type="submit">{editing ? 'Save changes' : 'Add student'}</Button>
          </div>
        </form>
      </Modal>

      {/* Profile modal */}
      <Modal open={profile !== null} title="Student profile" onClose={() => setProfile(null)}>
        {profile && (
          <>
            <div className="cell-name" style={{ marginBottom: '1rem' }}>
              <span className="cell-avatar" style={{ width: 44, height: 44, fontSize: '1rem' }}>{initials(profile.name)}</span>
              <div>
                <strong style={{ fontSize: '1.05rem' }}>{profile.name}</strong>
                <div style={{ color: 'var(--muted)', fontSize: '0.82rem' }}>{profile.admissionNo}</div>
                <Badge tone={profile.status === 'Active' ? 'green' : 'muted'}>{profile.status}</Badge>
              </div>
            </div>
            <dl style={{ display: 'grid', gap: '0.45rem', color: 'var(--muted)', fontSize: '0.9rem' }}>
              <div><b style={{ color: 'var(--text)' }}>Class:</b> {profile.className}-{profile.section}</div>
              <div><b style={{ color: 'var(--text)' }}>Guardian:</b> {profile.guardian}</div>
              <div><b style={{ color: 'var(--text)' }}>Phone:</b> {profile.phone}</div>
              <div><b style={{ color: 'var(--text)' }}>Email:</b> {profile.email || '—'}</div>
            </dl>
          </>
        )}
      </Modal>
    </div>
  )
}

function initials(name: string) {
  return name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()
}
