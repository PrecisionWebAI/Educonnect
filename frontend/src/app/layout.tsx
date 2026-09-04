import type { Metadata } from "next";
import "./globals.css";
import "@/styles/tokens.css";
import "@/styles/public.css";
import "@/styles/ui.css";
import "@/styles/shell.css";
import "@/styles/splash.css";
import "@/styles/landing.css";
import "@/styles/auth.css";
import "@/styles/modules.css";
import { AuthProvider } from "@/providers/AuthProvider";
import { ThemeProvider } from "@/providers/ThemeProvider";
import { ThemeScript } from "@/components/layout/ThemeScript";
import { ToastProvider } from "@/components/ui/toast";
import SplashOverlay from "@/components/layout/SplashOverlay";

export const metadata: Metadata = {
    title: "EduConnect — AI-Powered School OS",
    description:
        "One platform connecting Directors, Principals, Teachers, Students and Parents — from attendance to analytics.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en" className="h-full antialiased" suppressHydrationWarning>
            <head>
                <ThemeScript />
            </head>
            <body className="flex min-h-full flex-col">
                <ThemeProvider defaultTheme="system">
                    <AuthProvider>
                        <ToastProvider>
                            <SplashOverlay />
                            {children}
                        </ToastProvider>
                    </AuthProvider>
                </ThemeProvider>
            </body>
        </html>
    );
}
