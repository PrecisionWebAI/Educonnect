/**
 * ThemeScript prevents Flash of Unstyled Content (FOUC) on Next.js initial
 * render. It executes synchronously while the browser parses <body>, before the
 * page paints, and applies the stored/system theme directly onto <html>.
 *
 * WHY a plain <script> (and NOT next/script):
 *   With `strategy="beforeInteractive"` in the App Router, next/script does not
 *   emit the inline code — it pushes it into the `self.__next_s` queue that
 *   Next's runtime flushes later (after the framework JS loads). That is too
 *   late to beat the first paint, so the theme would flash.
 *   A plain inline <script> is parsed and executed immediately = no flash.
 *
 * WHY it must live INSIDE <body> (see app/layout.tsx):
 *   React 19 validates host elements it cannot hoist. An inline script has no
 *   `async` + `src`, so React logs:
 *     "Cannot render a sync or defer <script> outside the main document…"
 *   whenever it is rendered *outside* the document container (e.g. as a direct
 *   child of <html>). Inside <body> it is a normal element: React hydrates the
 *   server-rendered node instead of creating one, so no warning is logged.
 *
 * `suppressHydrationWarning` is required because the script mutates <html>'s
 * class list (dark/light) before React hydrates — the DOM intentionally
 * differs from the server HTML at that point.
 */
export function ThemeScript() {
    const code = `
(function() {
  try {
    var key = 'educonnect-theme';
    var stored = localStorage.getItem(key);
    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    var isDark = stored === 'dark' || (stored !== 'light' && prefersDark);
    var root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
  } catch (e) {}
})();
`;

    return (
        <script
            id="educonnect-theme-script"
            suppressHydrationWarning
            dangerouslySetInnerHTML={{ __html: code }}
        />
    );
}
