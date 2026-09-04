import type { Role } from '@/types'
import type { IconName } from '@/components/ui/Icon'

// ============================================================
// Sidebar navigation — one entry per blueprinted module page.
// Next.js routes: /dashboard/<module>. Icons are SVG names
// (see components/ui/Icon.tsx) — no emoji anywhere.
// ============================================================

export interface NavItem {
  to: string
  label: string
  icon: IconName
  roles?: Role[]
  badge?: number
}

export interface NavGroup {
  title: string
  items: NavItem[]
}

export const NAV_GROUPS: NavGroup[] = [
  {
    title: 'Main',
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
      { to: '/dashboard/notifications', label: 'Notifications', icon: 'bell', badge: 5 },
      { to: '/dashboard/ai-copilot', label: 'AI Copilot', icon: 'ai' },
      { to: '/dashboard/chat', label: 'Chat', icon: 'chat' },
    ],
  },
  {
    title: 'Academic',
    items: [
      { to: '/dashboard/students', label: 'Students', icon: 'students' },
      { to: '/dashboard/attendance', label: 'Attendance', icon: 'attendance' },
      { to: '/dashboard/academics', label: 'Academics & Marks', icon: 'book' },
      { to: '/dashboard/exams', label: 'Exams & AI Papers', icon: 'edit' },
      { to: '/dashboard/homework', label: 'Homework & Diary', icon: 'book' },
      { to: '/dashboard/classroom', label: 'Classroom', icon: 'school' },
      { to: '/dashboard/timetable', label: 'Timetable', icon: 'calendar' },
    ],
  },
  {
    title: 'People & Finance',
    items: [
      { to: '/dashboard/teachers', label: 'Teachers & Staff', icon: 'guardian' },
      { to: '/dashboard/payroll', label: 'Payroll / Payslip', icon: 'money' },
      { to: '/dashboard/finance', label: 'Finance (Fees)', icon: 'wallet' },
    ],
  },
  {
    title: 'Services',
    items: [
      { to: '/dashboard/library', label: 'Library', icon: 'book' },
      { to: '/dashboard/transport', label: 'Transport', icon: 'bus' },
      { to: '/dashboard/meetings', label: 'Meetings', icon: 'groups' },
      { to: '/dashboard/tickets', label: 'Tickets & Support', icon: 'warning' },
      { to: '/dashboard/leave', label: 'Leave & Applications', icon: 'calendar' },
    ],
  },
  {
    title: 'Insights & Admin',
    items: [
      { to: '/dashboard/reports', label: 'Reports & Analytics', icon: 'trending' },
      { to: '/dashboard/settings', label: 'Settings', icon: 'more' },
    ],
  },
]
