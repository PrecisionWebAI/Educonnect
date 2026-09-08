"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
    ArrowRight,
    Bot,
    CalendarCheck,
    ClipboardList,
    GraduationCap,
    HeartHandshake,
    Landmark,
    LayoutDashboard,
    Mail,
    MapPin,
    MessageSquare,
    Phone,
    Presentation,
    School,
    Sparkles,
    Star,
    TrendingUp,
    UserCog,
    Users,
    Wallet,
    Workflow,
} from "lucide-react";
import { useRevealOnScroll } from "./useReveal";
import ParticleField from "./ParticleField";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

// ============================================================
// PAGE 02 — Public Landing page (Framer-style motion layer:
// cursor-follow glow, CSS-drawn product window mockup,
// count-up stats, trust marquee, scroll reveals — zero deps).
// ============================================================

const STATS = [
    { value: "500+", label: "Schools onboard" },
    { value: "2.5L+", label: "Students managed" },
    { value: "99.9%", label: "Uptime" },
    { value: "40%", label: "Admin work saved" },
];

/** Count-up number that animates when scrolled into view. */
function Counter({ value }: { value: string }) {
    const num = parseFloat(value.replace(/[^0-9.]/g, ""));
    const suffix = value.replace(/[0-9.,]/g, "");
    const ref = useRef<HTMLSpanElement>(null);
    const [display, setDisplay] = useState("0");
    const decimals = num % 1 !== 0 ? 1 : 0;

    useEffect(() => {
        const el = ref.current;
        if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            setDisplay(String(num));
            return;
        }
        const io = new IntersectionObserver(
            ([entry]) => {
                if (!entry?.isIntersecting) return;
                io.disconnect();
                const dur = 950;
                const start = performance.now();
                const tick = (t: number) => {
                    const p = Math.min(1, (t - start) / dur);
                    const eased = 1 - Math.pow(1 - p, 3);
                    setDisplay((num * eased).toFixed(decimals));
                    if (p < 1) requestAnimationFrame(tick);
                };
                requestAnimationFrame(tick);
            },
            { threshold: 0.4 },
        );
        io.observe(el);
        return () => io.disconnect();
    }, [num, decimals]);

    return (
        <span ref={ref}>
            {display}
            {suffix}
        </span>
    );
}

const SCHOOLS = [
    "Sunrise Public School",
    "Green Valley Academy",
    "St. Xavier High",
    "Nova International",
    "Little Flowers School",
    "Prime Scholars",
    "Riverdale Public",
    "Bright Future Academy",
];

type IconCmp = React.ComponentType<{ size?: number; strokeWidth?: number }>;

interface BentoItem {
    icon: IconCmp;
    title: string;
    text: string;
    quote?: string;
    large?: boolean;
}

const BENTO: BentoItem[] = [
    {
        icon: Bot,
        title: "AI Assistant Copilot",
        text: "Your 24/7 administrative partner. Automate routine parent queries, draft personalized reports, and summarize meeting notes instantly.",
        quote: '"Draft an email to parents regarding tomorrow\'s schedule change…"',
        large: true,
    },
    {
        icon: CalendarCheck,
        title: "Smart Attendance",
        text: "Frictionless tracking for physical classrooms with automated anomaly detection for absenteeism.",
    },
    {
        icon: TrendingUp,
        title: "Deep Analytics",
        text: "Transform data into action. Gain comprehensive insights into academic performance and operational efficiency.",
    },
    {
        icon: Wallet,
        title: "Transparent Fees",
        text: "Online payments, instant receipts and live dues tracking — no more ledger registers.",
    },
    {
        icon: MessageSquare,
        title: "Unified Comms",
        text: "Secure, real-time messaging connecting teachers, parents, and students in one centralized hub.",
    },
];

const ABOUT_POINTS = [
    "Attendance, marks, exams and report cards — one screen for every teacher",
    "Fees, receipts, budgets, payroll and payslips for the finance team",
    "Library, transport, leave & applications — all workflows online",
    "Parent–teacher meetings, chat, tickets and role-based notifications",
    "Reports, analytics and AI Copilot for smarter school decisions",
];

/* Product window — mini sidebar icons (first one is "active") */
const WIN_SIDE: IconCmp[] = [LayoutDashboard, CalendarCheck, Wallet, ClipboardList, MessageSquare];

/* KPI tiles rendered with the animated Counter */
const KPIS = [
    { label: "Fee collected", prefix: "₹", value: "4.2L" },
    { label: "Attendance", prefix: "", value: "96%" },
    { label: "Dues", prefix: "₹", value: "38K" },
    { label: "Open tickets", prefix: "", value: "5" },
];

/* CSS bar chart — heights in %, grow in on reveal */
const CHART_BARS = [32, 48, 40, 62, 55, 78, 66, 92];

/* "Today" feed — the original mock-card content, now inside the window */
const TODAY_FEED = [
    {
        head: "Attendance — 8A · Live",
        rows: [
            { k: "Present", v: "38 / 42", cls: "up" },
            { k: "Absent", v: "3", cls: "down" },
            { k: "Late", v: "1", cls: "" },
        ],
    },
    {
        head: "Fee receipt · #REC-2291",
        rows: [
            { k: "Tuition (Q2)", v: "₹18,500", cls: "" },
            { k: "Status", v: "Paid · UPI", cls: "up" },
            { k: "Dues", v: "₹0", cls: "up" },
        ],
    },
    {
        head: "AI Copilot · Suggestion",
        rows: [
            { k: "Task", v: "Fee reminder", cls: "" },
            { k: "Audience", v: "12 parents", cls: "" },
            { k: "Draft", v: "Ready → Send", cls: "up" },
        ],
    },
];

const ROLES: { icon: IconCmp; title: string; text: string }[] = [
    {
        icon: Landmark,
        title: "Directors",
        text: "Full-campus visibility — fees, attendance, analytics and AI insights in one dashboard.",
    },
    {
        icon: UserCog,
        title: "Principals",
        text: "Approvals, timetables, teacher workload and daily operations on autopilot.",
    },
    {
        icon: Presentation,
        title: "Teachers",
        text: "Attendance, marks, homework and parent chat — one screen, zero paperwork.",
    },
    {
        icon: GraduationCap,
        title: "Students",
        text: "Diary, homework, exams, library and transport — everything in one place.",
    },
    {
        icon: HeartHandshake,
        title: "Parents",
        text: "Live attendance, fee payments, PTMs and direct messaging with teachers.",
    },
];

const HOW_STEPS = [
    {
        num: "01",
        title: "Onboard",
        text: "Import students, staff and fee structures in days — our team handles the migration.",
    },
    {
        num: "02",
        title: "Configure",
        text: "Tailor attendance rules, fee heads, roles and permissions to your campus.",
    },
    {
        num: "03",
        title: "Automate",
        text: "AI Copilot and workflows run reminders, receipts, reports and follow-ups.",
    },
    {
        num: "04",
        title: "Analyze",
        text: "Live dashboards turn daily activity into decisions for directors and principals.",
    },
];

const TESTIMONIALS = [
    {
        quote: "Fee collection is fully transparent now — receipts, dues and reminders run themselves. Our office workload dropped by half.",
        name: "Meera Nair",
        role: "Director · Sunrise Public School",
        initials: "MN",
    },
    {
        quote: "Attendance to report cards on one screen. My teachers finally spend their time teaching, not on registers.",
        name: "Rajesh Iyer",
        role: "Principal · Green Valley Academy",
        initials: "RI",
    },
    {
        quote: "Parents message me directly and get answers the same day. The AI Copilot drafts all the routine replies.",
        name: "Anita Sharma",
        role: "Teacher · St. Xavier High",
        initials: "AS",
    },
];

const FOOTER_COLS: { title: string; links: { label: string; href: string }[] }[] = [
    {
        title: "Product",
        links: [
            { label: "Modules", href: "#modules" },
            { label: "Roles", href: "#roles" },
            { label: "How it works", href: "#how" },
            { label: "Log in", href: "/auth" },
        ],
    },
    {
        title: "Company",
        links: [
            { label: "About", href: "#about" },
            { label: "Home", href: "/" },
            { label: "Register", href: "/auth" },
        ],
    },
];

export default function LandingPage() {
    const glowRef = useRef<HTMLSpanElement>(null);
    useRevealOnScroll();

    useEffect(() => {
        const ids = ["modules", "roles", "how", "testimonials", "about"];
        const id = window.location.hash.replace("#", "");
        if (ids.includes(id)) {
            document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
        }
    }, []);

    return (
        <>
            <div
                className="lp-root"
                onMouseMove={(e) => {
                    // instant transform follow — no lag, never clipped
                    glowRef.current?.style.setProperty(
                        "transform",
                        `translate3d(${e.clientX - 320}px, ${e.clientY - 320}px, 0)`,
                    );
                }}
            >
                {/* Galaxy background — full page width, hero-scoped height, scrolls with page */}
                <ParticleField speed={0.5} />
                {/* Cursor glow — fixed viewport layer, above canvas, below content */}
                <span className="hero-glow" ref={glowRef} aria-hidden="true" />

                {/* Public navbar */}
                <header className="navbar">
                    <Link href="/" className="brand">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src="/logo.png" alt="EduConnect" />
                        <span>EduConnect</span>
                    </Link>
                    <nav>
                        <Link href="/">Home</Link>
                        <a href="#roles">Roles</a>
                        <a href="#modules">Modules</a>
                        <a href="#how">How it works</a>
                        <a href="#about">About</a>
                        <Link href="/auth">Log in / Register</Link>
                        <ThemeToggle />
                    </nav>
                </header>

                <main className="app-main">
                    {/* ── Hero ───────────────────────────────────────── */}
                    <section id="hero" className="section lp-hero">
                        <div className="hero-bg" aria-hidden="true" />

                        <span className="lp-badge">
                            <span className="lp-badge-dot" /> EduConnect 2.0 is here
                        </span>

                        <h1 className="lp-title">
                            <span className="w" style={{ "--d": "0.05s" } as React.CSSProperties}>
                                The
                            </span>{" "}
                            <span className="w" style={{ "--d": "0.14s" } as React.CSSProperties}>
                                AI-Powered
                            </span>{" "}
                            <span className="w" style={{ "--d": "0.23s" } as React.CSSProperties}>
                                Operating
                            </span>{" "}
                            <span className="w" style={{ "--d": "0.32s" } as React.CSSProperties}>
                                System
                            </span>{" "}
                            <span className="w" style={{ "--d": "0.41s" } as React.CSSProperties}>
                                for
                            </span>{" "}
                            <span
                                className="grad-text w"
                                style={{ "--d": "0.5s" } as React.CSSProperties}
                            >
                                Physical Schools
                            </span>
                        </h1>

                        <p className="lp-sub">
                            One platform connecting Directors, Principals, Teachers, Students and
                            Parents — from attendance to analytics. Run your entire campus on
                            autopilot.
                        </p>

                        <div className="cta-row">
                            <Link href="/auth" className="btn btn-primary">
                                Get started free
                            </Link>
                            <a href="#features" className="btn btn-outline">
                                Explore features
                            </a>
                        </div>

                        {/* Product window mockup — CSS-drawn director dashboard */}
                        <div className="lp-window reveal">
                            <div className="win-titlebar">
                                <span className="win-dots" aria-hidden="true">
                                    <i />
                                    <i />
                                    <i />
                                </span>
                                <span className="win-title">EduConnect — Director Dashboard</span>
                            </div>

                            <div className="win-body">
                                <aside className="win-side" aria-hidden="true">
                                    {WIN_SIDE.map((Icon, i) => (
                                        <span
                                            key={i}
                                            className={`win-side-icon${i === 0 ? "active" : ""}`}
                                        >
                                            <Icon size={17} strokeWidth={2} />
                                        </span>
                                    ))}
                                </aside>

                                <div className="win-main">
                                    <div className="win-kpis">
                                        {KPIS.map((k) => (
                                            <div key={k.label} className="win-kpi">
                                                <span className="win-kpi-label">{k.label}</span>
                                                <span className="win-kpi-value">
                                                    {k.prefix}
                                                    <Counter value={k.value} />
                                                </span>
                                            </div>
                                        ))}
                                    </div>

                                    <div className="win-panels">
                                        <div className="win-chart" aria-hidden="true">
                                            <div className="win-chart-bars">
                                                {CHART_BARS.map((h, i) => (
                                                    <i
                                                        key={i}
                                                        style={
                                                            {
                                                                "--h": `${h}%`,
                                                                "--i": i,
                                                            } as React.CSSProperties
                                                        }
                                                    />
                                                ))}
                                            </div>
                                            <span className="win-chart-caption">
                                                Fee collection · last 8 weeks
                                            </span>
                                        </div>

                                        <div className="win-today">
                                            <div className="win-panel-title">Today</div>
                                            {TODAY_FEED.map((m) => (
                                                <div key={m.head} className="today-item">
                                                    <div className="today-head">
                                                        <span className="mock-dot" /> {m.head}
                                                    </div>
                                                    {m.rows.map((row) => (
                                                        <div key={row.k} className="mock-row">
                                                            <span>{row.k}</span>
                                                            <b className={row.cls}>{row.v}</b>
                                                        </div>
                                                    ))}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Stats band docked to the window's bottom edge */}
                            <dl className="lp-stats win-stats">
                                {STATS.map((s) => (
                                    <div key={s.label} className="lp-stat">
                                        <dt>{s.label}</dt>
                                        <dd>
                                            <Counter value={s.value} />
                                        </dd>
                                    </div>
                                ))}
                            </dl>
                        </div>

                        {/* Trust marquee */}
                        <div className="marquee" aria-hidden="true">
                            <div className="marquee-track">
                                {[...SCHOOLS, ...SCHOOLS].map((name, i) => (
                                    <span key={`${name}-${i}`}>◆ {name}</span>
                                ))}
                            </div>
                        </div>
                    </section>

                    {/* ── Roles ──────────────────────────────────────── */}
                    <section id="roles" className="section">
                        <div className="lp-head reveal">
                            <span className="eyebrow">
                                <Users size={13} /> Built for every role
                            </span>
                            <h2>One platform, five happy users</h2>
                            <p>
                                EduConnect gives each role exactly the tools they need — nothing
                                more, nothing missing.
                            </p>
                        </div>
                        <div className="roles">
                            {ROLES.map((r, i) => (
                                <article
                                    key={r.title}
                                    className={`reveal reveal-d${(i % 3) + 1} role-card`}
                                >
                                    <div className="role-icon">
                                        <r.icon size={22} strokeWidth={2} />
                                    </div>
                                    <h3>{r.title}</h3>
                                    <p>{r.text}</p>
                                </article>
                            ))}
                        </div>
                    </section>

                    {/* ── Modules (bento grid) ───────────────────────── */}
                    <section id="modules" className="section">
                        <div className="lp-head reveal">
                            <span className="eyebrow">
                                <Sparkles size={13} /> Modules
                            </span>
                            <h2>A Unified Toolkit for the Modern Campus</h2>
                            <p>
                                Everything you need to run a physical school, seamlessly integrated
                                and powered by intelligent automation.
                            </p>
                        </div>

                        <div className="bento">
                            {BENTO.map((f, i) => (
                                <article
                                    key={f.title}
                                    className={`reveal reveal-d${(i % 3) + 1} bento-card${f.large ? "bento-lg" : ""}`}
                                >
                                    <div className="bento-icon">
                                        <f.icon size={22} strokeWidth={2} />
                                    </div>
                                    <h3>{f.title}</h3>
                                    <p>{f.text}</p>
                                    {f.quote && (
                                        <div className="bento-quote">
                                            <em>{f.quote}</em>
                                        </div>
                                    )}
                                </article>
                            ))}
                        </div>
                    </section>

                    {/* ── How it works ───────────────────────────────── */}
                    <section id="how" className="section">
                        <div className="lp-head reveal">
                            <span className="eyebrow">
                                <Workflow size={13} /> How it works
                            </span>
                            <h2>Live in days, not months</h2>
                            <p>
                                From first import to full automation — a guided rollout your office
                                will actually enjoy.
                            </p>
                        </div>
                        <div className="how-steps">
                            {HOW_STEPS.map((s, i) => (
                                <div
                                    key={s.num}
                                    className={`reveal reveal-d${(i % 3) + 1} how-step`}
                                >
                                    <span className="how-num">{s.num}</span>
                                    <h3>{s.title}</h3>
                                    <p>{s.text}</p>
                                </div>
                            ))}
                        </div>
                    </section>

                    {/* ── Testimonials ───────────────────────────────── */}
                    <section id="testimonials" className="section">
                        <div className="lp-head reveal">
                            <span className="eyebrow">
                                <Star size={13} /> Loved by campuses
                            </span>
                            <h2>Schools that run on EduConnect</h2>
                            <p>
                                Directors, principals and teachers on what changed after switching.
                            </p>
                        </div>
                        <div className="testimonials">
                            {TESTIMONIALS.map((t, i) => (
                                <figure
                                    key={t.name}
                                    className={`reveal reveal-d${(i % 3) + 1} t-card`}
                                >
                                    <div className="t-stars" aria-label="Rated 5 out of 5">
                                        {Array.from({ length: 5 }).map((_, si) => (
                                            <Star
                                                key={si}
                                                size={13}
                                                fill="currentColor"
                                                strokeWidth={0}
                                            />
                                        ))}
                                    </div>
                                    <blockquote className="t-quote">
                                        &ldquo;{t.quote}&rdquo;
                                    </blockquote>
                                    <figcaption className="t-person">
                                        <span className="t-avatar" aria-hidden="true">
                                            {t.initials}
                                        </span>
                                        <span>
                                            <b>{t.name}</b>
                                            <em>{t.role}</em>
                                        </span>
                                    </figcaption>
                                </figure>
                            ))}
                        </div>
                    </section>

                    {/* ── Final CTA band ─────────────────────────────── */}
                    <section className="section">
                        <div className="cta-band reveal">
                            <h2>Ready to run your school on autopilot?</h2>
                            <p>
                                Join 500+ schools automating attendance, fees and communication with
                                EduConnect.
                            </p>
                            <div className="cta-row">
                                <Link href="/auth" className="btn btn-invert">
                                    Get started free <ArrowRight size={16} />
                                </Link>
                                <a href="#modules" className="btn btn-ghost-light">
                                    Explore modules
                                </a>
                            </div>
                        </div>
                    </section>

                    {/* ── About ──────────────────────────────────────── */}
                    <section id="about" className="section about">
                        <span className="eyebrow reveal">
                            <School size={13} /> About
                        </span>
                        <h2 className="reveal">About EduConnect</h2>
                        <p className="about-lead reveal reveal-d1">
                            EduConnect is a <strong>school operating system</strong> — it automates
                            the complete workflow of a school in one secure platform.
                        </p>
                        <ul className="about-list reveal reveal-d2">
                            {ABOUT_POINTS.map((point) => (
                                <li key={point}>{point}</li>
                            ))}
                        </ul>
                    </section>
                </main>

                {/* Footer */}
                <footer className="footer">
                    <div className="footer-cols">
                        <div className="footer-brand">
                            <Link href="/" className="brand">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img src="/logo.png" alt="EduConnect" />
                                <span>EduConnect</span>
                            </Link>
                            <p>
                                The AI-powered operating system for physical schools — from
                                attendance to analytics, on one platform.
                            </p>
                        </div>
                        {FOOTER_COLS.map((col) => (
                            <div key={col.title} className="footer-col">
                                <h4>{col.title}</h4>
                                {col.links.map((l) =>
                                    l.href.startsWith("#") ? (
                                        <a key={l.label} href={l.href}>
                                            {l.label}
                                        </a>
                                    ) : (
                                        <Link key={l.label} href={l.href}>
                                            {l.label}
                                        </Link>
                                    ),
                                )}
                            </div>
                        ))}
                        <div className="footer-col">
                            <h4>Get in touch</h4>
                            <a href="mailto:hello@educonnect.school">
                                <Mail size={13} /> hello@educonnect.school
                            </a>
                            <a href="tel:+919876543210">
                                <Phone size={13} /> +91 98765 43210
                            </a>
                            <span>
                                <MapPin size={13} /> Bengaluru, India
                            </span>
                        </div>
                    </div>
                    <div className="footer-base">
                        <span>
                            © {new Date().getFullYear()} EduConnect — Automation of Schools Workflow
                        </span>
                        <span>Zero-paperwork operations for physical schools</span>
                    </div>
                </footer>
            </div>
        </>
    );
}
