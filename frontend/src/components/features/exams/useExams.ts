'use client'
import { useEffect, useMemo, useState } from 'react'
import {
  getQuestionBank,
  getPaperDraftsFull,
  getExamSchedule,
  getExamMarkings,
  getExamPaperReviews,
} from '@/temp/school-data'
import type { QuestionItem } from '@/types'

export type ExamsTab = 'AI Paper Generator' | 'Question Bank' | 'My Papers' | 'Conduct & Marking' | 'Schedule & Seating'

export function useExams() {
  const [questions, setQuestions] = useState<QuestionItem[]>([])
  const [papers, setPapers] = useState<Awaited<ReturnType<typeof getPaperDraftsFull>>>([])
  const [schedule, setSchedule] = useState<Awaited<ReturnType<typeof getExamSchedule>>>([])
  const [markings, setMarkings] = useState<Awaited<ReturnType<typeof getExamMarkings>>>([])
  const [reviews, setReviews] = useState<Awaited<ReturnType<typeof getExamPaperReviews>>>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [subject, setSubject] = useState('All')

  useEffect(() => {
    let alive = true
    Promise.all([getQuestionBank(), getPaperDraftsFull(), getExamSchedule(), getExamMarkings(), getExamPaperReviews()])
      .then(([q, p, s, m, r]) => {
        if (!alive) return
        setQuestions(q)
        setPapers(p)
        setSchedule(s)
        setMarkings(m)
        setReviews(r)
        setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [])

  const subjects = useMemo(() => ['All', ...Array.from(new Set(questions.map((q) => q.subject)))], [questions])
  const questionTypes = useMemo(() => Array.from(new Set(questions.map((q) => q.type))), [questions])

  const filteredQuestions = useMemo(
    () =>
      questions.filter((q) => {
        const qs = query.trim().toLowerCase()
        const matchQ = !qs || q.text.toLowerCase().includes(qs) || q.chapter.toLowerCase().includes(qs)
        const matchS = subject === 'All' || q.subject === subject
        return matchQ && matchS
      }),
    [questions, query, subject],
  )

  return {
    questions, filteredQuestions, papers, schedule, markings, reviews,
    loading, query, setQuery, subject, setSubject, subjects, questionTypes,
  }
}