"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-context";
import { Button } from "@/components/ui";
import DemoRoleChips from "./DemoRoleChips";

// ============================================================
// PAGE 03 — Login (stitch: login_screen_dark_mode).
// Centered card: logo circle, credential fields, show/hide
// password, forgot link, quick demo role access.
// ============================================================

export default function AuthPage() {
    const { isAuthed, login } = useAuth();
    const router = useRouter();
    const [mode, setMode] = useState<"login" | "register">("login");
    const [identifier, setIdentifier] = useState("");
    const [password, setPassword] = useState("");
    const [showPwd, setShowPwd] = useState(false);
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    async function submit(id: string, pwd: string) {
        setError("");
        setIsSubmitting(true);
        try {
            await login(id, pwd);
            router.replace("/dashboard");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Login failed. Please try again.");
        } finally {
            setIsSubmitting(false);
        }
    }

    function handleSubmit(e: FormEvent<HTMLFormElement>) {
        e.preventDefault();
        void submit(identifier.trim(), password);
    }

    useEffect(() => {
        if (isAuthed) router.replace("/dashboard");
    }, [isAuthed, router]);

    return (
        <div className="auth-page">
            <div className="hero-bg" aria-hidden="true">
                <span className="blob blob-1" />
                <span className="blob blob-2" />
            </div>

            <Link href="/" className="auth-back">
                ← Back to home
            </Link>

            <main className="auth-card">
                {/* Brand header */}
                <div className="auth-brand">
                    <div className="auth-logo-circle">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img src="/logo.png" alt="EduConnect" />
                    </div>
                    <h1>EduConnect</h1>
                    <p>Sign in to your educational portal</p>
                </div>

                {mode === "register" ? (
                    <>
                        <p className="auth-note" style={{ marginBottom: "1rem" }}>
                            🚧 Registration is coming soon — accounts are created by the school
                            admin. Ask your administrator for an invite code.
                        </p>
                        <button
                            type="button"
                            className="btn btn-outline"
                            style={{ width: "100%" }}
                            onClick={() => setMode("login")}
                        >
                            ← Back to sign in
                        </button>
                    </>
                ) : (
                    <>
                        {error !== "" && <p className="auth-error">{error}</p>}

                        <form onSubmit={handleSubmit}>
                            {/* Identifier */}
                            <div className="field">
                                <label htmlFor="identifier">Email or Student ID</label>
                                <input
                                    id="identifier"
                                    type="text"
                                    className="input"
                                    placeholder="Enter your credentials"
                                    value={identifier}
                                    onChange={(e) => setIdentifier(e.target.value)}
                                    required
                                    disabled={isSubmitting}
                                    autoComplete="username"
                                />
                            </div>

                            {/* Password */}
                            <div className="field">
                                <label htmlFor="password">Password</label>
                                <div className="pwd-wrap">
                                    <input
                                        id="password"
                                        type={showPwd ? "text" : "password"}
                                        className="input"
                                        placeholder="Enter your password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                        disabled={isSubmitting}
                                        autoComplete="current-password"
                                    />
                                    <button
                                        type="button"
                                        className="pwd-toggle"
                                        onClick={() => setShowPwd((v) => !v)}
                                        aria-label={showPwd ? "Hide password" : "Show password"}
                                    >
                                        {showPwd ? "🙈" : "👁️"}
                                    </button>
                                </div>
                            </div>

                            <div className="auth-forgot">
                                <a href="#" onClick={(e) => e.preventDefault()}>
                                    Forgot password?
                                </a>
                            </div>

                            <Button type="submit" loading={isSubmitting} style={{ width: "100%" }}>
                                Sign In →
                            </Button>
                        </form>

                        <div className="divider">or continue with</div>

                        {/* Quick demo role access (replaces biometrics for now) */}
                        <div className="demo-block">
                            <DemoRoleChips
                                disabled={isSubmitting}
                                onPick={(id, pwd) => void submit(id, pwd)}
                            />
                        </div>

                        <p className="auth-switch">
                            Don&apos;t have an account?{" "}
                            <button type="button" onClick={() => setMode("register")}>
                                Register here
                            </button>
                        </p>
                    </>
                )}
            </main>
        </div>
    );
}
