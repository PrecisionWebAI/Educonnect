'use client'
import { useEffect, useState } from 'react'
import { getSettingUsers, getSchoolInfo, getSecurityLogs } from '@/db_demo/school-data'
import type { SettingUser, SchoolInfo, SecurityLog } from '@/types'

export type SettingsTab = 'Users & Roles' | 'School Profile' | 'Security' | 'Integrations & Prefs'

export function useSettings() {
  const [users, setUsers] = useState<SettingUser[]>([])
  const [info, setInfo] = useState<SchoolInfo[]>([])
  const [logs, setLogs] = useState<SecurityLog[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<SettingsTab>('Users & Roles')

  useEffect(() => {
    let alive = true
    Promise.all([getSettingUsers(), getSchoolInfo(), getSecurityLogs()]).then(([u, i, l]) => {
      if (!alive) return
      setUsers(u)
      setInfo(i)
      setLogs(l)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [])

  const activeCount = users.filter((u) => u.status === 'Active').length
  const pendingCount = users.filter((u) => u.status === 'Invited').length

  return { users, info, logs, loading, tab, setTab, activeCount, pendingCount }
}