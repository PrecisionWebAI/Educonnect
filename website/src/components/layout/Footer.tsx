"use client";

import React, { useState } from "react";
import { CheckCircle, GraduationCap, Mail, Phone, Send, ShieldCheck } from "lucide-react";

const APP_AUTH_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

const PRODUCT_LINKS = [
    { href: "#modules", label: "Modules" },
    { href: "#roles", label: "Roles" },
    { href: "#pricing", label: "Pricing" },
    { href: "#calculator", label: "ROI Calculator" },
    { href: "#faq", label: "FAQ" },
    { href: APP_AUTH_URL, label: "Log in", external: true },
];

const ARCHITECTURE_LINKS = [
    { href: "#modules", label: "Campus Intelligence Modules" },
    { href: "#roles", label: "Executive Command Suite" },
    { href: "#roles", label: "Faculty Copilot" },
    { href: "#roles", label: "Safety & Telemetry Protocol" },
    { href: "#how-it-works", label: "Implementation Playbook" },
];

const linkClass =
    "text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-white transition-colors hover:translate-x-1 duration-150 inline-block font-mono";

export default function Footer() {
    const [email, setEmail] = useState("");
    const [subscribed, setSubscribed] = useState(false);

    const onSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        if (!email.trim()) return;
        setSubscribed(true);
        setEmail("");
    };

    return (
        <footer className="w-full bg-slate-100/90 dark:bg-slate-950 border-t border-slate-200/80 dark:border-white/10 transition-colors duration-300">
            <div className="max-w-7xl mx-auto px-6 py-12 sm:py-14 w-full">
                <div className="grid grid-cols-1 md:grid-cols-12 gap-10 mb-12">
                    {/* Brand Info */}
                    <div className="md:col-span-4">
                        <div className="flex items-center gap-2 mb-4">
                            <div className="w-7 h-7 rounded-lg bg-blue-600 text-white flex items-center justify-center shadow-sm">
                                <GraduationCap size={16} />
                            </div>
                            <span className="text-lg font-extrabold text-blue-700 dark:text-white tracking-tight font-heading">
                                EduConnect
                            </span>
                        </div>
                        <p className="text-slate-600 dark:text-slate-300 text-xs mb-4 leading-relaxed">
                            The AI-powered operating system for physical schools — from attendance to analytics, on one
                            platform.
                        </p>
                        <p className="text-xs text-slate-500 dark:text-slate-400 font-medium font-mono">
                            Bengaluru, India
                        </p>
                    </div>

                    {/* Product Directory Links */}
                    <div className="md:col-span-2">
                        <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-4 font-mono">
                            Product
                        </h4>
                        <ul className="space-y-2.5 text-xs">
                            {PRODUCT_LINKS.map((link) => (
                                <li key={link.label}>
                                    <a
                                        className={linkClass}
                                        href={link.href}
                                        {...(link.external
                                            ? { target: "_blank", rel: "noopener noreferrer" }
                                            : {})}
                                    >
                                        {link.label}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Institutional Links */}
                    <div className="md:col-span-3">
                        <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-4 font-mono">
                            Architecture
                        </h4>
                        <ul className="space-y-2.5 text-xs">
                            {ARCHITECTURE_LINKS.map((link) => (
                                <li key={link.label}>
                                    <a className={linkClass} href={link.href}>
                                        {link.label}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    </div>

                    {/* Newsletter + Contact */}
                    <div className="md:col-span-3">
                        <h4 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider mb-4 font-mono">
                            Campus Dispatch
                        </h4>
                        <p className="text-xs text-slate-600 dark:text-slate-300 mb-3 leading-relaxed">
                            Monthly notes on school operations, AI in classrooms and rollout playbooks.
                        </p>

                        {subscribed ? (
                            <div className="flex items-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-3 text-xs font-semibold text-emerald-700 dark:text-emerald-300 font-mono">
                                <CheckCircle size={15} />
                                You&apos;re on the list. Talk soon!
                            </div>
                        ) : (
                            <form className="flex items-stretch gap-2" onSubmit={onSubmit}>
                                <label className="sr-only" htmlFor="footer-email">
                                    Work email
                                </label>
                                <input
                                    id="footer-email"
                                    type="email"
                                    required
                                    value={email}
                                    onChange={(event) => setEmail(event.target.value)}
                                    placeholder="you@school.edu"
                                    className="min-w-0 flex-1 rounded-lg border border-slate-200 dark:border-white/10 bg-white/90 dark:bg-slate-900 px-3 py-2.5 text-xs text-slate-900 dark:text-white placeholder:text-slate-400 outline-none transition-all focus:border-blue-600 dark:focus:border-sky-400 font-mono"
                                />
                                <button
                                    type="submit"
                                    aria-label="Subscribe to the campus dispatch"
                                    className="inline-flex items-center justify-center rounded-lg bg-blue-600 hover:bg-blue-700 px-3 py-2.5 text-white shadow-md transition-all hover:-translate-y-0.5 active:scale-95 glow-parchment"
                                >
                                    <Send size={15} />
                                </button>
                            </form>
                        )}

                        <div className="mt-5 space-y-2 text-xs text-slate-600 dark:text-slate-300 font-mono">
                            <p className="flex items-center gap-2">
                                <Mail size={14} />
                                <a
                                    className="hover:text-blue-600 dark:hover:text-white transition-colors"
                                    href="mailto:hello@educonnect.school"
                                >
                                    hello@educonnect.school
                                </a>
                            </p>
                            <p className="flex items-center gap-2">
                                <Phone size={14} />
                                <a
                                    className="hover:text-blue-600 dark:hover:text-white transition-colors"
                                    href="tel:+919876543210"
                                >
                                    +91 98765 43210
                                </a>
                            </p>
                        </div>
                    </div>
                </div>

                {/* Legal & Copyright Bar */}
                <div className="pt-8 border-t border-slate-200 dark:border-white/10 flex flex-col md:flex-row justify-between items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                    <p className="text-center md:text-left leading-relaxed">
                        © {new Date().getFullYear()} EduConnect Operating System Inc. Architecting intelligent campus
                        infrastructure. All rights reserved.
                    </p>
                    <div className="flex flex-wrap items-center justify-center gap-4">
                        <span className="inline-flex items-center gap-1.5 font-mono">
                            <ShieldCheck size={14} className="text-emerald-500 dark:text-emerald-400" />
                            ISO 27001 · FERPA · GDPR aligned
                        </span>
                        <span className="hidden sm:inline font-mono">
                            Zero-paperwork operations for physical schools
                        </span>
                    </div>
                </div>
            </div>
        </footer>
    );
}
