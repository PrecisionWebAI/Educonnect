'use client'

import { useState } from 'react'
import Splash from './Splash'

// PAGE 01 — shows the splash once per app load, then unmounts.
export default function SplashOverlay() {
  const [show, setShow] = useState(true)
  if (!show) return null
  return <Splash onDone={() => setShow(false)} />
}