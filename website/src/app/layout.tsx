import type { Metadata } from "next";
import "./globals.css";
import "@/styles/tokens.css";
import "@/styles/public.css";
import "@/styles/ui.css";
import "@/styles/landing.css";
import { ThemeProvider } from "@/providers/ThemeProvider";
import { ThemeScript } from "@/components/layout/ThemeScript";
import { Inter, Plus_Jakarta_Sans, JetBrains_Mono } from "next/font/google";
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

const mono = JetBrains_Mono({
    subsets: ["latin"],
    variable: "--font-mono",
    weight: ["400", "500", "600", "700"],
    display: "swap",
});

export const metadata: Metadata = {
    title: "EduConnect OS — The AI-Powered Operating System for Physical Schools",
    description:
        "Seamlessly connect Principals, Teachers, Students, and Parents through a synchronized, ultra-responsive crystal glass workspace.",
    icons: {
        icon: "/favicon.svg",
    },
};

/**
 * Root layout.
 *
 * Two dark-mode notes:
 *  • Do NOT hardcode `dark` on <html>. A static class would defeat ThemeScript
 *    and pin the site to dark mode, and it would also paint the server-rendered
 *    HTML dark before the script could run — the exact FOUC ThemeScript exists
 *    to prevent. ThemeScript sets `.dark` / `.light` before first paint, so the
 *    className here must stay theme-neutral.
 *  • `defaultTheme` is `system` to agree with ThemeScript, which already falls
 *    back to the OS preference. Passing "dark" made the two disagree, flipping
 *    the theme immediately after mount.
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html
            lang="en"
            className={cn("h-full antialiased scroll-smooth", inter.variable, display.variable, mono.variable)}
            suppressHydrationWarning
        >
            <body className="flex min-h-full flex-col font-sans transition-colors duration-300">
                <ThemeScript />
                <ThemeProvider defaultTheme="system">
                    {children}
                </ThemeProvider>
            </body>
        </html>
    );
}
