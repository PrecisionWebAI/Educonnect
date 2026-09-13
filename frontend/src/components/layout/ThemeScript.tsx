/**
 * ThemeScript prevents Flash of Unstyled Content (FOUC) on Next.js initial render.
 * It executes synchronously in the <head> before page paint to apply the user's
 * preferred theme (.dark or .light) directly onto <html>.
 *
 * Uses next/script (beforeInteractive) instead of a raw <script> tag — React 19
 * never executes <script> elements rendered inside components, and logs a dev
 * console error for them. next/script injects the code outside React's renderer.
 */
import Script from "next/script";

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
        <Script
            id="educonnect-theme-script"
            strategy="beforeInteractive"
            dangerouslySetInnerHTML={{ __html: code }}
        />
    );
}
