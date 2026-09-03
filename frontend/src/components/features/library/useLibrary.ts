'use client'
import { useEffect, useMemo, useState } from 'react'
import { getLibraryBooks, getBookIssues } from '@/temp/school-data'
import type { LibraryBook, BookIssue } from '@/types'

export type LibraryTab = 'Catalogue & Search' | 'Issue / Return' | 'Overdues & Notices'

export function useLibrary(tab: LibraryTab) {
  const [books, setBooks] = useState<LibraryBook[]>([])
  const [issues, setIssues] = useState<BookIssue[]>([])
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All')

  useEffect(() => {
    let alive = true
    setLoading(true)
    Promise.all([getLibraryBooks(), getBookIssues()]).then(([b, i]) => {
      if (!alive) return
      setBooks(b)
      setIssues(i)
      setLoading(false)
    })
    return () => {
      alive = false
    }
  }, [])

  const categories = useMemo(
    () => ['All', ...Array.from(new Set(books.map((b) => b.category)))],
    [books],
  )

  const filteredBooks = useMemo(
    () =>
      books.filter((b) => {
        const q = query.trim().toLowerCase()
        const matchQ = !q || b.title.toLowerCase().includes(q) || b.author.toLowerCase().includes(q) || b.isbn.toLowerCase().includes(q)
        const matchC = category === 'All' || b.category === category
        return matchQ && matchC
      }),
    [books, query, category],
  )

  const filteredIssues = useMemo(
    () =>
      issues.filter((i) => {
        const q = query.trim().toLowerCase()
        return !q || i.book.toLowerCase().includes(q) || i.student.toLowerCase().includes(q)
      }),
    [issues, query],
  )

  const overdueIssues = issues.filter((i) => i.status === 'Overdue')
  const totalCopies = books.reduce((a, b) => a + b.copies, 0)
  const issuedCount = issues.filter((i) => i.status === 'Borrowed').length

  return {
    books,
    issues,
    filteredBooks,
    filteredIssues,
    overdueIssues,
    loading,
    query,
    setQuery,
    category,
    setCategory,
    categories,
    totalCopies,
    issuedCount,
  }
}