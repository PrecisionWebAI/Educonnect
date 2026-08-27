'use client'

import { useEffect, useMemo, useState } from 'react'
import { getTeachers, getTimetable } from '@/temp/school-data'
import type { Teacher, TimetableSlot } from '@/types'
import { Badge, Button, Input, PageHeader, Select, Spinner } from '@/components/ui'
import { useToast } from '@/components/ui/toast'

// ============================================================
// PAGE 06 — Timetable (stitch: timetable_scheduling_desktop)
// Weekly color-coded grid Mon–Sat × P1–P6 + edit mode.
// ============================================================

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const PERIODS = ['P1', 'P2', 'P3', 'P4', 'P5', 'P6']
const COLORS = ['tt-c0', 'tt-c1', 'tt-c2', 'tt-c3', 'tt-c4', 'tt-c5', 'tt-c6']

function colorFor(subject: string) {
  let h = 0
  for (let i = 0; i < subject.length; i++) h = (h * 31 + subject.charCodeAt(i)) >>> 0
  return COLORS[h % COLORS.length]
}

export default function TimetablePage() {
  const toast = useToast()
  const [slots, setSlots] = useState<TimetableSlot[] | null>(null)
  const [teachers, setTeachers] = useState<Teacher[]>([])
  const [className, setClassName] = useState('all')
  const [editing, setEditing] = useState(false)
  const [selected, setSelected] = useState<{ day: string; period: string } | null>(null)
  const [draft, setDraft] = useState({ subject: '', teacher: '' })

  useEffect(() => {
    void Promise.all([getTimetable(), getTeachers()]).then(([t, th]) => {
      setSlots(t)
      setTeachers(th)
    })
  }, [])

  const classes = useMemo(() => Array.from(new Set((slots ?? []).map((s) => s.className))), [slots])
  const subjects = useMemo(
    () => Array.from(new Set((teachers ?? []).map((t) => t.subject))).sort(),
    [teachers],
  )

  /** Find the slot for a grid cell (respecting the class filter). */
  function findSlot(day: string, period: string): TimetableSlot | undefined {
    return (slots ?? []).find(
      (s) => s.day === day && s.period === period && (className === 'all' || s.className === className),
    )
  }

  /** Assign or clear a cell (scoped to the selected class). */
  function assignSlot(day: string, period: string, value: { subject: string; teacher: string } | null) {
    const cls = className === 'all' ? classes[0] : className
    if (!cls) return
    setSlots((prev) => {
      const rest = (prev ?? []).filter(
        (s) => !(s.day === day && s.period === period && s.className === cls),
      )
      return value ? [...rest, { day, period, className: cls, ...value }] : rest
    })
  }

  /** Warn when the same teacher is already teaching another class in that slot. */
  function clashWarning(day: string, period: string): string | null {
    if (!draft.teacher) return null
    const busy = (slots ?? []).find(
      (s) => s.day === day && s.period === period && s.teacher === draft.teacher,
    )
    return busy ? `${busy.teacher} already teaches ${busy.className} at ${day} ${period}` : null
  }

  function saveDraft() {
    if (!selected) return
    if (!draft.subject || !draft.teacher) {
      toast.push('error', 'Subject and teacher both required')
      return
    }
    assignSlot(selected.day, selected.period, draft)
    toast.push('success', `${selected.day} ${selected.period} → ${draft.subject}`)
    setSelected(null)
  }

  if (!slots) return <Spinner />

  const clash = selected ? clashWarning(selected.day, selected.period) : null

  return (
    <div className="page">
      <PageHeader
        title="Timetable"
        subtitle="Weekly class schedule — click any cell in edit mode"
        actions={
          <Button variant={editing ? 'success' : 'outline'} icon={editing ? '✓' : '✏️'}
            onClick={() => { setEditing((v) => !v); setSelected(null) }}>
            {editing ? 'Done editing' : 'Edit timetable'}
          </Button>
        }
      />

      <div className="toolbar">
        <Select value={className} onChange={(e) => setClassName(e.target.value)} aria-label="Class">
          <option value="all">All classes</option>
          {classes.map((c) => <option key={c} value={c}>{c}</option>)}
        </Select>
        {editing && <Badge tone="amber">Edit mode — click a cell</Badge>}
      </div>

      {/* Weekly grid */}
      <div className="table-wrap">
        <table className="table tt-grid">
          <thead>
            <tr>
              <th aria-label="Day" />
              {PERIODS.map((p) => <th key={p} style={{ textAlign: 'center' }}>{p}</th>)}
            </tr>
          </thead>
          <tbody>
            {DAYS.map((day) => (
              <tr key={day}>
                <th>{day}</th>
                {PERIODS.map((period) => {
                  const slot = findSlot(day, period)
                  const isSel = selected?.day === day && selected?.period === period
                  return (
                    <td key={period} style={{ textAlign: 'center', padding: '0.3rem' }}>
                      {slot ? (
                        editing ? (
                          <button type="button" className={`tt-cell ${colorFor(slot.subject)}${isSel ? ' tt-sel' : ''}`}
                            onClick={() => { setSelected({ day, period }); setDraft({ subject: slot.subject, teacher: slot.teacher }) }}>
                            <b>{slot.subject}</b>
                            <small>{slot.teacher}</small>
                          </button>
                        ) : (
                          <div className={`tt-cell ${colorFor(slot.subject)}`}>
                            <b>{slot.subject}</b>
                            <small>{slot.teacher}</small>
                          </div>
                        )
                      ) : editing ? (
                        <button type="button" className={`tt-cell tt-empty${isSel ? ' tt-sel' : ''}`}
                          onClick={() => { setSelected({ day, period }); setDraft({ subject: '', teacher: '' }) }}>
                          ＋
                        </button>
                      ) : (
                        <span style={{ color: 'var(--muted)' }}>·</span>
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Slot editor */}
      {editing && selected && (
        <div className="card" style={{ marginTop: '1rem', maxWidth: 520 }}>
          <div className="card-body">
            <h3 style={{ marginBottom: '0.8rem' }}>Edit · {selected.day} {selected.period}</h3>
            {clash && <p className="auth-error">⚠️ {clash}</p>}
            <Select label="Subject" id="tt-subject" value={draft.subject}
              onChange={(e) => setDraft({ ...draft, subject: e.target.value })}>
              <option value="">— select —</option>
              {subjects.map((s) => <option key={s} value={s}>{s}</option>)}
            </Select>
            <Input label="Teacher" id="tt-teacher" value={draft.teacher} placeholder="Teacher name"
              onChange={(e) => setDraft({ ...draft, teacher: e.target.value })} />
            <div className="modal-actions">
              <Button variant="ghost" onClick={() => setSelected(null)}>Cancel</Button>
              <Button variant="danger" size="sm"
                onClick={() => { assignSlot(selected.day, selected.period, null); setSelected(null); toast.push('info', 'Slot cleared') }}>
                Clear slot
              </Button>
              <Button onClick={saveDraft}>Save slot</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
