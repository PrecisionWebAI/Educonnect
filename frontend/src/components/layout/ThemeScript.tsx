/**
 * ThemeScript prevents Flash of Unstyled Content (FOUC) on Next.js initial render.
 * It executes synchronously in the <head> before page paint to apply the user's
 * preferred theme (.dark or .light) directly onto <html>.
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

    return <script dangerouslySetInnerHTML={{ __html: code }} />;
}
