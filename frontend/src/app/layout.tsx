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
import { TooltipProvider } from "@/components/ui/tooltip";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import { cn } from "@/lib/utils";

const inter = Inter({
    subsets: ["latin"],
    variable: "--font-sans",
    display: "swap",
});

const display = Plus_Jakarta_Sans({
    subsets: ["latin"],
    variable: "--font-display",
    weight: ["400", "500", "600", "700", "800"],
    display: "swap",
});

export const metadata: Metadata = {
    title: "EduConnect — AI-Powered School OS",
    description:
        "One platform connecting Directors, Principals, Teachers, Students and Parents — from attendance to analytics.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html
            lang="en"
            className={cn("h-full antialiased", "font-sans", inter.variable, display.variable)}
            suppressHydrationWarning
        >
            <head>
                <ThemeScript />
            </head>
            <body className="flex min-h-full flex-col">
                <ThemeProvider defaultTheme="system">
                    <AuthProvider>
                        <ToastProvider>
                            <TooltipProvider>
                                {children}
                            </TooltipProvider>
                        </ToastProvider>
                    </AuthProvider>
                </ThemeProvider>
            </body>
        </html>
    );
}
