'use client'

import type { Student } from '@/types'
import { Button } from '@/components/ui'
import { ATTENDANCE_STATUSES, type Status } from './useAttendance'

function initials(name: string) {
  return name.split(' ').map((p) => p[0]).slice(0, 2).join('').toUpperCase()
}

// Roster grid — one row per student with 4-way status chips.
export default function MarkAttendanceTab({
  roster,
  marks,
  onSetMark,
  onSetAll,
  onReset,
}: {
  roster: Student[]
  marks: Record<number, Status>
  onSetMark: (id: number, status: Status) => void
  onSetAll: (status: Status) => void
  onReset: () => void
}) {
  if (roster.length === 0) {
    return <p style={{ color: 'var(--muted)' }}>No students in this class-section. Add students first.</p>
  }

  return (
    <div className="roster">
      <div className="roster-actions">
        <Button size="sm" variant="success" onClick={() => onSetAll('Present')}>Mark all present</Button>
        <Button size="sm" variant="ghost" onClick={onReset}>Reset</Button>
      </div>

      {roster.map((s) => (
        <div key={s.id} className="roster-row">
          <span className="cell-avatar">{initials(s.name)}</span>
          <span className="roster-name">
            <strong>{s.name}</strong>
            <span style={{ color: 'var(--muted)', fontSize: '0.76rem' }}>{s.admissionNo}</span>
          </span>
          <div className="roster-status" role="radiogroup" aria-label={`Attendance for ${s.name}`}>
            {ATTENDANCE_STATUSES.map((st) => (
              <button
                key={st}
                type="button"
                role="radio"
                aria-checked={marks[s.id] === st}
                className={`chip chip-${(marks[s.id] ?? '').toLowerCase()}${marks[s.id] === st ? ' chip-on' : ''}`}
                onClick={() => onSetMark(s.id, st)}
              >
                {st}
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}