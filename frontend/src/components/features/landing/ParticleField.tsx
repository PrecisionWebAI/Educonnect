'use client'

import { useEffect, useRef } from 'react'

interface Star {
  orbitR: number
  angle: number
  speed: number
  wobble: number
  wobbleSpeed: number
  r: number
  tw: number
  color: string
  squash: number
}

/**
 * Galaxy particle field — stars orbiting a centre in slow spiral arms,
 * with twinkling dust. Fixed to the full viewport, behind all content.
 * Pure canvas, zero dependencies, reduced-motion aware.
 */
export default function ParticleField() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const PALETTE = [
      'rgba(214,220,255,', // soft star white-blue (majority)
      'rgba(214,220,255,',
      'rgba(45,212,191,',  // teal (accent-2)
      'rgba(167,139,250,', // violet
      'rgba(100,108,255,', // accent
    ]

    let w = 0
    let h = 0
    let raf = 0
    let stars: Star[] = []
    let time = 0
    let cx = 0
    let cy = 0

    function build() {
      // radii must reach from the far-below centre up to the badge line,
      // otherwise no star would be visible inside the canvas band
      const maxR = Math.hypot(w * 0.6, cy - h * 0.12) * 1.05
      const count = Math.min(560, Math.max(240, Math.floor((w * h) / 3600)))
      stars = Array.from({ length: count }, (_, i) => {
        // spiral arms: bias starting angle along 2 arms + spread
        const arm = i % 2
        const orbitR = 100 + Math.pow(Math.random(), 0.9) * maxR
        const armBias = arm * Math.PI + orbitR * 0.0035 + (Math.random() - 0.5) * 0.9
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
          color: PALETTE[Math.random() < 0.62 ? 0 : 2 + Math.floor(Math.random() * 3)],
          squash: 0.42 + Math.random() * 0.16, // vertical squash = disk perspective
        }
      })
    }

    function resize() {
      if (!canvas) return
      const dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = canvas.offsetWidth
      h = canvas.offsetHeight
      canvas.width = w * dpr
      canvas.height = h * dpr
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
      cx = w / 2
      cy = h * 1.5
      build()
    }

    function frame() {
      time += 1 / 60
      ctx!.clearRect(0, 0, w, h)

      // faint galactic core glow
      const core = ctx!.createRadialGradient(cx, cy, 0, cx, cy, 240)
      core.addColorStop(0, 'rgba(100,108,255,0.10)')
      core.addColorStop(1, 'rgba(100,108,255,0)')
      ctx!.fillStyle = core
      ctx!.fillRect(0, 0, w, h)

      // stars use additive blending — overlaps brighten (glow), never go dark
      ctx!.globalCompositeOperation = 'lighter'
      for (const s of stars) {
        s.angle += s.speed
        s.wobble += s.wobbleSpeed
        s.tw += 0.02

        const rr = s.orbitR + Math.sin(s.wobble) * 14 // radial breathing
        const x = cx + Math.cos(s.angle) * rr
        const y = cy + Math.sin(s.angle) * rr * s.squash

        const alpha = 0.2 + 0.6 * (0.5 + 0.5 * Math.sin(s.tw))
        ctx!.beginPath()
        ctx!.arc(x, y, s.r, 0, Math.PI * 2)
        ctx!.fillStyle = `${s.color}${alpha.toFixed(3)})`
        ctx!.fill()
      }
      ctx!.globalCompositeOperation = 'source-over'
      raf = requestAnimationFrame(frame)
    }

    function onVis() {
      if (document.hidden) cancelAnimationFrame(raf)
      else raf = requestAnimationFrame(frame)
    }

    resize()
    raf = requestAnimationFrame(frame)
    window.addEventListener('resize', resize)
    document.addEventListener('visibilitychange', onVis)
    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', resize)
      document.removeEventListener('visibilitychange', onVis)
    }
  }, [])

  return <canvas ref={canvasRef} className="particle-canvas" aria-hidden="true" />
}