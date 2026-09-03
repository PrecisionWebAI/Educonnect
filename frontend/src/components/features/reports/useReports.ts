'use client'
import { useEffect, useState } from 'react'
import { getReportCards, getDataQuality } from '@/temp/school-data'
import type { ReportCard, DataQualityRow } from '@/types'

export function useReports() {
  const [cards, setCards] = useState<ReportCard[]>([])
  const [quality, setQuality] = useState<DataQualityRow[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    Promise.all([getReportCards(), getDataQuality()]).then(([c, q]) => {
      if (!alive) return
      setCards(c)
      setQuality(q)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [])

  const criticalCount = quality.filter((q) => q.status === 'Critical').length
  const attentionCount = quality.filter((q) => q.status === 'Attention').length
  const avgScore = quality.length ? Math.round(quality.reduce((s, q) => s + q.score, 0) / quality.length) : 0

  return { cards, quality, loading, criticalCount, attentionCount, avgScore }
}