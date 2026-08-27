'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '@/providers/auth-context'
import { NAV_GROUPS, type NavItem } from '@/lib/constants/nav'
import { ROLE_LABELS } from '@/types'
import Icon from '@/components/ui/Icon'

// App shell for logged-in users — sidebar + topbar (Next.js port).

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const close = () => setMobileOpen(false)
  const router = useRouter()
  const pathname = usePathname()

  const primaryRole = user?.roles[0] ?? 'STAFF'
  const roleLabel = ROLE_LABELS[primaryRole] ?? primaryRole

  async function handleLogout() {
    await logout()
    router.push('/auth')
  }

  return (
    <div className="shell">
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="sidebar-brand" onClick={close}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="EduConnect" />
          <span>EduConnect</span>
        </div>

        <nav className="sidebar-nav">
          {NAV_GROUPS.map((group) => (
            <div key={group.title} className="nav-group">
              <div className="nav-gtitle">{group.title}</div>
              {group.items.map((item) => (
                <NavItemLink key={item.to} item={item} active={pathname === item.to} onNavigate={close} />
              ))}
            </div>
          ))}
        </nav>
      </aside>

      {mobileOpen && <div className="sidebar-scrim" onClick={close} aria-hidden="true" />}

      <div className="shell-main">
        <header className="topbar">
          <button className="hamburger" onClick={() => setMobileOpen((v) => !v)} aria-label="Menu"><Icon name="more" size={20} /></button>
          <div className="topbar-search">
            <span className="topbar-search-ico"><Icon name="search" size={16} /></span>
            <input type="text" placeholder="Search students, classes, modules…  (⌘K)" />
          </div>
          <div className="topbar-actions">
            <Link href="/dashboard/notifications" className="icon-btn" aria-label="Notifications">
              <Icon name="bell" size={18} /><span className="icon-dot">5</span>
            </Link>
            <Link href="/dashboard/ai-copilot" className="icon-btn" aria-label="AI Copilot"><Icon name="ai" size={18} /></Link>
            <div className="user-chip">
              <span className="avatar">{user?.fullName?.[0] ?? 'U'}</span>
              <div className="user-meta">
                <span className="user-name">{user?.fullName}</span>
                <span className="user-role">{roleLabel}</span>
              </div>
            </div>
            <button className="btn btn-ghost btn-sm" onClick={() => void handleLogout()}>Log out</button>
          </div>
        </header>

        <main className="shell-content">{children}</main>
      </div>
    </div>
  )
}

function NavItemLink({ item, active, onNavigate }: { item: NavItem; active: boolean; onNavigate: () => void }) {
  return (
    <Link href={item.to} onClick={onNavigate} className={`nav-item${active ? ' nav-item-active' : ''}`}>
      <span className="nav-ico"><Icon name={item.icon} size={18} /></span>
      <span className="nav-label">{item.label}</span>
      {item.badge !== undefined && item.badge > 0 && <span className="nav-badge">{item.badge}</span>}
    </Link>
  )
}