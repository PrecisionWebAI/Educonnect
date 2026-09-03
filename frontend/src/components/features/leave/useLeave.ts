'use client'
import { useEffect, useState } from 'react'
import { getLeaveApplications } from '@/db_demo/school-data'
import type { LeaveApplicationItem } from '@/types'

export type LeaveTab = 'Apply' | 'My Leaves' | 'Approvals' | 'Staff Leave'

export function useLeave() {
  const [leaves, setLeaves] = useState<LeaveApplicationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<LeaveTab>('Apply')

  useEffect(() => {
    let alive = true
    getLeaveApplications().then((l) => {
      if (!alive) return
      setLeaves(l)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [])

  const pendingCount = leaves.filter((l) => l.status === 'Pending').length
  const approvedCount = leaves.filter((l) => l.status === 'Approved').length

  const approve = (id: number) => {
    setLeaves((prev) => prev.map((l) =>
      l.id === id ? { ...l, status: 'Approved' as const } : l
    ))
  }

  return { leaves, loading, tab, setTab, pendingCount, approvedCount, approve }
}