"use client";

import { useSyncExternalStore } from "react";

const emptySubscribe = () => () => {};

/**
 * React 19.3+ (Next.js 16) logs a dev error if a `<script>` tag is rendered during
 * client-side rendering (since dynamically inserted scripts in React trees are not executed).
 *
 * `useSyncExternalStore` returns `true` during the SSR pass and the initial hydration render,
 * and `false` on any subsequent client render.
 *
 * This ensures:
 * 1. The inline script is rendered into the server HTML → executes before first paint (no theme FOUC).
 * 2. It matches during initial hydration pass.
 * 3. On subsequent client-side renders, the `<script>` tag is removed from the React tree,
 *    preventing React 19's "Encountered a script tag while rendering React component" error.
 */
export function ThemeScript() {
    const isServerOrHydrating = useSyncExternalStore(
        emptySubscribe,
        () => false, // Client snapshot
        () => true,  // Server snapshot
    );

    if (!isServerOrHydrating) {
        return null;
    }

    const themeInitializationCode = `(function(){try{var k='educonnect-theme';var s=localStorage.getItem(k);var p=window.matchMedia('(prefers-color-scheme: dark)').matches;var d=s==='dark'||(s!=='light'&&p);var r=document.documentElement;r.classList.toggle('dark',d);r.classList.toggle('light',!d);}catch(e){}})();`;

    return (
        <script
            id="educonnect-theme-script"
            suppressHydrationWarning
            dangerouslySetInnerHTML={{ __html: themeInitializationCode }}
        />
    );
}
