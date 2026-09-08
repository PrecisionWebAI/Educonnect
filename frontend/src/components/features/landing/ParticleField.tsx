"use client";

import { useEffect, useRef } from "react";

// ──────────────────────────────────────────────────────────────────────────
// Galaxy particle field — stars orbiting a centre in slow spiral arms, with
// twinkling dust, faint nebula clouds and a subtle cursor interaction.
//
// Improvements over the original implementation:
//  • batched canvas draws (stars grouped by palette + alpha step) — far fewer
//    draw operations per frame for an identical look
//  • core glow + nebula clouds pre-rendered to offscreen canvases (no per-frame
//    gradient work; both themes are cached so toggling is instant)
//  • soft halos behind the brightest stars
//  • pointer repulsion — stars near the cursor are gently pushed away
//  • prefers-reduced-motion now paints a single static frame instead of nothing
//  • props API (density / speed / interactive / toggles) with sane defaults;
//    star simulation extracted into a pure function
//
// Pure canvas, zero dependencies, DPR-aware, reduced-motion aware.
// ──────────────────────────────────────────────────────────────────────────

const DENSITY_BASE = 1;
const SPEED_BASE = 1;
/** Pointer influence radius (CSS px) — stars inside are pushed away. */
const REPULSE_RADIUS = 130;
/** Max repulsion offset (CSS px). */
const REPULSE_STRENGTH = 22;
/** How much larger a bright star's halo is than the star itself. */
const HALO_SCALE = 3;
/** Alpha quantization steps used for batched draws (0.1 steps). */
const ALPHA_LEVELS = 10;
/** Number of entries in each palette (must match DARK/LIGHT_PALETTE). */
const PALETTE_LEN = 5;

interface Star {
    orbitR: number;
    angle: number;
    speed: number;
    wobble: number;
    wobbleSpeed: number;
    r: number;
    tw: number;
    ci: number;
    squash: number;
    /** Bright enough to receive a soft halo. */
    halo: boolean;
}

export interface ParticleFieldProps {
    /** Star density multiplier (1 = default auto density). */
    density?: number;
    /** Global orbit speed multiplier. */
    speed?: number;
    /** Enable pointer repulsion (ignored under reduced motion). */
    interactive?: boolean;
    /** Draw the faint galactic core glow. */
    showCoreGlow?: boolean;
    /** Draw slow-drifting nebula clouds. */
    showNebula?: boolean;
    /** Draw soft halos behind the brightest stars. */
    showHalos?: boolean;
}

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

// ── Pure simulation helpers ──────────────────────────────────────────────

function clamp(v: number, lo: number, hi: number) {
    return Math.min(hi, Math.max(lo, v));
}

/**
 * Generate a fresh galaxy. Pure — no canvas or DOM access, so it can be
 * unit-tested and is deterministic in shape (only Math.random() varies).
 */
function generateStars(
    w: number,
    h: number,
    cx: number,
    cy: number,
    density = DENSITY_BASE,
    speedMul = SPEED_BASE,
): Star[] {
    const base = Math.min(672, Math.max(288, Math.floor(((w * h) / 3800) * 1.2)));
    const count = Math.round(clamp(base * density, 40, 900));
    const stars: Star[] = [];
    for (let i = 0; i < count; i++) {
        // spiral arms: bias starting angle along 2 arms + spread
        const arm = i % 2;
        // each star's orbit-top is uniformly spread over the visible band
        // (badge line -> CTA line), so density is even top-to-bottom
        const yTop = h * (0.2 + Math.random() * 0.66);
        const orbitR = cy - yTop;
        const armBias = arm * Math.PI + orbitR * 0.0035 + (Math.random() - 0.5) * 0.9;
        const r = 0.5 + Math.pow(Math.random(), 2.2) * 2.4;
        stars.push({
            orbitR,
            angle: armBias + Math.random() * 0.4,
            // inner stars orbit faster — classic galaxy differential rotation
            speed: (0.05 + 26 / (orbitR + 120)) * 0.18 * speedMul,
            wobble: Math.random() * Math.PI * 2,
            wobbleSpeed: 0.15 + Math.random() * 0.3,
            r,
            tw: Math.random() * Math.PI * 2,
            ci: Math.random() < 0.62 ? 0 : 2 + Math.floor(Math.random() * 3),
            squash: 1, // circular orbit — even coverage across the band
            halo: r > 2.0, // brightest ~10–15% get a glow
        });
    }
    return stars;
}
// ── Offscreen layer factories (cached per theme, rebuilt on resize) ────────

/**
 * Faint galactic core glow, pre-rendered to an offscreen canvas so the frame
 * loop only ever does a cheap drawImage. One layer per theme is cached.
 */
function makeCoreLayer(w: number, h: number, dark: boolean): HTMLCanvasElement | null {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const cv = document.createElement("canvas");
    cv.width = Math.ceil(w * dpr);
    cv.height = Math.ceil(h * dpr);
    const c = cv.getContext("2d");
    if (!c) return null;
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    // indigo in dark, brand violet in light
    const cx = w / 2;
    const cy = h * 1.5;
    const g = c.createRadialGradient(cx, cy, 0, cx, cy, 240);
    g.addColorStop(0, dark ? "rgba(100,108,255,0.10)" : "rgba(179,156,208,0.12)");
    g.addColorStop(1, dark ? "rgba(100,108,255,0)" : "rgba(179,156,208,0)");
    c.fillStyle = g;
    c.fillRect(0, 0, w, h);
    return cv;
}

interface Nebula {
    canvas: HTMLCanvasElement;
    x: number;
    y: number;
    r: number;
    phx: number;
    phy: number;
    sx: number;
    sy: number;
}

/** One soft radial cloud, baked to a small offscreen canvas (alpha included). */
function makeNebula(r: number, color: string): HTMLCanvasElement | null {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const size = Math.ceil(r * 2 * dpr);
    const cv = document.createElement("canvas");
    cv.width = size;
    cv.height = size;
    const c = cv.getContext("2d");
    if (!c) return null;
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    const g = c.createRadialGradient(r, r, 0, r, r, r);
    g.addColorStop(0, `${color}0.07)`);
    g.addColorStop(0.55, `${color}0.04)`);
    g.addColorStop(1, `${color}0)`);
    c.fillStyle = g;
    c.fillRect(0, 0, r * 2, r * 2);
    return cv;
}

function buildNebulae(w: number, h: number, dark: boolean): Nebula[] {
    const colors = dark
        ? ["rgba(100,108,255,", "rgba(45,212,191,", "rgba(167,139,250,"]
        : ["rgba(179,156,208,", "rgba(95,168,170,", "rgba(201,127,146,"];
    const base = Math.max(w, h);
    const spots = [
        { x: w * 0.2, y: h * 0.4, r: base * 0.3 },
        { x: w * 0.84, y: h * 0.55, r: base * 0.26 },
        { x: w * 0.55, y: h * 0.08, r: base * 0.32 },
    ];
    return spots.map((s, i) => ({
        canvas: makeNebula(s.r, colors[i % colors.length]) ?? document.createElement("canvas"),
        x: s.x,
        y: s.y,
        r: s.r,
        phx: Math.random() * Math.PI * 2,
        phy: Math.random() * Math.PI * 2,
        sx: 9 + Math.random() * 11,
        sy: 6 + Math.random() * 8,
    }));
}
// ── Component ────────────────────────────────────────────────────────────

export default function ParticleField({
    density = DENSITY_BASE,
    speed = SPEED_BASE,
    interactive = true,
    showCoreGlow = true,
    showNebula = true,
    showHalos = true,
}: ParticleFieldProps = {}) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas!.getContext("2d");
        if (!ctx) return;

        const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

        let w = 0;
        let h = 0;
        let raf = 0;
        let stars: Star[] = [];
        let cx = 0;
        let cy = 0;
        let coreDark: HTMLCanvasElement | null = null;
        let coreLight: HTMLCanvasElement | null = null;
        let nebulaeDark: Nebula[] = [];
        let nebulaeLight: Nebula[] = [];
        const pointer = { x: -9999, y: -9999, active: false };
        // bucket[ci * ALPHA_LEVELS + alphaStep] holds [x, y, r, ...]; the final
        // bucket holds halo circles and is drawn first (behind the stars).
        const HALO_BUCKET = PALETTE_LEN * ALPHA_LEVELS;
        const buckets: number[][] = [];
        for (let i = 0; i <= HALO_BUCKET; i++) buckets.push([]);

        function resize() {
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            w = canvas!.offsetWidth;
            h = canvas!.offsetHeight;
            canvas!.width = w * dpr;
            canvas!.height = h * dpr;
            ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
            cx = w / 2;
            cy = h * 1.5;
            stars = generateStars(w, h, cx, cy, density, speed);
            coreDark = showCoreGlow ? makeCoreLayer(w, h, true) : null;
            coreLight = showCoreGlow ? makeCoreLayer(w, h, false) : null;
            nebulaeDark = showNebula ? buildNebulae(w, h, true) : [];
            nebulaeLight = showNebula ? buildNebulae(w, h, false) : [];
        }

        function render(dark: boolean, t: number) {
            ctx!.clearRect(0, 0, w, h);
            const palette = dark ? DARK_PALETTE : LIGHT_PALETTE;

            // nebula clouds — very low alpha, slow drift that never stops
            if (showNebula) {
                const nebulae = dark ? nebulaeDark : nebulaeLight;
                ctx!.globalCompositeOperation = dark ? "lighter" : "source-over";
                for (const n of nebulae) {
                    const dx = Math.sin(t * 0.00008 + n.phx) * n.r * 0.12;
                    const dy = Math.cos(t * 0.00006 + n.phy) * n.r * 0.1;
                    ctx!.drawImage(n.canvas, n.x - n.r + dx, n.y - n.r + dy, n.r * 2, n.r * 2);
                }
                ctx!.globalCompositeOperation = "source-over";
            }

            // cached galactic core glow (cheap drawImage)
            if (showCoreGlow) {
                const layer = dark ? coreDark : coreLight;
                if (layer) ctx!.drawImage(layer, 0, 0, w, h);
            }

            // reset buckets + step every star
            for (const b of buckets) b.length = 0;

            const rr2 = REPULSE_RADIUS * REPULSE_RADIUS;
            const usePointer = interactive && pointer.active && !reducedMotion;

            for (const s of stars) {
                s.angle += s.speed;
                s.wobble += s.wobbleSpeed;
                s.tw += 0.02;

                const rr = s.orbitR + Math.sin(s.wobble) * 14; // radial breathing
                let x = cx + Math.cos(s.angle) * rr;
                let y = cy + Math.sin(s.angle) * rr * s.squash;

                // pointer repulsion — push only the *drawn* position and leave
                // the orbit params untouched, so the field relaxes back naturally
                if (usePointer) {
                    const dx = x - pointer.x;
                    const dy = y - pointer.y;
                    const d2 = dx * dx + dy * dy;
                    if (d2 < rr2 && d2 > 0.0001) {
                        const d = Math.sqrt(d2);
                        const push = (1 - d / REPULSE_RADIUS) * REPULSE_STRENGTH;
                        x += (dx / d) * push;
                        y += (dy / d) * push;
                    }
                }

                if (showHalos && s.halo) {
                    buckets[HALO_BUCKET].push(x, y, s.r * HALO_SCALE);
                }

                const alpha = 0.2 + 0.6 * (0.5 + 0.5 * Math.sin(s.tw));
                const aQ = clamp(Math.round(alpha * 10), 2, 8);
                buckets[s.ci * ALPHA_LEVELS + aQ].push(x, y, s.r);
            }

            // additive blending on dark (overlaps brighten), normal on light
            ctx!.globalCompositeOperation = dark ? "lighter" : "source-over";

            // halos first — soft glow rings behind the brightest stars
            if (showHalos) {
                const hb = buckets[HALO_BUCKET];
                const L = hb.length;
                if (L) {
                    ctx!.beginPath();
                    for (let i = 0; i < L; i += 3) {
                        const hx = hb[i];
                        const hy = hb[i + 1];
                        const hr = hb[i + 2];
                        ctx!.moveTo(hx + hr, hy);
                        ctx!.arc(hx, hy, hr, 0, Math.PI * 2);
                    }
                    ctx!.fillStyle = dark ? "rgba(214,220,255,0.055)" : "rgba(179,156,208,0.05)";
                    ctx!.fill();
                }
            }

            // batched stars — one path per (palette × alpha step) bucket
            for (let b = 0; b < HALO_BUCKET; b++) {
                const arr = buckets[b];
                const L = arr.length;
                if (!L) continue;
                const ci = (b / ALPHA_LEVELS) | 0;
                const aQ = b % ALPHA_LEVELS;
                ctx!.beginPath();
                for (let i = 0; i < L; i += 3) {
                    const sx = arr[i];
                    const sy = arr[i + 1];
                    const sr = arr[i + 2];
                    ctx!.moveTo(sx + sr, sy);
                    ctx!.arc(sx, sy, sr, 0, Math.PI * 2);
                }
                ctx!.fillStyle = `${palette[ci]}${(aQ / 10).toFixed(1)})`;
                ctx!.fill();
            }

            ctx!.globalCompositeOperation = "source-over";
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
            render(document.documentElement.classList.contains("dark"), performance.now());
            raf = requestAnimationFrame(frame);
        }

        function onVis() {
            if (document.hidden) cancelAnimationFrame(raf);
            else raf = requestAnimationFrame(frame);
        }

        function onPointerMove(e: PointerEvent) {
            if (!interactive || reducedMotion) return;
            const rect = canvas!.getBoundingClientRect();
            if (rect.width === 0 || rect.height === 0) return;
            pointer.x = e.clientX - rect.left;
            pointer.y = e.clientY - rect.top;
            pointer.active = true;
        }

        function onPointerLeave() {
            pointer.active = false;
        }

        resize();
        // paint once immediately — this is also the entire effect for reduced
        // motion users (static galaxy instead of an empty hero)
        render(document.documentElement.classList.contains("dark"), 0);

        if (!reducedMotion) {
            raf = requestAnimationFrame(frame);
            window.addEventListener("resize", resize);
            document.addEventListener("visibilitychange", onVis);
            if (interactive) {
                window.addEventListener("pointermove", onPointerMove);
                document.addEventListener("pointerleave", onPointerLeave);
                window.addEventListener("blur", onPointerLeave);
            }
        }

        // first-open fix: on initial load CSS may not be painted yet, so
        // offsetWidth is 0 and the canvas measures empty. ResizeObserver
        // re-measures as soon as the canvas gets its real layout size. For
        // reduced motion we repaint here; otherwise the next rAF does.
        const ro = new ResizeObserver(() => {
            const pw = canvas!.offsetWidth;
            const ph = canvas!.offsetHeight;
            if (pw > 0 && ph > 0 && (pw !== w || ph !== h)) {
                resize();
                if (reducedMotion) render(document.documentElement.classList.contains("dark"), 0);
            }
        });
        ro.observe(canvas);

        return () => {
            cancelAnimationFrame(raf);
            ro.disconnect();
            window.removeEventListener("resize", resize);
            document.removeEventListener("visibilitychange", onVis);
            window.removeEventListener("pointermove", onPointerMove);
            document.removeEventListener("pointerleave", onPointerLeave);
            window.removeEventListener("blur", onPointerLeave);
        };
    }, [density, speed, interactive, showCoreGlow, showNebula, showHalos]);

    return <canvas ref={canvasRef} className="particle-canvas" aria-hidden="true" />;
}
