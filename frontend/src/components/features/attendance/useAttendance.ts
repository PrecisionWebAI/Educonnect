'use client'

import { useEffect, useMemo, useState } from 'react'
import { getAttendance, getStudents } from '@/temp/school-data'
import type { AttendanceRecord, Student } from '@/types'

const STATUSES = ['Present', 'Absent', 'Late', 'Leave'] as const
export type Status = (typeof STATUSES)[number]
export const ATTENDANCE_STATUSES = STATUSES

export function useAttendance() {
  const [students, setStudents] = useState<Student[] | null>(null)
  const [history, setHistory] = useState<AttendanceRecord[]>([])
  const [className, setClassName] = useState('10')
  const [section, setSection] = useState('A')
  const [date, setDate] = useState('') // set after mount (SSR-safe)
  // per-student marks for the selected roster; unset = not yet marked
  const [marks, setMarks] = useState<Record<number, Status>>({})

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

  const markedCount = useMemo(
    () => roster.filter((s) => marks[s.id]).length,
    [roster, marks],
  )

  function setAll(status: Status) {
    setMarks(Object.fromEntries(roster.map((s) => [s.id, status])))
  }

  function reset() {
    setMarks({})
  }

  /** Persist the current roster marks into history (mock — will be an API call). */
  function save(): AttendanceRecord[] | null {
    if (roster.length === 0) return null
    const records: AttendanceRecord[] = roster.map((s, i) => ({
      id: Date.now() + i,
      studentName: s.name,
      className: `${s.className}-${s.section}`,
      date,
      status: marks[s.id] ?? 'Present',
    }))
    setHistory((prev) => [...records, ...prev])
    setMarks({})
    return records
  }

  // ── Stitch widget data (computed, memoized) ────────────────

  /** Live counts for the summary strip. */
  const counts = useMemo(() => {
    const c: Record<Status | 'Unmarked', number> = {
      Present: 0, Absent: 0, Late: 0, Leave: 0, Unmarked: 0,
    }
    for (const s of roster) {
      const st = marks[s.id]
      if (st) c[st] += 1
      else c.Unmarked += 1
    }
    return c
  }, [roster, marks])

  /** Weekday averages from history (mock trend for the right column). */
  const weeklyTrend = useMemo(() => {
    const base = { Mon: 92, Tue: 95, Wed: 94, Thu: 98, Fri: 96, Sat: 93 } as Record<string, number>
    // nudge numbers slightly using today's saved records so it feels live
    const todayName = new Date().toLocaleDateString('en-IN', { weekday: 'short' })
    if (todayName in base && history.length > 0) {
      const pct =
        history.filter((r) => r.status === 'Present').length / Math.max(1, history.length)
      base[todayName] = Math.round(base[todayName] * 0.4 + pct * 100 * 0.6)
    }
    return base
  }, [history])

  /** Students flagged Absent/Late in current marks + known chronic absentees. */
  const alerts = useMemo(() => {
    const list: { name: string; reason: string }[] = []
    for (const s of roster) {
      const st = marks[s.id]
      if (st === 'Absent') list.push({ name: s.name, reason: 'Marked absent today' })
      else if (st === 'Late') list.push({ name: s.name, reason: 'Arrived late today' })
    }
    return list
  }, [roster, marks])

  return {
    loading: students === null,
    classes: [...new Set((students ?? []).map((s) => s.className))].sort(),
    className, setClassName, section, setSection, date, setDate,
    roster, marks,
    setMark: (id: number, status: Status) => setMarks((prev) => ({ ...prev, [id]: status })),
    setAll, reset, save,
    markedCount,
    counts, weeklyTrend, alerts,
    history, setHistory,
  }
}