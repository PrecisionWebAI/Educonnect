"use client";

import React, { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface RevealProps {
    children: React.ReactNode;
    /** Stagger delay in milliseconds. */
    delay?: number;
    className?: string;
    /** Direction the content travels from while fading in. */
    from?: "bottom" | "left" | "right" | "scale";
}

const HIDDEN: Record<NonNullable<RevealProps["from"]>, string> = {
    bottom: "translate-y-8 opacity-0",
    left: "-translate-x-8 opacity-0",
    right: "translate-x-8 opacity-0",
    scale: "scale-[0.96] opacity-0",
};

/**
 * Lightweight scroll reveal — fades/slides content in the first time it enters
 * the viewport. Respects `prefers-reduced-motion` and degrades gracefully when
 * IntersectionObserver is unavailable.
 */
export default function Reveal({ children, delay = 0, className, from = "bottom" }: RevealProps) {
    const ref = useRef<HTMLDivElement>(null);
    const [shown, setShown] = useState(false);

    useEffect(() => {
        const el = ref.current;
        if (!el) return;
        if (!("IntersectionObserver" in window) || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            setShown(true);
            return;
        }
        const io = new IntersectionObserver(
            ([entry]) => {
                if (!entry?.isIntersecting) return;
                setShown(true);
                io.disconnect();
            },
            { threshold: 0.12, rootMargin: "0px 0px -60px 0px" },
        );
        io.observe(el);
        return () => io.disconnect();
    }, []);

    return (
        <div
            ref={ref}
            style={{ transitionDelay: shown ? `${delay}ms` : "0ms" }}
            className={cn(
                "transition-all duration-700 ease-out will-change-transform",
                shown ? "translate-x-0 translate-y-0 scale-100 opacity-100" : HIDDEN[from],
                className,
            )}
        >
            {children}
        </div>
    );
}
