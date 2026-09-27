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

    // Applies the stored theme before paint. Each id maps to the DOM class it
    // resolves to (0 = light, 1 = dark) and is written to `data-theme`, which
    // selects the numbered preset tokens in `globals.css`. Unknown values fall
    // back to "light".
    const themeInitializationCode = `(function(){try{var k='educonnect-theme';var m={light:0,dark:1,'pure-dark':1,'midnight-blue':1};var s=localStorage.getItem(k);if(!(s in m)){s='light';}var d=m[s]===1;var r=document.documentElement;r.classList.toggle('dark',d);r.classList.toggle('light',!d);r.setAttribute('data-theme',s);}catch(e){}})();`;

    return (
        <script
            id="educonnect-theme-script"
            suppressHydrationWarning
            dangerouslySetInnerHTML={{ __html: themeInitializationCode }}
        />
    );
}
