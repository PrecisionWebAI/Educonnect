"use client";

import { useEffect, useRef } from "react";

interface Star {
    orbitR: number;
    angle: number;
    speed: number;
    wobble: number;
    wobbleSpeed: number;
    r: number;
    tw: number;
    /** index into the active theme palette (resolved per frame) */
    ci: number;
    squash: number;
}

/**
 * Galaxy particle field — stars orbiting a centre in slow spiral arms,
 * with twinkling dust. Fixed to the full viewport, behind all content.
 * Pure canvas, zero dependencies, reduced-motion aware.
 */
export default function ParticleField() {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Dark keeps the original galaxy palette; light uses brand pastels
        // deepened to stay visible on white (primary / accent / accent-2 light).
        const DARK_PALETTE = [
            "rgba(214,220,255,", // soft star white-blue (majority)
            "rgba(214,220,255,",
            "rgba(45,212,191,", // teal
            "rgba(167,139,250,", // violet
            "rgba(100,108,255,", // indigo
        ];
        const LIGHT_PALETTE = [
            "rgba(179,156,208,", // brand violet (majority star)
            "rgba(179,156,208,",
            "rgba(95,168,170,", // cyan (chart-1 light)
            "rgba(201,127,146,", // pink (accent-2 light)
            "rgba(122,102,160,", // deep violet
        ];

        let w = 0;
        let h = 0;
        let raf = 0;
        let stars: Star[] = [];
        let cx = 0;
        let cy = 0;

        function build() {
            // +20% dot count vs previous setting
            const count = Math.min(672, Math.max(288, Math.floor(((w * h) / 3800) * 1.2)));
            stars = Array.from({ length: count }, (_, i) => {
                // spiral arms: bias starting angle along 2 arms + spread
                const arm = i % 2;
                // each star's orbit-top is uniformly spread over the visible band
                // (badge line -> CTA line), so density is even top-to-bottom
                const yTop = h * (0.2 + Math.random() * 0.66);
                const orbitR = cy - yTop;
                const armBias = arm * Math.PI + orbitR * 0.0035 + (Math.random() - 0.5) * 0.9;
                return {
                    orbitR,
                    angle: armBias + Math.random() * 0.4,
                    // inner stars orbit faster — classic galaxy differential rotation
                    // 0.26 → 0.18: total ~30% slower than previous 75% setting
                    speed: (0.05 + 26 / (orbitR + 120)) * 0.18,
                    wobble: Math.random() * Math.PI * 2,
                    wobbleSpeed: 0.15 + Math.random() * 0.3,
                    r: 0.5 + Math.pow(Math.random(), 2.2) * 2.4,
                    tw: Math.random() * Math.PI * 2,
                    ci: Math.random() < 0.62 ? 0 : 2 + Math.floor(Math.random() * 3),
                    squash: 1, // circular orbit — even coverage across the band
                };
            });
        }

        function resize() {
            if (!canvas) return;
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            w = canvas.offsetWidth;
            h = canvas.offsetHeight;
            canvas.width = w * dpr;
            canvas.height = h * dpr;
            ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
            cx = w / 2;
            cy = h * 1.5;
            build();
        }

        function frame() {
            // self-healing: if the canvas got its real layout size after this
            // effect started (e.g. CSS painted late on first open), rebuild
            const pw = canvas!.offsetWidth;
            const ph = canvas!.offsetHeight;
            if (pw !== w || ph !== h) {
                resize();
                return (raf = requestAnimationFrame(frame));
            }
            ctx!.clearRect(0, 0, w, h);

            // theme is re-resolved every frame so the toggle applies instantly
            const dark = document.documentElement.classList.contains("dark");
            const palette = dark ? DARK_PALETTE : LIGHT_PALETTE;

            // faint galactic core glow (indigo in dark, brand violet in light)
            const core = ctx!.createRadialGradient(cx, cy, 0, cx, cy, 240);
            core.addColorStop(0, dark ? "rgba(100,108,255,0.10)" : "rgba(179,156,208,0.12)");
            core.addColorStop(1, dark ? "rgba(100,108,255,0)" : "rgba(179,156,208,0)");
            ctx!.fillStyle = core;
            ctx!.fillRect(0, 0, w, h);

            // dark: additive blending — overlaps brighten (glow), never go dark.
            // light: normal compositing (additive washes out on white).
            ctx!.globalCompositeOperation = dark ? "lighter" : "source-over";
            for (const s of stars) {
                s.angle += s.speed;
                s.wobble += s.wobbleSpeed;
                s.tw += 0.02;

                const rr = s.orbitR + Math.sin(s.wobble) * 14; // radial breathing
                const x = cx + Math.cos(s.angle) * rr;
                const y = cy + Math.sin(s.angle) * rr * s.squash;

                const alpha = 0.2 + 0.6 * (0.5 + 0.5 * Math.sin(s.tw));
                ctx!.beginPath();
                ctx!.arc(x, y, s.r, 0, Math.PI * 2);
                ctx!.fillStyle = `${palette[s.ci]}${alpha.toFixed(3)})`;
                ctx!.fill();
            }
            ctx!.globalCompositeOperation = "source-over";
            raf = requestAnimationFrame(frame);
        }

        function onVis() {
            if (document.hidden) cancelAnimationFrame(raf);
            else raf = requestAnimationFrame(frame);
        }

        resize();
        raf = requestAnimationFrame(frame);
        window.addEventListener("resize", resize);
        document.addEventListener("visibilitychange", onVis);
        // first-open fix: on initial load CSS may not be painted yet, so
        // offsetWidth is 0 and the canvas measures empty. ResizeObserver
        // re-measures as soon as the canvas gets its real layout size.
        const ro = new ResizeObserver(() => {
            const pw = canvas.offsetWidth;
            const ph = canvas.offsetHeight;
            if (pw > 0 && ph > 0 && (pw !== w || ph !== h)) resize();
        });
        ro.observe(canvas);
        return () => {
            cancelAnimationFrame(raf);
            ro.disconnect();
            window.removeEventListener("resize", resize);
            document.removeEventListener("visibilitychange", onVis);
        };
    }, []);

    return <canvas ref={canvasRef} className="particle-canvas" aria-hidden="true" />;
}
