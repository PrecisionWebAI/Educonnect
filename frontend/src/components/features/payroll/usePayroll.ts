'use client'
import { useEffect, useMemo, useState } from 'react'
import { getSalaryStructure, getPayrollEntry } from '@/db_demo/school-data'
import type { SalaryStructureRow, PayrollEntry } from '@/types'

export type PayrollTab = 'Salary Structure' | 'Month Processing' | 'Payslips'

export function usePayroll(tab: PayrollTab) {
  const [structures, setStructures] = useState<SalaryStructureRow[]>([])
  const [entries, setEntries] = useState<PayrollEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState('All')

  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.all([getSalaryStructure(), getPayrollEntry()]).then(([s, e]) => {
      if (!alive) return
      setStructures(s)
      setEntries(e)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [])

  const statuses = useMemo(
    () => ['All', ...Array.from(new Set(entries.map((e) => e.status)))],
    [entries],
  )

  const filtered = useMemo(
    () =>
      entries.filter((e) => {
        const q = query.trim().toLowerCase()
        const matchQ = !q || e.name.toLowerCase().includes(q) || e.staffCode.toLowerCase().includes(q)
        const matchS = status === 'All' || e.status === status
        return matchQ && matchS
      }),
    [entries, query, status],
  )

  const totalPayroll = useMemo(() => entries.reduce((a, e) => a + e.net, 0), [entries])
  const draftCount = entries.filter((e) => e.status === 'Draft').length
  const postedCount = entries.filter((e) => e.status === 'Posted').length
  const paidCount = entries.filter((e) => e.status === 'Paid').length

  return {
    structures,
    entries,
    filtered,
    loading,
    query,
    setQuery,
    status,
    setStatus,
    statuses,
    totalPayroll,
    draftCount,
    postedCount,
    paidCount,
  }
}