"use client";

import React, { useState } from "react";
import Image from "next/image";
import { CheckCircle, Mail, Phone, Send, ShieldCheck } from "lucide-react";

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
  "text-slate-600 dark:text-slate-400 hover:text-[#99753a] dark:hover:text-[#99753a] transition-colors duration-150 inline-block text-xs font-normal";

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
    <footer className="w-full border-t border-slate-200/80 bg-slate-100/90 transition-colors duration-300 dark:border-white/5 dark:bg-[#0B1221]">
      <div className="mx-auto w-full max-w-7xl px-6 py-16 sm:py-20">
        <div className="mb-14 grid grid-cols-1 gap-10 sm:gap-12 md:grid-cols-12">
          {/* Brand Info */}
          <div className="space-y-3 md:col-span-4">
            <div className="flex items-center gap-2.5">
              <Image
                src="/logo.png?v=2"
                alt="EduConnect"
                width={36}
                height={36}
                unoptimized
                className="h-9 w-9 object-contain"
              />
              <span className="font-heading text-lg font-extrabold tracking-tight text-slate-900 dark:text-slate-50">
                EduConnect
              </span>
            </div>
            <p className="max-w-sm text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              The intelligent school operating system for physical campuses —
              from daily attendance and fee collections to institutional
              analytics.
            </p>
            <p className="text-xs font-medium text-slate-500 dark:text-slate-400">
              Bengaluru, India
            </p>
          </div>

          {/* Product Directory Links */}
          <div className="md:col-span-2">
            <h4 className="mb-4 text-xs font-bold tracking-wider text-slate-900 uppercase dark:text-slate-50">
              Platform
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
            <h4 className="mb-4 text-xs font-bold tracking-wider text-slate-900 uppercase dark:text-slate-50">
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
            <h4 className="mb-4 text-xs font-bold tracking-wider text-slate-900 uppercase dark:text-slate-50">
              Campus Dispatch
            </h4>
            <p className="mb-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              Monthly insights on physical school management, regulatory
              compliance, and digital rollouts.
            </p>

            {subscribed ? (
              <div className="flex items-center gap-2 rounded-lg border border-emerald-500/40 bg-emerald-50 px-3 py-3 text-xs font-semibold text-emerald-700/80 dark:border-emerald-500/20 dark:bg-emerald-950/30 dark:text-emerald-300/80">
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
                  placeholder="principal@school.edu"
                  className="min-w-0 flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-xs text-slate-900 transition-all outline-none placeholder:text-slate-400 focus:border-[#99753a] dark:border-white/10 dark:bg-[#131E3A] dark:text-slate-100"
                />
                <button
                  type="submit"
                  aria-label="Subscribe to the campus dispatch"
                  className="inline-flex items-center justify-center rounded-lg bg-[#99753a] px-3.5 py-2.5 text-white shadow-sm shadow-[#99753a]/20 transition-all hover:-translate-y-0.5 hover:bg-[#85632f] active:scale-95 dark:shadow-md dark:shadow-black/40"
                >
                  <Send size={15} />
                </button>
              </form>
            )}

            <div className="mt-5 space-y-2 text-xs text-slate-600 dark:text-slate-400">
              <p className="flex items-center gap-2">
                <Mail size={14} className="text-slate-500" />
                <a
                  className="transition-colors hover:text-[#99753a] dark:hover:text-[#99753a]"
                  href="mailto:hello@educonnect.school"
                >
                  hello@educonnect.school
                </a>
              </p>
              <p className="flex items-center gap-2">
                <Phone size={14} className="text-slate-500" />
                <a
                  className="transition-colors hover:text-[#99753a] dark:hover:text-[#99753a]"
                  href="tel:+919876543210"
                >
                  +91 98765 43210
                </a>
              </p>
            </div>
          </div>
        </div>

        {/* Legal & Copyright Bar */}
        <div className="flex flex-col items-center justify-between gap-4 border-t border-slate-200/80 pt-8 text-xs text-slate-600 md:flex-row dark:border-white/5 dark:text-slate-400">
          <p className="text-center leading-relaxed md:text-left">
            © {new Date().getFullYear()} EduConnect Operating System Inc.
            Architecting intelligent campus infrastructure. All rights reserved.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-4">
            <span className="inline-flex items-center gap-1.5 font-medium">
              <ShieldCheck size={14} className="text-[#99753a]" />
              ISO 27001 · FERPA · GDPR aligned
            </span>
            <span className="hidden font-medium sm:inline">
              Zero-paperwork operations for physical schools
            </span>
          </div>
        </div>
      </div>
    </footer>
  );
}
