'use client'
import { useEffect, useState } from 'react'
import { getTickets } from '@/db_demo/school-data'
import type { TicketItem } from '@/types'

export type TicketTab = 'My Tickets' | 'Raise' | 'Inbox' | 'Oversight'

export function useTickets() {
  const [tickets, setTickets] = useState<TicketItem[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<TicketTab>('My Tickets')

  useEffect(() => {
    let alive = true
    getTickets().then((t) => {
      if (!alive) return
      setTickets(t)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [])

  const openCount = tickets.filter((t) => t.status === 'Open').length
  const inProgressCount = tickets.filter((t) => t.status === 'In Progress').length
  const resolvedCount = tickets.filter((t) => t.status === 'Resolved' || t.status === 'Closed').length

  return { tickets, loading, tab, setTab, openCount, inProgressCount, resolvedCount }
}