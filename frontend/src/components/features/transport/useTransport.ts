'use client'
import { useEffect, useMemo, useState } from 'react'
import { getTransportRoutes, getBuses } from '@/db_demo/school-data'
import type { TransportRoute, Bus } from '@/types'

export type TransportTab = 'Routes & Stops' | 'Buses & GPS' | 'Fees & Enforcement'

export function useTransport() {
  const [routes, setRoutes] = useState<TransportRoute[]>([])
  const [buses, setBuses] = useState<Bus[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.all([getTransportRoutes(), getBuses()]).then(([r, b]) => {
      if (!alive) return
      setRoutes(r)
      setBuses(b)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [])

  const totalStudents = useMemo(() => routes.reduce((a, r) => a + r.students, 0), [routes])
  const activeRoutes = routes.filter((r) => r.status === 'Active').length
  const enRoute = buses.filter((b) => b.status === 'En route').length
  const avgOccupancy = useMemo(() => {
    if (buses.length === 0) return 0
    const sum = buses.reduce((a, b) => a + (b.occupied / b.capacity) * 100, 0)
    return Math.round(sum / buses.length)
  }, [buses])

  return {
    routes,
    buses,
    loading,
    totalStudents,
    activeRoutes,
    enRoute,
    avgOccupancy,
  }
}