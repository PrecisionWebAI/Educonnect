"use client";

import { useEffect, useState, type FormEvent } from "react";
import Image from "next/image";
import {
    ArrowLeft,
    ArrowRight,
    BookOpen,
    Eye,
    EyeOff,
    LockKeyhole,
    Mail,
    ShieldCheck,
    Sparkles,
    UsersRound,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/providers/auth-context";
import { Button } from "@/components/ui";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ThemeToggle } from "@/components/layout/ThemeToggle";

export default function AuthPage() {
    const { isAuthed, login } = useAuth();
    const router = useRouter();
    const [mode, setMode] = useState<"login" | "register">("login");
    const [identifier, setIdentifier] = useState("");
    const [password, setPassword] = useState("");
    const [showPwd, setShowPwd] = useState(false);
    const [error, setError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const sessionExpired = useSearchParams().get("expired") === "1";
    const notice =
        error || (sessionExpired ? "Your session has expired. Please sign in again." : "");

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

    function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        void submit(identifier.trim(), password);
    }

    useEffect(() => {
        if (isAuthed) router.replace("/dashboard");
    }, [isAuthed, router]);

    return (
        <div className="auth-page">
            <header className="auth-topbar">
                <div className="auth-brand-lockup">
                    <Image
                        src="/logo.png"
                        alt=""
                        width={32}
                        height={32}
                        className="auth-brand-mark"
                    />
                    <span className="auth-brand-name">
                        EduConnect
                        <span>School OS</span>
                    </span>
                </div>

                <div className="auth-topbar-actions">
                    <span className="auth-secure-label">
                        <ShieldCheck aria-hidden="true" size={16} />
                        Secure sign in
                    </span>
                    <ThemeToggle className="auth-theme-toggle" />
                </div>
            </header>

            <main className="auth-layout">
                <section className="auth-story-panel" aria-label="EduConnect for schools">
                    <div className="auth-story-orbit" aria-hidden="true">
                        <span>
                            <BookOpen size={34} strokeWidth={1.35} />
                        </span>
                    </div>

                    <div className="auth-story-content">
                        <p className="auth-story-kicker">
                            <span aria-hidden="true" />
                            BUILT FOR EVERY SCHOOL
                        </p>
                        <h1>
                            Better school days,
                            <br />
                            <span>all connected.</span>
                        </h1>
                        <p className="auth-story-description">
                            The people, learning, and everyday work of your school — in one
                            thoughtful place.
                        </p>

                        <div className="auth-feature-list" aria-label="Platform features">
                            <div className="auth-feature">
                                <span className="auth-feature-icon">
                                    <BookOpen aria-hidden="true" size={17} />
                                </span>
                                <span>Learning</span>
                            </div>
                            <div className="auth-feature">
                                <span className="auth-feature-icon">
                                    <UsersRound aria-hidden="true" size={17} />
                                </span>
                                <span>Community</span>
                            </div>
                            <div className="auth-feature">
                                <span className="auth-feature-icon">
                                    <ShieldCheck aria-hidden="true" size={17} />
                                </span>
                                <span>Operations</span>
                            </div>
                        </div>
                    </div>

                    <div className="auth-story-footer">
                        <span className="auth-story-footer-mark" aria-hidden="true">
                            <Sparkles size={15} />
                        </span>
                        <span>Made for the people who make school matter.</span>
                    </div>
                </section>

                <section className="auth-form-panel" aria-labelledby="auth-heading">
                    <div className="auth-form-content">
                        <div className="auth-form-heading">
                            <span className="auth-form-icon" aria-hidden="true">
                                {mode === "login" ? (
                                    <Sparkles size={19} />
                                ) : (
                                    <ShieldCheck size={19} />
                                )}
                            </span>
                            <p className="auth-form-eyebrow">
                                {mode === "login" ? "WELCOME BACK" : "ACCOUNT ACCESS"}
                            </p>
                            <h2 id="auth-heading">
                                {mode === "login" ? "Sign in to continue" : "Join your school"}
                            </h2>
                            <p className="auth-form-description">
                                {mode === "login"
                                    ? "Pick up where your school community left off."
                                    : "Your school administrator can help you get started."}
                            </p>
                        </div>

                        {mode === "register" ? (
                            <div className="auth-register-panel">
                                <span className="auth-register-icon" aria-hidden="true">
                                    <LockKeyhole size={20} />
                                </span>
                                <div>
                                    <h3>Access is managed by your school</h3>
                                    <p>
                                        Accounts are created by the school administrator. Ask them
                                        for an invitation to join your EduConnect community.
                                    </p>
                                </div>
                                <Button
                                    variant="outline"
                                    type="button"
                                    className="auth-back-button w-full"
                                    onClick={() => setMode("login")}
                                >
                                    <ArrowLeft aria-hidden="true" />
                                    Back to sign in
                                </Button>
                            </div>
                        ) : (
                            <>
                                {notice !== "" && (
                                    <div className="auth-alert" role="alert">
                                        <ShieldCheck aria-hidden="true" size={18} />
                                        <p>{notice}</p>
                                    </div>
                                )}

                                <form onSubmit={handleSubmit} className="auth-form">
                                    <div className="auth-field">
                                        <Label htmlFor="identifier" className="auth-label">
                                            Email or username
                                        </Label>
                                        <div className="auth-input-wrap">
                                            <Mail
                                                className="auth-input-icon"
                                                aria-hidden="true"
                                                size={18}
                                            />
                                            <Input
                                                id="identifier"
                                                type="text"
                                                className="auth-input"
                                                placeholder="you@school.edu"
                                                value={identifier}
                                                onChange={(event) =>
                                                    setIdentifier(event.target.value)
                                                }
                                                required
                                                disabled={isSubmitting}
                                                autoComplete="username"
                                            />
                                        </div>
                                    </div>

                                    <div className="auth-field">
                                        <Label htmlFor="password" className="auth-label">
                                            Password
                                        </Label>
                                        <div className="auth-input-wrap">
                                            <LockKeyhole
                                                className="auth-input-icon"
                                                aria-hidden="true"
                                                size={18}
                                            />
                                            <Input
                                                id="password"
                                                type={showPwd ? "text" : "password"}
                                                className="auth-input auth-password-input"
                                                placeholder="Enter your password"
                                                value={password}
                                                onChange={(event) =>
                                                    setPassword(event.target.value)
                                                }
                                                required
                                                disabled={isSubmitting}
                                                autoComplete="current-password"
                                            />
                                            <button
                                                type="button"
                                                className="auth-password-toggle"
                                                onClick={() => setShowPwd((visible) => !visible)}
                                                aria-label={
                                                    showPwd ? "Hide password" : "Show password"
                                                }
                                                aria-pressed={showPwd}
                                            >
                                                {showPwd ? (
                                                    <EyeOff aria-hidden="true" size={18} />
                                                ) : (
                                                    <Eye aria-hidden="true" size={18} />
                                                )}
                                            </button>
                                        </div>
                                    </div>

                                    <div className="auth-forgot">
                                        <a href="#" onClick={(event) => event.preventDefault()}>
                                            Forgot password?
                                        </a>
                                    </div>

                                    <Button
                                        type="submit"
                                        loading={isSubmitting}
                                        className="auth-submit w-full"
                                    >
                                        Sign in
                                        <ArrowRight aria-hidden="true" size={17} />
                                    </Button>
                                </form>

                                <div className="auth-form-divider">
                                    <span />
                                    <span>YOUR SCHOOL, IN SYNC</span>
                                    <span />
                                </div>

                                <p className="auth-switch">
                                    New to EduConnect?{" "}
                                    <button type="button" onClick={() => setMode("register")}>
                                        Request access
                                        <ArrowRight aria-hidden="true" size={14} />
                                    </button>
                                </p>
                            </>
                        )}

                        <p className="auth-privacy-note">
                            <LockKeyhole aria-hidden="true" size={14} />
                            Your school account keeps your community secure.
                        </p>
                    </div>
                </section>
            </main>

            <footer className="auth-footer">
                <span>EduConnect</span>
                <span>Helping school communities thrive</span>
            </footer>
        </div>
    );
}
