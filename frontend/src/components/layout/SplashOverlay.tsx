'use client'

import { useEffect, useState } from 'react'
import Splash from './Splash'

// PAGE 01 — shows the splash once per app load, then unmounts.
export default function SplashOverlay() {
  // Render only after mount — splash is purely visual and its content
  // depends on client-only auth state, so skip SSR entirely.
  const [mounted, setMounted] = useState(false)
  const [show, setShow] = useState(true)

  useEffect(() => setMounted(true), [])

  if (!mounted || !show) return null
  return <Splash onDone={() => setShow(false)} />
}