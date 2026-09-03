'use client'
import { useEffect, useState } from 'react'
import { getNotifications, markAllNotificationsRead } from '@/temp/school-data'
import type { NotificationItem } from '@/types'

export type NotificationsTab = 'All' | 'Unread' | 'Attendance' | 'Homework' | 'Alerts'

export function useNotifications() {
  const [items, setItems] = useState<NotificationItem[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<NotificationsTab>('All')

  useEffect(() => {
    let alive = true
    getNotifications().then((n) => {
      if (!alive) return
      setItems(n)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [])

  const unreadCount = items.filter((i) => !i.read).length

  const filtered = items.filter((i) => {
    if (tab === 'Unread') return !i.read
    if (tab === 'All') return true
    return i.kind === tab
  })

  const markAll = () => {
    markAllNotificationsRead().then(() => {
      setItems((prev) => prev.map((i) => ({ ...i, read: true })))
    })
  }

  return { items, filtered, loading, tab, setTab, unreadCount, markAll }
}