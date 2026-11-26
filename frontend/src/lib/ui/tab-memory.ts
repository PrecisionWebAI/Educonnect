/**
 * Which tab a page was on, remembered across a refresh.
 *
 * The shared `Tabs` keeps the choice in `sessionStorage` (per browser tab, gone when the tab
 * is closed): a refresh lands back on the tab the person was reading - in a class-section,
 * under Teachers, under Staff - without a URL full of `?tab=` noise and without touching the
 * thirty screens that own their tab state. These are the pure rules; `Tabs` does the storage.
 */

/**
 * The storage key for one set of tabs on one page.
 *
 * The page's path plus the **first** tab: stable when a later tab appears or disappears
 * (permissions loading, a tab that only some people hold), and different for two tab bars
 * on one page as long as they start with different tabs. A screen can pass its own
 * `persistKey` when two bars on a page would otherwise share one.
 */
export function tabStorageKey(
    pathname: string,
    tabs: readonly string[],
    persistKey?: string,
): string {
    return `edu-tab:${pathname}:${persistKey ?? tabs[0] ?? ""}`;
}

/**
 * The saved tab to go back to, or `null` when there is nothing to do.
 *
 * Only a tab that is **in the list right now** is restored (a tab the person may no longer
 * open, or that has not appeared yet, is left alone) and only when it differs from the one
 * already showing.
 */
export function tabToRestore(
    saved: string | null | undefined,
    tabs: readonly string[],
    active: string,
): string | null {
    if (!saved || saved === active) return null;
    return tabs.includes(saved) ? saved : null;
}
