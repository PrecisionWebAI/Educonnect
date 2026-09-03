'use client'
import { useEffect, useState } from 'react'
import { getChatConversations } from '@/temp/school-data'
import type { ChatConversation } from '@/types'

export type ChatTab = 'Conversations' | 'Groups' | 'Files'

export function useChat() {
  const [conversations, setConversations] = useState<ChatConversation[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<ChatTab>('Conversations')

  useEffect(() => {
    let alive = true
    getChatConversations().then((c) => {
      if (!alive) return
      setConversations(c)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [])

  const unreadTotal = conversations.reduce((sum, c) => sum + c.unread, 0)
  const onlineCount = conversations.filter((c) => c.online).length
  const filtered = tab === 'Groups' ? conversations.filter((c) => c.group) : tab === 'Files' ? [] : conversations.filter((c) => !c.group)

  return { conversations, filtered, loading, tab, setTab, unreadTotal, onlineCount }
}