// ============================================================================
// Educonnect / EduVerse — Shared Prettier Configuration (monorepo root)
// Applies to BOTH frontend (TS/TSX) and backend (Python) consistently.
// ============================================================================

/** @type {import("prettier").Config} */
const config = {
    // ---- Core formatting ----
    printWidth: 100,
    tabWidth: 4,
    useTabs: false,

    // Semicolons & quotes (JS/TSX)
    semi: true,
    singleQuote: false,
    quoteProps: "as-needed",

    // Trailing / spacing behavior
    trailingComma: "all",
    bracketSpacing: true,
    proseWrap: "preserve",

    // Sorts Tailwind utility classes consistently.
    // Tailwind v4 auto-detected (no tailwind.config.ts needed for the plugin).
    plugins: ["prettier-plugin-tailwindcss"],
};

export default config;
