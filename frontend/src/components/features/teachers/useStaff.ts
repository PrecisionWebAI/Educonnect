'use client'
import { useEffect, useMemo, useState } from 'react'
import {
  getStaff,
  getWorkloadMatrix,
  getStaffLeaves,
  getStaffPerformance,
} from '@/temp/school-data'
import type { StaffMember } from '@/types'

export type StaffTab = 'List' | 'Workload' | 'Leave & Substitute' | 'Performance'

export type WorkloadMatrixRows = Awaited<ReturnType<typeof getWorkloadMatrix>>
export type StaffLeaveRows = Awaited<ReturnType<typeof getStaffLeaves>>
export type StaffPerfRows = Awaited<ReturnType<typeof getStaffPerformance>>

export function useStaff(tab: StaffTab) {
  const [staff, setStaff] = useState<StaffMember[]>([])
  const [matrix, setMatrix] = useState<Awaited<ReturnType<typeof getWorkloadMatrix>>>([])
  const [leaves, setLeaves] = useState<Awaited<ReturnType<typeof getStaffLeaves>>>([])
  const [perf, setPerf] = useState<Awaited<ReturnType<typeof getStaffPerformance>>>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [dept, setDept] = useState('All')

  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.all([getStaff(), getWorkloadMatrix(), getStaffLeaves(), getStaffPerformance()])
      .then(([s, m, l, p]) => {
        if (!alive) return
        setStaff(s)
        setMatrix(m)
        setLeaves(l)
        setPerf(p)
        setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [])

  const departments = useMemo(
    () => ['All', ...Array.from(new Set(staff.map((s) => s.department)))],
    [staff],
  )

  const filtered = useMemo(
    () =>
      staff.filter((s) => {
        const q = query.trim().toLowerCase()
        const matchQ = !q || s.name.toLowerCase().includes(q) || s.subject.toLowerCase().includes(q) || s.staffCode.toLowerCase().includes(q)
        const matchD = dept === 'All' || s.department === dept
        return matchQ && matchD
      }),
    [staff, query, dept],
  )

  const activeCount = staff.filter((s) => s.status === 'Active').length
  const leaveCount = staff.filter((s) => s.status === 'On Leave').length

  return {
    staff,
    filtered,
    matrix,
    leaves,
    perf,
    loading,
    query,
    setQuery,
    dept,
    setDept,
    departments,
    activeCount,
    leaveCount,
  }
}