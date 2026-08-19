// ============================================================================
// Educonnect / EduVerse — Shared Prettier Configuration (monorepo root)
// Applies to BOTH frontend (TS/TSX) and backend (Python) consistently.
// ============================================================================

/** @type {import("prettier").Config} */
const config = {
  // ---- Core formatting ----
  printWidth: 100,
  tabWidth: 2,
  useTabs: false,

  // Semicolons & quotes (JS/TSX)
  semi: true,
  singleQuote: false,
  quoteProps: "as-needed",

  // Trailing / spacing behavior
  trailingComma: "all",
  bracketSpacing: true,
  proseWrap: "preserve",

  // Keep Tailwind utility class order stable across the Next.js/Tailwind app.
  plugins: ["prettier-plugin-tailwindcss"],
  tailwindConfig: "./frontend/tailwind.config.ts",
};

export default config;
