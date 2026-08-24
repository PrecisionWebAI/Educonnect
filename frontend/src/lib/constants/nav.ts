import type { Role } from '@/types'

// ============================================================
// Sidebar navigation — one entry per blueprinted module page.
// Next.js routes: /dashboard/<module>
// ============================================================

export interface NavItem {
  to: string
  label: string
  icon: string
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
      { to: '/dashboard', label: 'Dashboard', icon: '📊' },
      { to: '/dashboard/notifications', label: 'Notifications', icon: '🔔', badge: 5 },
      { to: '/dashboard/ai-copilot', label: 'AI Copilot', icon: '🤖' },
      { to: '/dashboard/chat', label: 'Chat', icon: '💬' },
    ],
  },
  {
    title: 'Academic',
    items: [
      { to: '/dashboard/students', label: 'Students', icon: '🎓' },
      { to: '/dashboard/attendance', label: 'Attendance', icon: '✅' },
      { to: '/dashboard/academics', label: 'Academics & Marks', icon: '📝' },
      { to: '/dashboard/exams', label: 'Exams & AI Papers', icon: '🧪' },
      { to: '/dashboard/homework', label: 'Homework & Diary', icon: '📚' },
      { to: '/dashboard/timetable', label: 'Timetable', icon: '🗓️' },
    ],
  },
  {
    title: 'People & Finance',
    items: [
      { to: '/dashboard/teachers', label: 'Teachers & Staff', icon: '👩‍🏫' },
      { to: '/dashboard/payroll', label: 'Payroll / Payslip', icon: '💸' },
      { to: '/dashboard/finance', label: 'Finance (Fees)', icon: '💰' },
    ],
  },
  {
    title: 'Services',
    items: [
      { to: '/dashboard/library', label: 'Library', icon: '📖' },
      { to: '/dashboard/transport', label: 'Transport', icon: '🚌' },
      { to: '/dashboard/meetings', label: 'Meetings', icon: '🤝' },
      { to: '/dashboard/tickets', label: 'Tickets & Support', icon: '🎫' },
      { to: '/dashboard/leave', label: 'Leave & Applications', icon: '🏖️' },
    ],
  },
  {
    title: 'Insights & Admin',
    items: [
      { to: '/dashboard/reports', label: 'Reports & Analytics', icon: '📈' },
      { to: '/dashboard/settings', label: 'Settings', icon: '⚙️' },
    ],
  },
]
