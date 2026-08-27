'use client'

import { useAuth } from '@/providers/auth-context'
import type { Role } from '@/types'
import DirectorDashboard from './DirectorDashboard'
import PrincipalDashboard from './PrincipalDashboard'
import HodDashboard from './HodDashboard'
import ClassTeacherDashboard from './ClassTeacherDashboard'
import SubjectTeacherDashboard from './SubjectTeacherDashboard'
import StudentDashboard from './StudentDashboard'
import ParentDashboard from './ParentDashboard'
import AccountantDashboard from './AccountantDashboard'

// PAGE 02 — Role-mastered Home. Picks the right dashboard by role.
export default function DashboardHome() {
  const { user } = useAuth()
  const role = user?.roles[0] as Role | undefined

  switch (role) {
    case 'PRINCIPAL': return <PrincipalDashboard />
    case 'HOD': return <HodDashboard />
    case 'CLASS_TEACHER': return <ClassTeacherDashboard />
    case 'SUBJECT_TEACHER': return <SubjectTeacherDashboard />
    case 'STUDENT': return <StudentDashboard />
    case 'GUARDIAN': return <ParentDashboard />
    case 'ACCOUNTANT': return <AccountantDashboard />
    // DIRECTOR, ADMIN, LIBRARIAN, TRANSPORT, STAFF, unknown → directors (admin) view
    default: return <DirectorDashboard />
  }
}