"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/providers/auth-context";

// ============================================================
// PAGE 01 — Startup / Splash screen (Next.js port).
// Shows once on app start, then fades out and reveals the app.
// ============================================================

const AUTO_DISMISS_MS = 1600;
const FADE_MS = 500;

export default function Splash({ onDone }: { onDone: () => void }) {
    const [leaving, setLeaving] = useState(false);
    const { isAuthed } = useAuth();

    useEffect(() => {
        const fadeAt = window.setTimeout(() => setLeaving(true), AUTO_DISMISS_MS - FADE_MS);
        const doneAt = window.setTimeout(onDone, AUTO_DISMISS_MS);
        return () => {
            window.clearTimeout(fadeAt);
            window.clearTimeout(doneAt);
        };
    }, [onDone]);

    function finish() {
        if (leaving) return;
        setLeaving(true);
        window.setTimeout(onDone, 350);
    }

    return (
        <div
            className={`splash ${leaving ? "splash-leaving" : ""}`}
            role="status"
            aria-label="Loading EduConnect"
        >
            <div className="splash-bg" aria-hidden="true">
                <span className="splash-blob splash-blob-1" />
                <span className="splash-blob splash-blob-2" />
                <span className="splash-particle splash-particle-1" />
                <span className="splash-particle splash-particle-2" />
                <span className="splash-particle splash-particle-3" />
            </div>

            <div className="splash-content">
                <div className="splash-logo-wrap">
                    <span className="splash-glow" aria-hidden="true" />
                    <span className="splash-ring" aria-hidden="true" />
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src="/logo.png" className="splash-logo" alt="EduConnect logo" />
                </div>

                <h1 className="splash-title">EduConnect</h1>
                <p className="splash-tagline">Connecting Schools, Empowering Students</p>

                <div className="splash-bar">
                    <span className="splash-bar-fill" />
                </div>
                <span className="splash-hint">AI-Powered School OS</span>
            </div>

            <div className="splash-actions">
                <Link
                    href={isAuthed ? "/dashboard" : "/auth"}
                    className="btn btn-primary splash-cta"
                    onClick={finish}
                >
                    Get Started <span className="splash-arrow">→</span>
                </Link>
                <p className="splash-login">
                    Already have an account?{" "}
                    <Link href="/auth" onClick={finish}>
                        Log in
                    </Link>
                </p>
            </div>

            <div className="splash-footer" aria-hidden="true">
                <span className="splash-pill" />
            </div>
        </div>
    );
}
