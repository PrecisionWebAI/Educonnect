"use client";

import { useState, useSyncExternalStore } from "react";
import Splash from "./Splash";

const emptySubscribe = () => () => {};

// PAGE 01 — shows the splash once per app load, then unmounts.
export default function SplashOverlay() {
    // Render only after mount — splash is purely visual and its content
    // depends on client-only auth state, so skip SSR entirely.
    const isClient = useSyncExternalStore(
        emptySubscribe,
        () => true,
        () => false,
    );
    const [show, setShow] = useState(true);

    if (!isClient || !show) return null;
    return <Splash onDone={() => setShow(false)} />;
}
