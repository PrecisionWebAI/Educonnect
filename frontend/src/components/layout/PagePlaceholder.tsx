'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { EmptyState, PageHeader } from '@/components/ui'

// Generic shell for modules that aren't built yet. Each module
// gets real content in its own phase; this shows its planned tabs.

const TABS_BY_PATH: Record<string, string[]> = {
  '/dashboard/students': ['Student list', 'Add / Edit', 'Profile', 'Class matrix'],
  '/dashboard/attendance': ['Mark attendance', 'History', 'Insights', 'Leave sync'],
  '/dashboard/academics': ['Marks entry', 'Gradebook', 'Results', 'Disputes'],
  '/dashboard/exams': ['AI paper generator', 'Question bank', 'My papers', 'Conduct', 'Schedule'],
  '/dashboard/homework': ['Assign', 'Submissions', 'Class diary', 'Student/Parent'],
  '/dashboard/timetable': ['Weekly table', 'Editor'],
  '/dashboard/teachers': ['Staff list', 'Workload', 'Leave & substitute', 'Performance'],
  '/dashboard/payroll': ['Salary structure', 'Month processing', 'Payslips'],
  '/dashboard/finance': ['Fee collection', 'Dues', 'Expenses & budget', 'Reports'],
  '/dashboard/library': ['Catalogue', 'Issue / Return', 'Overdues'],
  '/dashboard/transport': ['Routes & stops', 'Buses & GPS', 'Fees'],
  '/dashboard/meetings': ['Book', 'My meetings', 'Schedule', 'History'],
  '/dashboard/tickets': ['Raise', 'My tickets', 'Inbox', 'Oversight'],
  '/dashboard/notifications': ['Inbox', 'Templates', 'Preferences', 'History'],
  '/dashboard/chat': ['Conversations', 'Groups', 'Files'],
  '/dashboard/leave': ['Apply', 'My leaves', 'Approvals', 'Settings'],
  '/dashboard/reports': ['Report builder', 'Director center', 'Education', 'Data quality'],
  '/dashboard/ai-copilot': ['Command palette', 'Ask AI', 'Genius assistant', 'Automation'],
  '/dashboard/settings': ['Users & roles', 'School profile', 'Security', 'Preferences'],
}

export default function PagePlaceholder({ title, icon }: { title: string; icon: string }) {
  const pathname = usePathname()
  const tabs = TABS_BY_PATH[pathname]

  return (
    <div className="page">
      <PageHeader title={title} subtitle="Module scaffold — coming in a later phase" />
      <div className="placeholder-tabs">
        {tabs?.map((t) => (
          <span key={t} className="ph-tab">{t}</span>
        ))}
      </div>
      <EmptyState
        icon={icon}
        title={`“${title}” is next on the roadmap`}
        body="The blueprint for this module is pinned in project-blueprint.md. I'll build its tabs next."
      />
      <div className="placeholder-actions">
        <Link href="/dashboard" className="btn btn-primary">Back to Dashboard</Link>
        <Link href="/dashboard/ai-copilot" className="btn btn-outline">Ask EduConnect AI</Link>
      </div>
    </div>
  )
}