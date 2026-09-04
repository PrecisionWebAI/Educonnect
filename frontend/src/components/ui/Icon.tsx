// ============================================================
// Icon — minimal Material-style SVG icon set (stroke-based).
// No emoji, no icon-font dependency. Usage: <Icon name="groups" />
// ============================================================

export type IconName =
  | 'attendance' | 'wallet' | 'ai' | 'warning' | 'check' | 'groups'
  | 'students' | 'guardian' | 'school' | 'active' | 'download' | 'plus'
  | 'calendar' | 'trending' | 'clock' | 'search' | 'edit' | 'more'
  | 'dashboard' | 'bell' | 'chat' | 'book' | 'money' | 'bus' | 'home'

const PATHS: Record<IconName, React.ReactNode> = {
  attendance: <><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M8 2v4M16 2v4M3 9h18" /><circle cx="9.5" cy="14.5" r="1.6" /><path d="M6.2 19c.4-1.8 1.8-3 3.3-3s2.9 1.2 3.3 3" /></>,
  wallet: <><rect x="3" y="6" width="18" height="13" rx="2" /><path d="M3 10h18" /><circle cx="16.5" cy="14.5" r="1.3" /></>,
  ai: <><rect x="5" y="5" width="14" height="14" rx="3" /><path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" /><circle cx="12" cy="12" r="2.4" /></>,
  warning: <path d="M12 3 2.5 20h19L12 3zM12 10v4M12 17.5v.5" />,
  check: <path d="M4 12.5 9.5 18 20 6.5" />,
  groups: <><circle cx="9" cy="9" r="3" /><path d="M3.5 19c.5-3 2.8-5 5.5-5s5 2 5.5 5" /><circle cx="17" cy="10" r="2.4" /><path d="M15.8 19c.4-2.2 1.8-3.6 3.7-3.6 1 0 1.9.4 2.5 1.1" /></>,
  students: <><circle cx="12" cy="8" r="3.2" /><path d="M5 20c.7-3.6 3.6-6 7-6s6.3 2.4 7 6" /></>,
  guardian: <><circle cx="9" cy="8.5" r="2.8" /><path d="M4 19c.5-2.8 2.5-4.5 5-4.5s4.5 1.7 5 4.5" /><circle cx="17" cy="10" r="2.2" /><path d="M15.5 19c.3-2 1.6-3.4 3.5-3.4.9 0 1.7.3 2.3.9" /></>,
  school: <><path d="M12 3 2 8l10 5 10-5-10-5z" /><path d="M6 10.5V16c0 1.5 2.7 3 6 3s6-1.5 6-3v-5.5" /></>,
  active: <><circle cx="12" cy="12" r="9" /><path d="M8 12.5 11 15.5 16 9.5" /></>,
  download: <><path d="M12 3v12M7 10l5 5 5-5" /><path d="M4 19h16" /></>,
  plus: <path d="M12 5v14M5 12h14" />,
  calendar: <><rect x="3" y="4" width="18" height="17" rx="2" /><path d="M8 2v4M16 2v4M3 9h18" /></>,
  trending: <path d="M3 17 9.5 10.5 13.5 14.5 21 7M15.5 7H21v5.5" />,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3.5 2" /></>,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.5 15.5 21 21" /></>,
  edit: <path d="M4 20h4L19.5 8.5a2.1 2.1 0 0 0-3-3L5 17v3zM14 7l3 3" />,
  more: <path d="M12 6h.01M12 12h.01M12 18h.01" />,
  dashboard: <><rect x="3" y="3" width="8" height="8" rx="1.5" /><rect x="13" y="3" width="8" height="5" rx="1.5" /><rect x="13" y="10" width="8" height="11" rx="1.5" /><rect x="3" y="13" width="8" height="8" rx="1.5" /></>,
  bell: <><path d="M18 9a6 6 0 1 0-12 0c0 6-2 7-2 7h16s-2-1-2-7" /><path d="M10.3 20a2 2 0 0 0 3.4 0" /></>,
  chat: <path d="M21 12a8 8 0 0 1-8 8H4l2-3a8 8 0 1 1 15-5z" />,
  book: <><path d="M4 5a2 2 0 0 1 2-2h14v18H6a2 2 0 0 0-2 2V5z" /><path d="M20 17H6a2 2 0 0 0-2 2" /></>,
  money: <><rect x="2" y="6" width="20" height="12" rx="2" /><circle cx="12" cy="12" r="2.6" /><path d="M6 12h.01M18 12h.01" /></>,
  bus: <><rect x="4" y="3" width="16" height="14" rx="2" /><path d="M4 11h16M7 20v-3M17 20v-3M7 17h10" /><circle cx="8" cy="14" r=".5" /><circle cx="16" cy="14" r=".5" /></>,
  home: <path d="M3 11 12 3l9 8M5.5 9.5V20h13V9.5" />,
}

export default function Icon({ name, size = 20, className }: {
  name: IconName
  size?: number
  className?: string
}) {
  return (
    <svg
      className={className}
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  )
}