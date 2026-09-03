'use client'
import { useEffect, useState } from 'react'
import { getAutomations, getCopilotSuggestions } from '@/temp/school-data'
import type { CopilotAutomation, CopilotSuggestion } from '@/types'

export type CopilotTab = 'Ask AI' | 'Command Palette' | 'Genius Assistant' | 'Automations'

export function useCopilot() {
  const [automations, setAutomations] = useState<CopilotAutomation[]>([])
  const [suggestions, setSuggestions] = useState<CopilotSuggestion[]>([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState<CopilotTab>('Ask AI')
  const [prompt, setPrompt] = useState('')

  useEffect(() => {
    let alive = true
    Promise.all([getAutomations(), getCopilotSuggestions()]).then(([a, s]) => {
      if (!alive) return
      setAutomations(a)
      setSuggestions(s)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [])

  const activeCount = automations.filter((a) => a.active).length

  return { automations, suggestions, loading, tab, setTab, prompt, setPrompt, activeCount }
}