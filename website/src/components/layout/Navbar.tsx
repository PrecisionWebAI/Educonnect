"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowRight, GraduationCap, Menu, X } from "lucide-react";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { cn } from "@/lib/utils";

const APP_AUTH_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

const NAV_LINKS = [
    { href: "#roles", label: "Roles" },
    { href: "#modules", label: "Modules" },
    { href: "#pricing", label: "Pricing" },
    { href: "#calculator", label: "ROI Calculator" },
    { href: "#how-it-works", label: "How it works" },
    { href: "#faq", label: "FAQ" },
    { href: "#about", label: "About" },
];

/**
 * Floating glass navigation bar.
 *  • scroll-progress rail at the very top of the viewport
 *  • active-section highlighting via IntersectionObserver
 *  • fully responsive drawer for small screens (Esc to close, body scroll lock)
 */
export default function Navbar() {
    const [open, setOpen] = useState(false);
    const [scrolled, setScrolled] = useState(false);
    const [progress, setProgress] = useState(0);
    const [active, setActive] = useState("");
    const frame = useRef<number | null>(null);

    // Scroll progress + condensed state (rAF-throttled).
    useEffect(() => {
        const onScroll = () => {
            if (frame.current !== null) return;
            frame.current = window.requestAnimationFrame(() => {
                frame.current = null;
                const doc = document.documentElement;
                const max = doc.scrollHeight - window.innerHeight;
                setProgress(max > 0 ? Math.min(100, (window.scrollY / max) * 100) : 0);
                setScrolled(window.scrollY > 24);
            });
        };
        onScroll();
        window.addEventListener("scroll", onScroll, { passive: true });
        return () => {
            window.removeEventListener("scroll", onScroll);
            if (frame.current !== null) window.cancelAnimationFrame(frame.current);
        };
    }, []);

    // Highlight the section currently in view.
    useEffect(() => {
        const sections = NAV_LINKS.map((link) => document.getElementById(link.href.slice(1))).filter(
            (el): el is HTMLElement => Boolean(el),
        );
        if (!sections.length || !("IntersectionObserver" in window)) return;
        const io = new IntersectionObserver(
            (entries) => {
                const visible = entries
                    .filter((entry) => entry.isIntersecting)
                    .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
                if (visible?.target.id) setActive(visible.target.id);
            },
            { rootMargin: "-45% 0px -45% 0px", threshold: [0, 0.25, 0.5, 1] },
        );
        sections.forEach((section) => io.observe(section));
        return () => io.disconnect();
    }, []);

    // Body scroll lock + Escape-to-close while the drawer is open.
    useEffect(() => {
        if (!open) return;
        const previous = document.body.style.overflow;
        document.body.style.overflow = "hidden";
        const onKeyDown = (event: KeyboardEvent) => {
            if (event.key === "Escape") setOpen(false);
        };
        window.addEventListener("keydown", onKeyDown);
        return () => {
            document.body.style.overflow = previous;
            window.removeEventListener("keydown", onKeyDown);
        };
    }, [open]);

    const linkClass = (id: string) =>
        cn(
            "relative text-xs tracking-wider uppercase font-mono font-medium transition-all hover:-translate-y-0.5",
            active === id
                ? "text-blue-600 dark:text-sky-400 font-bold"
                : "text-slate-600 dark:text-slate-300 hover:text-blue-600 dark:hover:text-white",
        );

    return (
        <>
            {/* Scroll progress rail */}
            <div
                className="fixed top-0 left-0 z-[60] h-0.5 w-full bg-transparent"
                aria-hidden="true"
            >
                <div
                    className="h-full bg-gradient-to-r from-blue-600 via-cyan-500 to-sky-400 dark:from-blue-500 dark:via-sky-400 dark:to-cyan-300 transition-[width] duration-150 ease-out"
                    style={{ width: `${progress}%` }}
                />
            </div>

            <header
                className={cn(
                    "fixed top-4 left-1/2 -translate-x-1/2 w-[calc(100%-2rem)] max-w-7xl rounded-xl z-50 border transition-all duration-300 glint-surface",
                    "bg-white/80 dark:bg-slate-900/85 backdrop-blur-xl border-white/80 dark:border-white/10",
                    scrolled
                        ? "shadow-2xl shadow-blue-900/10 dark:shadow-black/60"
                        : "shadow-lg shadow-blue-900/5 dark:shadow-black/30",
                )}
            >
                <div className="flex justify-between items-center gap-4 px-5 sm:px-6 py-3.5 w-full">
                    {/* Brand Anchor */}
                    <Link className="flex items-center gap-2.5 group shrink-0" href="/">
                        <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-600/30 transition-all group-hover:scale-105 group-hover:rotate-3">
                            <GraduationCap size={18} />
                        </div>
                        <span className="text-base sm:text-lg font-extrabold text-blue-700 dark:text-white tracking-tight transition-colors font-heading">
                            EduConnect OS
                        </span>
                    </Link>

                    {/* Desktop Navigation Links */}
                    <nav className="hidden lg:flex items-center gap-6 xl:gap-8">
                        {NAV_LINKS.map((link) => {
                            const id = link.href.slice(1);
                            return (
                                <a key={link.href} className={linkClass(id)} href={link.href}>
                                    {link.label}
                                    <span
                                        className={cn(
                                            "absolute -bottom-1.5 left-0 h-0.5 rounded-full bg-blue-600 dark:bg-sky-400 transition-all duration-300",
                                            active === id ? "w-full opacity-100" : "w-0 opacity-0",
                                        )}
                                    />
                                </a>
                            );
                        })}
                    </nav>

                    {/* Trailing Action Cluster */}
                    <div className="flex items-center gap-2 sm:gap-3 shrink-0">
                        <ThemeToggle />
                        <a
                            className="hidden sm:inline-flex items-center text-xs tracking-wider font-semibold text-slate-700 dark:text-slate-200 hover:text-blue-600 dark:hover:text-white px-3 py-2 transition-all hover:-translate-y-0.5 font-mono"
                            href={APP_AUTH_URL}
                        >
                            Log in
                        </a>
                        <a
                            className="hidden sm:inline-flex items-center justify-center text-xs tracking-wider font-bold px-4 py-2 rounded-lg bg-blue-600 text-white shadow-md shadow-blue-600/25 hover:bg-blue-700 transition-all hover:-translate-y-0.5 active:scale-[0.98] glow-parchment font-mono"
                            href={APP_AUTH_URL}
                        >
                            Get started free
                        </a>

                        {/* Mobile menu trigger */}
                        <button
                            type="button"
                            onClick={() => setOpen((value) => !value)}
                            aria-expanded={open}
                            aria-controls="educonnect-mobile-nav"
                            aria-label={open ? "Close navigation menu" : "Open navigation menu"}
                            className="lg:hidden inline-flex items-center justify-center w-10 h-10 rounded-lg border border-slate-200 dark:border-white/10 bg-white/80 dark:bg-slate-800/80 text-slate-800 dark:text-white transition-all hover:-translate-y-0.5 active:scale-95"
                        >
                            {open ? <X size={18} /> : <Menu size={18} />}
                        </button>
                    </div>
                </div>

                {/* Mobile drawer */}
                <div
                    id="educonnect-mobile-nav"
                    className={cn(
                        "lg:hidden overflow-hidden border-t transition-all duration-500 ease-out",
                        open
                            ? "max-h-[42rem] opacity-100 border-slate-200/80 dark:border-white/10"
                            : "max-h-0 opacity-0 border-transparent",
                    )}
                >
                    <nav className="flex flex-col gap-1 px-4 py-4 max-h-[calc(100vh-8rem)] overflow-y-auto">
                        {NAV_LINKS.map((link, index) => (
                            <a
                                key={link.href}
                                href={link.href}
                                onClick={() => setOpen(false)}
                                style={{ transitionDelay: open ? `${index * 40}ms` : "0ms" }}
                                className={cn(
                                    "flex items-center justify-between rounded-lg px-3 py-3 text-sm font-semibold transition-all font-mono",
                                    "text-slate-800 dark:text-slate-100 hover:bg-blue-50 dark:hover:bg-slate-800/60",
                                    open ? "translate-x-0 opacity-100" : "-translate-x-3 opacity-0",
                                )}
                            >
                                <span className="tracking-wide uppercase text-xs">{link.label}</span>
                                <ArrowRight size={15} className="text-slate-400 dark:text-slate-400" />
                            </a>
                        ))}

                        <div className="mt-3 flex flex-col gap-2.5 border-t border-slate-200/80 dark:border-white/10 pt-4">
                            <a
                                href={APP_AUTH_URL}
                                onClick={() => setOpen(false)}
                                className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-200 dark:border-white/10 bg-white/80 dark:bg-slate-800/60 px-4 py-3 text-xs font-bold tracking-wide text-slate-800 dark:text-white transition-all hover:-translate-y-0.5 font-mono"
                            >
                                Log in
                            </a>
                            <a
                                href={APP_AUTH_URL}
                                onClick={() => setOpen(false)}
                                className="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-3 text-xs font-bold tracking-wide text-white shadow-md shadow-blue-600/25 transition-all hover:-translate-y-0.5 active:scale-[0.98] glow-parchment font-mono"
                            >
                                Get started free
                                <ArrowRight size={15} />
                            </a>
                        </div>
                    </nav>
                </div>
            </header>
        </>
    );
}
