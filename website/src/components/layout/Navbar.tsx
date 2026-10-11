"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import {
  ArrowRight,
  Calculator,
  ChevronDown,
  HelpCircle,
  Info,
  Layers,
  Menu,
  Shield,
  Workflow,
  X,
} from "lucide-react";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { cn } from "@/lib/utils";

const APP_AUTH_URL = process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000";

interface DropdownItem {
  href: string;
  label: string;
  description: string;
  icon: React.ElementType;
}

const PRODUCT_ITEMS: DropdownItem[] = [
  {
    href: "#roles",
    label: "Roles",
    description: "Tailored workspaces for Principals, Teachers & Parents",
    icon: Shield,
  },
  {
    href: "#modules",
    label: "Modules",
    description: "Attendance, exams, fees, transport & AI copilot",
    icon: Layers,
  },
  {
    href: "#how-it-works",
    label: "How it works",
    description: "Rapid 3-step school onboarding & ERP migration",
    icon: Workflow,
  },
];

const RESOURCE_ITEMS: DropdownItem[] = [
  {
    href: "#calculator",
    label: "ROI Calculator",
    description: "Calculate staff hours and tuition fee recovery",
    icon: Calculator,
  },
  {
    href: "#faq",
    label: "FAQ",
    description: "Data security, migration, compliance & timelines",
    icon: HelpCircle,
  },
  {
    href: "#about",
    label: "About",
    description: "Our mission, leadership, and institutional standards",
    icon: Info,
  },
];

/**
 * Consolidated header & navigation bar with Product/Resources dropdowns
 * and prominent 'Get started free' primary CTA.
 */
export default function Navbar() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [progress, setProgress] = useState(0);
  const [active, setActive] = useState("");
  const [openDropdown, setOpenDropdown] = useState<
    "product" | "resources" | null
  >(null);
  const [mobileProductOpen, setMobileProductOpen] = useState(true);
  const [mobileResourcesOpen, setMobileResourcesOpen] = useState(false);
  const closeTimeoutRef = useRef<NodeJS.Timeout | null>(null);
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
    const allHrefs = [
      ...PRODUCT_ITEMS.map((i) => i.href),
      "#pricing",
      ...RESOURCE_ITEMS.map((i) => i.href),
    ];
    const sections = allHrefs
      .map((href) => document.getElementById(href.slice(1)))
      .filter((el): el is HTMLElement => Boolean(el));

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

  // Body scroll lock + Escape-to-close while the mobile drawer is open.
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

  // Handle mouse enter for dropdowns with debounce cancellation
  const handleMouseEnter = (menu: "product" | "resources") => {
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }
    setOpenDropdown(menu);
  };

  // Handle mouse leave with small grace period
  const handleMouseLeave = () => {
    closeTimeoutRef.current = setTimeout(() => {
      setOpenDropdown(null);
    }, 150);
  };

  const isProductActive = PRODUCT_ITEMS.some((i) => active === i.href.slice(1));
  const isResourceActive = RESOURCE_ITEMS.some(
    (i) => active === i.href.slice(1),
  );

  return (
    <>
      {/* Scroll progress rail */}
      <div
        className="fixed top-0 left-0 z-[60] h-0.5 w-full bg-transparent"
        aria-hidden="true"
      >
        <div
          className="h-full bg-[#99753a] transition-[width] duration-150 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      <header
        className={cn(
          "fixed top-4 left-1/2 z-50 w-[calc(100%-2rem)] max-w-7xl -translate-x-1/2 rounded-2xl border transition-all duration-300",
          "border-slate-200/80 bg-white/95 backdrop-blur-md dark:border-white/10 dark:bg-[#0B1221]/95",
          scrolled
            ? "shadow-md shadow-slate-200/50 dark:shadow-xl dark:shadow-black/40"
            : "shadow-sm dark:shadow-lg dark:shadow-black/25",
        )}
      >
        <div className="flex w-full items-center justify-between gap-4 px-5 py-3 sm:px-6">
          {/* Brand Anchor */}
          <Link className="group flex shrink-0 items-center gap-2.5" href="/">
            <Image
              src="/logo.png?v=2"
              alt="EduConnect"
              width={40}
              height={40}
              priority
              unoptimized
              className="h-8 w-8 object-contain transition-transform group-hover:scale-105"
            />
            <span className="font-heading text-base font-extrabold tracking-tight text-slate-900 transition-colors sm:text-lg dark:text-slate-50">
              EduConnect
            </span>
          </Link>

          {/* Desktop Consolidated Navigation */}
          <nav className="hidden items-center gap-6 lg:flex xl:gap-8">
            {/* 1. Product Dropdown */}
            <div
              className="relative"
              onMouseEnter={() => handleMouseEnter("product")}
              onMouseLeave={handleMouseLeave}
            >
              <button
                type="button"
                onClick={() =>
                  setOpenDropdown(openDropdown === "product" ? null : "product")
                }
                aria-expanded={openDropdown === "product"}
                aria-haspopup="true"
                className={cn(
                  "inline-flex items-center gap-1.5 py-2 text-sm font-medium transition-colors",
                  isProductActive || openDropdown === "product"
                    ? "font-semibold text-[#99753a]"
                    : "text-slate-600 hover:text-[#99753a] dark:text-slate-300",
                )}
              >
                <span>Product</span>
                <ChevronDown
                  size={14}
                  className={cn(
                    "transition-transform duration-200",
                    openDropdown === "product"
                      ? "rotate-180 text-[#99753a]"
                      : "text-slate-400 dark:text-slate-400",
                  )}
                />
              </button>

              {/* Dropdown Flyout */}
              <div
                className={cn(
                  "absolute top-full left-0 z-50 w-80 pt-2 transition-all duration-200",
                  openDropdown === "product"
                    ? "pointer-events-auto translate-y-0 opacity-100"
                    : "pointer-events-none -translate-y-2 opacity-0",
                )}
              >
                <div className="nav-dropdown-card space-y-1 rounded-2xl border border-slate-200 bg-white p-2 shadow-2xl shadow-slate-900/10 dark:border-white/10 dark:bg-[#131E3A] dark:shadow-black/60">
                  {PRODUCT_ITEMS.map((item) => {
                    const Icon = item.icon;
                    const isCurrent = active === item.href.slice(1);
                    return (
                      <a
                        key={item.href}
                        href={item.href}
                        onClick={() => setOpenDropdown(null)}
                        className={cn(
                          "group flex items-start gap-3 rounded-xl p-3 transition-all",
                          isCurrent
                            ? "bg-[#99753a]/10 dark:bg-[#1C294A]"
                            : "hover:bg-slate-100 dark:hover:bg-[#1C294A]/70",
                        )}
                      >
                        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#99753a]/10 text-[#99753a] transition-transform group-hover:scale-105 dark:border dark:border-white/5 dark:bg-[#0B1221]">
                          <Icon size={16} />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-900 dark:text-slate-100">
                            <span>{item.label}</span>
                            <ArrowRight
                              size={12}
                              className="-translate-x-1 text-[#99753a] opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100"
                            />
                          </div>
                          <p className="mt-0.5 text-xs leading-snug text-slate-500 dark:text-slate-400">
                            {item.description}
                          </p>
                        </div>
                      </a>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* 2. Resources Dropdown */}
            <div
              className="relative"
              onMouseEnter={() => handleMouseEnter("resources")}
              onMouseLeave={handleMouseLeave}
            >
              <button
                type="button"
                onClick={() =>
                  setOpenDropdown(
                    openDropdown === "resources" ? null : "resources",
                  )
                }
                aria-expanded={openDropdown === "resources"}
                aria-haspopup="true"
                className={cn(
                  "inline-flex items-center gap-1.5 py-2 text-sm font-medium transition-colors",
                  isResourceActive || openDropdown === "resources"
                    ? "font-semibold text-[#99753a]"
                    : "text-slate-600 hover:text-[#99753a] dark:text-slate-300",
                )}
              >
                <span>Resources</span>
                <ChevronDown
                  size={14}
                  className={cn(
                    "transition-transform duration-200",
                    openDropdown === "resources"
                      ? "rotate-180 text-[#99753a]"
                      : "text-slate-400 dark:text-slate-400",
                  )}
                />
              </button>

              {/* Dropdown Flyout */}
              <div
                className={cn(
                  "absolute top-full left-0 z-50 w-80 pt-2 transition-all duration-200",
                  openDropdown === "resources"
                    ? "pointer-events-auto translate-y-0 opacity-100"
                    : "pointer-events-none -translate-y-2 opacity-0",
                )}
              >
                <div className="nav-dropdown-card space-y-1 rounded-2xl border border-slate-200 bg-white p-2 shadow-2xl shadow-slate-900/10 dark:border-white/10 dark:bg-[#131E3A] dark:shadow-black/60">
                  {RESOURCE_ITEMS.map((item) => {
                    const Icon = item.icon;
                    const isCurrent = active === item.href.slice(1);
                    return (
                      <a
                        key={item.href}
                        href={item.href}
                        onClick={() => setOpenDropdown(null)}
                        className={cn(
                          "group flex items-start gap-3 rounded-xl p-3 transition-all",
                          isCurrent
                            ? "bg-[#99753a]/10 dark:bg-[#1C294A]"
                            : "hover:bg-slate-100 dark:hover:bg-[#1C294A]/70",
                        )}
                      >
                        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-[#99753a]/10 text-[#99753a] transition-transform group-hover:scale-105 dark:border dark:border-white/5 dark:bg-[#0B1221]">
                          <Icon size={16} />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5 text-sm font-semibold text-slate-900 dark:text-slate-100">
                            <span>{item.label}</span>
                            <ArrowRight
                              size={12}
                              className="-translate-x-1 text-[#99753a] opacity-0 transition-all group-hover:translate-x-0 group-hover:opacity-100"
                            />
                          </div>
                          <p className="mt-0.5 text-xs leading-snug text-slate-500 dark:text-slate-400">
                            {item.description}
                          </p>
                        </div>
                      </a>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* 3. Standalone Pricing Link */}
            <a
              href="#pricing"
              className={cn(
                "relative py-2 text-sm font-medium transition-colors hover:text-[#99753a]",
                active === "pricing"
                  ? "font-semibold text-[#99753a]"
                  : "text-slate-600 dark:text-slate-300",
              )}
            >
              <span>Pricing</span>
              <span
                className={cn(
                  "absolute -bottom-1 left-0 h-0.5 rounded-full bg-[#99753a] transition-all duration-300",
                  active === "pricing" ? "w-full opacity-100" : "w-0 opacity-0",
                )}
              />
            </a>
          </nav>

          {/* Trailing Action Cluster */}
          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            <ThemeToggle />
            <a
              className="hidden items-center px-3 py-2 text-sm font-medium text-slate-700 transition-colors hover:text-[#99753a] sm:inline-flex dark:text-slate-300"
              href={APP_AUTH_URL}
            >
              Log in
            </a>
            <a
              className="inline-flex items-center justify-center rounded-xl bg-[#99753a] px-5 py-2.5 text-sm font-bold text-white shadow-md shadow-[#99753a]/25 transition-all hover:-translate-y-0.5 hover:bg-[#85632f] active:scale-[0.98] dark:shadow-md dark:shadow-black/40"
              href={APP_AUTH_URL}
            >
              <span>Get started free</span>
            </a>

            {/* Mobile menu trigger */}
            <button
              type="button"
              onClick={() => setOpen((value) => !value)}
              aria-expanded={open}
              aria-controls="educonnect-mobile-nav"
              aria-label={
                open ? "Close navigation menu" : "Open navigation menu"
              }
              className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white/80 text-slate-800 shadow-xs transition-all hover:-translate-y-0.5 active:scale-95 lg:hidden dark:border-white/10 dark:bg-[#1C294A] dark:text-slate-100"
            >
              {open ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>

        {/* Mobile Drawer */}
        <div
          id="educonnect-mobile-nav"
          className={cn(
            "overflow-hidden border-t transition-all duration-500 ease-out lg:hidden",
            open
              ? "max-h-[46rem] border-slate-200/80 bg-white/95 opacity-100 dark:border-white/10 dark:bg-[#131E3A]/95"
              : "max-h-0 border-transparent opacity-0",
          )}
        >
          <nav className="flex max-h-[calc(100vh-8rem)] flex-col gap-2 overflow-y-auto px-4 py-4">
            {/* Mobile Product Group */}
            <div className="rounded-xl border border-slate-200/70 bg-slate-50/60 p-2 dark:border-white/5 dark:bg-[#0B1221]">
              <button
                type="button"
                onClick={() => setMobileProductOpen(!mobileProductOpen)}
                className="flex w-full items-center justify-between px-3 py-2 text-xs font-bold tracking-wider text-slate-500 uppercase dark:text-[#99753a]"
              >
                <span>Product</span>
                <ChevronDown
                  size={14}
                  className={cn(
                    "transition-transform",
                    mobileProductOpen ? "rotate-180" : "",
                  )}
                />
              </button>
              {mobileProductOpen && (
                <div className="space-y-1 pt-1">
                  {PRODUCT_ITEMS.map((item) => (
                    <a
                      key={item.href}
                      href={item.href}
                      onClick={() => setOpen(false)}
                      className="flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium text-slate-800 hover:bg-white dark:text-slate-200 dark:hover:bg-[#1C294A]"
                    >
                      <span>{item.label}</span>
                      <ArrowRight
                        size={14}
                        className="text-slate-400 dark:text-slate-500"
                      />
                    </a>
                  ))}
                </div>
              )}
            </div>

            {/* Mobile Resources Group */}
            <div className="rounded-xl border border-slate-200/70 bg-slate-50/60 p-2 dark:border-white/5 dark:bg-[#0B1221]">
              <button
                type="button"
                onClick={() => setMobileResourcesOpen(!mobileResourcesOpen)}
                className="flex w-full items-center justify-between px-3 py-2 text-xs font-bold tracking-wider text-slate-500 uppercase dark:text-[#99753a]"
              >
                <span>Resources</span>
                <ChevronDown
                  size={14}
                  className={cn(
                    "transition-transform",
                    mobileResourcesOpen ? "rotate-180" : "",
                  )}
                />
              </button>
              {mobileResourcesOpen && (
                <div className="space-y-1 pt-1">
                  {RESOURCE_ITEMS.map((item) => (
                    <a
                      key={item.href}
                      href={item.href}
                      onClick={() => setOpen(false)}
                      className="flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium text-slate-800 hover:bg-white dark:text-slate-200 dark:hover:bg-[#1C294A]"
                    >
                      <span>{item.label}</span>
                      <ArrowRight
                        size={14}
                        className="text-slate-400 dark:text-slate-500"
                      />
                    </a>
                  ))}
                </div>
              )}
            </div>

            {/* Standalone Pricing in Mobile */}
            <a
              href="#pricing"
              onClick={() => setOpen(false)}
              className="flex items-center justify-between rounded-xl border border-slate-200/70 px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-100 dark:border-white/5 dark:text-slate-100 dark:hover:bg-[#1C294A]"
            >
              <span>Pricing</span>
              <ArrowRight
                size={15}
                className="text-slate-400 dark:text-slate-500"
              />
            </a>

            <div className="mt-2 flex flex-col gap-2.5 border-t border-slate-200/80 pt-3 dark:border-white/10">
              <a
                href={APP_AUTH_URL}
                onClick={() => setOpen(false)}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white/80 px-4 py-2.5 text-sm font-semibold text-slate-800 transition-all dark:border-white/10 dark:bg-[#1C294A] dark:text-white"
              >
                Log in
              </a>
              <a
                href={APP_AUTH_URL}
                onClick={() => setOpen(false)}
                className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#99753a] px-4 py-3 text-sm font-bold text-white shadow-md shadow-[#99753a]/20 transition-all hover:bg-[#85632f] dark:shadow-black/40"
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
