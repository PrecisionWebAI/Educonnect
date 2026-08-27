'use client'

import { useEffect } from 'react'
import Link from 'next/link'

// ============================================================
// PAGE 02 — Public Landing page (Next.js port of the stitch
// educonnect_landing_page_desktop_1 design).
// ============================================================

const STATS = [
  { value: '500+', label: 'Schools onboard' },
  { value: '2.5L+', label: 'Students managed' },
  { value: '99.9%', label: 'Uptime' },
  { value: '40%', label: 'Admin work saved' },
]

interface BentoItem {
  icon: string
  title: string
  text: string
  quote?: string
  large?: boolean
}

const BENTO: BentoItem[] = [
  {
    icon: '🤖',
    title: 'AI Assistant Copilot',
    text: 'Your 24/7 administrative partner. Automate routine parent queries, draft personalized reports, and summarize meeting notes instantly.',
    quote: '"Draft an email to parents regarding tomorrow\'s schedule change…"',
    large: true,
  },
  { icon: '✅', title: 'Smart Attendance', text: 'Frictionless tracking for physical classrooms with automated anomaly detection for absenteeism.' },
  { icon: '📊', title: 'Deep Analytics', text: 'Transform data into action. Gain comprehensive insights into academic performance and operational efficiency.' },
  { icon: '💰', title: 'Transparent Fees', text: 'Online payments, instant receipts and live dues tracking — no more ledger registers.' },
  { icon: '💬', title: 'Unified Comms', text: 'Secure, real-time messaging connecting teachers, parents, and students in one centralized hub.' },
]

const ABOUT_POINTS = [
  'Attendance, marks, exams and report cards — one screen for every teacher',
  'Fees, receipts, budgets, payroll and payslips for the finance team',
  'Library, transport, leave & applications — all workflows online',
  'Parent–teacher meetings, chat, tickets and role-based notifications',
  'Reports, analytics and AI Copilot for smarter school decisions',
]

export default function LandingPage() {
  useEffect(() => {
    if (window.location.hash === '#features') {
      document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })
    }
    if (window.location.hash === '#about') {
      document.getElementById('about')?.scrollIntoView({ behavior: 'smooth' })
    }
  }, [])

  return (
    <>
      {/* Public navbar */}
      <header className="navbar">
        <Link href="/" className="brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/logo.png" alt="EduConnect" />
          <span>EduConnect</span>
        </Link>
        <nav>
          <Link href="/">Home</Link>
          <a href="#features">Features</a>
          <a href="#about">About</a>
          <Link href="/auth">Log in / Register</Link>
        </nav>
      </header>

      <main className="app-main">
        {/* ── Hero ───────────────────────────────────────── */}
        <section id="hero" className="section lp-hero">
          <div className="hero-bg" aria-hidden="true">
            <span className="blob blob-1" />
            <span className="blob blob-2" />
            <span className="blob blob-3" />
          </div>

          <span className="lp-badge">
            <span className="lp-badge-dot" /> EduConnect 2.0 is here
          </span>

          <h1 className="lp-title">
            The AI-Powered Operating System for <span className="grad-text">Physical Schools</span>
          </h1>

          <p className="lp-sub">
            One platform connecting Directors, Principals, Teachers, Students and Parents —
            from attendance to analytics. Run your entire campus on autopilot.
          </p>

          <div className="cta-row">
            <Link href="/auth" className="btn btn-primary">Get started free</Link>
            <a href="#features" className="btn btn-outline">Explore features</a>
          </div>

          <dl className="lp-stats">
            {STATS.map((s) => (
              <div key={s.label} className="lp-stat">
                <dt>{s.label}</dt>
                <dd>{s.value}</dd>
              </div>
            ))}
          </dl>
        </section>

        {/* ── Features (bento grid) ──────────────────────── */}
        <section id="features" className="section">
          <div className="lp-head">
            <h2>A Unified Toolkit for the Modern Campus</h2>
            <p>Everything you need to run a physical school, seamlessly integrated and powered by intelligent automation.</p>
          </div>

          <div className="bento">
            {BENTO.map((f) => (
              <article key={f.title} className={`bento-card${f.large ? ' bento-lg' : ''}`}>
                <div className="bento-icon">{f.icon}</div>
                <h3>{f.title}</h3>
                <p>{f.text}</p>
                {f.quote && (
                  <div className="bento-quote"><em>{f.quote}</em></div>
                )}
              </article>
            ))}
          </div>
        </section>

        {/* ── About ──────────────────────────────────────── */}
        <section id="about" className="section about">
          <h2>About EduConnect</h2>
          <p className="about-lead">
            EduConnect is a <strong>school operating system</strong> — it automates the complete
            workflow of a school in one secure platform.
          </p>
          <ul className="about-list">
            {ABOUT_POINTS.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </section>
      </main>

      {/* Footer */}
      <footer className="footer">
        <span>© {new Date().getFullYear()} EduConnect — Automation of Schools Workflow</span>
        <span><Link href="/">Home</Link> · <a href="#about">About</a></span>
      </footer>
    </>
  )
}