"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-context";
import { Button } from "@/components/ui";
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// ============================================================
// PAGE 03 — Login (stitch: login_screen_dark_mode).
// Shadcn Card shell + shadcn inputs/buttons. Centered card:
// logo circle, credential fields, show/hide password, forgot
// link.
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
                {mode === "register" ? (
                    <Card className="shadow-lg">
                        <CardHeader className="flex flex-col items-center gap-3 pb-6 text-center">
                            <div className="auth-logo-circle">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img src="/logo.png" alt="EduConnect" />
                            </div>
                            <div className="space-y-1">
                                <CardTitle className="text-2xl font-bold tracking-tight">
                                    EduConnect
                                </CardTitle>
                                <CardDescription>Create your account</CardDescription>
                            </div>
                        </CardHeader>
                        <CardContent>
                            <p className="auth-note" style={{ marginBottom: 0 }}>
                                🚧 Registration is coming soon — accounts are created by the
                                school admin. Ask your administrator for an invite code.
                            </p>
                        </CardContent>
                        <CardFooter className="flex justify-center">
                            <Button
                                variant="outline"
                                type="button"
                                className="w-full"
                                onClick={() => setMode("login")}
                            >
                                ← Back to sign in
                            </Button>
                        </CardFooter>
                    </Card>
                ) : (
                    <Card className="shadow-lg">
                        <CardHeader className="flex flex-col items-center gap-3 pb-6 text-center">
                            <div className="auth-logo-circle">
                                {/* eslint-disable-next-line @next/next/no-img-element */}
                                <img src="/logo.png" alt="EduConnect" />
                            </div>
                            <div className="space-y-1">
                                <CardTitle className="text-2xl font-bold tracking-tight">
                                    EduConnect
                                </CardTitle>
                                <CardDescription>Sign in to your educational portal</CardDescription>
                            </div>
                        </CardHeader>

                        <CardContent className="space-y-4">
                            {error !== "" && <p className="auth-error">{error}</p>}

                            <form onSubmit={handleSubmit} className="space-y-4">
                                {/* Identifier */}
                                <div className="space-y-2">
                                    <Label htmlFor="identifier">Email or Student ID</Label>
                                    <Input
                                        id="identifier"
                                        type="text"
                                        className="h-9"
                                        placeholder="Enter your credentials"
                                        value={identifier}
                                        onChange={(e) => setIdentifier(e.target.value)}
                                        required
                                        disabled={isSubmitting}
                                        autoComplete="username"
                                    />
                                </div>

                                {/* Password */}
                                <div className="space-y-2">
                                    <Label htmlFor="password">Password</Label>
                                    <div className="pwd-wrap">
                                        <Input
                                            id="password"
                                            type={showPwd ? "text" : "password"}
                                            className="h-9 pr-10"
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

                                <Button
                                    type="submit"
                                    loading={isSubmitting}
                                    className="w-full"
                                    style={{ height: "2.35rem" }}
                                >
                                    Sign In →
                                </Button>
                            </form>
                        </CardContent>

                        <CardFooter className="flex flex-col gap-4 pt-5">
                            <p className="auth-switch">
                                Don&apos;t have an account?{" "}
                                <button type="button" onClick={() => setMode("register")}>
                                    Register here
                                </button>
                            </p>
                        </CardFooter>
                    </Card>
                )}
            </main>
        </div>
    );
}
