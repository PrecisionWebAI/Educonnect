'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/providers/auth-context'
import AppLayout from '@/components/AppLayout'

// Guard: only logged-in users can see anything under /dashboard.
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { isAuthed } = useAuth()
  const router = useRouter()

  useEffect(() => {
    if (!isAuthed) router.replace('/auth')
  }, [isAuthed, router])

  if (!isAuthed) return null
  return <AppLayout>{children}</AppLayout>
}