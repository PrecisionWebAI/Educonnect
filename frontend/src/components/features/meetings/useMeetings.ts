'use client'
import { useEffect, useState } from 'react'
import { getMeetings } from '@/temp/school-data'
import type { MeetingItem } from '@/types'

export type MeetingTab = 'Upcoming' | 'Book' | 'Pending' | 'History'

export function useMeetings() {
  const [meetings, setMeetings] = useState<MeetingItem[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<MeetingTab>('Upcoming')

  useEffect(() => {
    let alive = true
    getMeetings().then((m) => {
      if (!alive) return
      setMeetings(m)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [])

  const pendingCount = meetings.filter((m) => m.type === 'Pending').length
  const doneCount = meetings.filter((m) => m.type === 'Done').length

  const filtered = meetings.filter((m) => {
    if (tab === 'Pending') return m.type === 'Pending'
    if (tab === 'History') return m.type === 'Done'
    if (tab === 'Book') return false
    return m.type === 'Scheduled'
  })

  return { meetings, filtered, loading, tab, setTab, pendingCount, doneCount }
}