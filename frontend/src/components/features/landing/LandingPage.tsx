"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRevealOnScroll } from "./useReveal";
import ParticleField from "./ParticleField";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

// ============================================================
// PAGE 02 — Public Landing page (Framer-style motion layer:
// cursor-follow glow, floating glass mockups, count-up stats,
// trust marquee, scroll reveals — all zero-dependency).
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

interface BentoItem {
    icon: string;
    title: string;
    text: string;
    quote?: string;
    large?: boolean;
}

const BENTO: BentoItem[] = [
    {
        icon: "🤖",
        title: "AI Assistant Copilot",
        text: "Your 24/7 administrative partner. Automate routine parent queries, draft personalized reports, and summarize meeting notes instantly.",
        quote: '"Draft an email to parents regarding tomorrow\'s schedule change…"',
        large: true,
    },
    {
        icon: "✅",
        title: "Smart Attendance",
        text: "Frictionless tracking for physical classrooms with automated anomaly detection for absenteeism.",
    },
    {
        icon: "📊",
        title: "Deep Analytics",
        text: "Transform data into action. Gain comprehensive insights into academic performance and operational efficiency.",
    },
    {
        icon: "💰",
        title: "Transparent Fees",
        text: "Online payments, instant receipts and live dues tracking — no more ledger registers.",
    },
    {
        icon: "💬",
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

const MOCKUPS = [
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

export default function LandingPage() {
    const glowRef = useRef<HTMLSpanElement>(null);
    useRevealOnScroll();

    useEffect(() => {
        if (window.location.hash === "#features") {
            document.getElementById("features")?.scrollIntoView({ behavior: "smooth" });
        }
        if (window.location.hash === "#about") {
            document.getElementById("about")?.scrollIntoView({ behavior: "smooth" });
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
                <ParticleField />
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
                        <a href="#features">Features</a>
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

                        {/* Floating glass product mockups */}
                        <div className="lp-mockups" aria-hidden="true">
                            {MOCKUPS.map((m) => (
                                <div key={m.head} className="mock-card">
                                    <div className="mock-head">
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

                        <dl className="lp-stats">
                            {STATS.map((s) => (
                                <div key={s.label} className="lp-stat">
                                    <dt>{s.label}</dt>
                                    <dd>
                                        <Counter value={s.value} />
                                    </dd>
                                </div>
                            ))}
                        </dl>

                        {/* Trust marquee */}
                        <div className="marquee" aria-hidden="true">
                            <div className="marquee-track">
                                {[...SCHOOLS, ...SCHOOLS].map((name, i) => (
                                    <span key={`${name}-${i}`}>◆ {name}</span>
                                ))}
                            </div>
                        </div>
                    </section>

                    {/* ── Features (bento grid) ──────────────────────── */}
                    <section id="features" className="section">
                        <div className="lp-head reveal">
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
                                    <div className="bento-icon">{f.icon}</div>
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

                    {/* ── About ──────────────────────────────────────── */}
                    <section id="about" className="section about">
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
                    <span>
                        © {new Date().getFullYear()} EduConnect — Automation of Schools Workflow
                    </span>
                    <span>
                        <Link href="/">Home</Link> · <a href="#about">About</a>
                    </span>
                </footer>
            </div>
        </>
    );
}
