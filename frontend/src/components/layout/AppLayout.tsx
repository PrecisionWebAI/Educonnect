"use client";

import { useCallback, useMemo, useState, type KeyboardEvent } from "react";
import { ChevronDown, LogOut } from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-context";
import { NAV_GROUPS } from "@/lib/constants/nav";
import { titleCase } from "@/lib/format";
import { hasAnyRole, hasPermission } from "@/lib/auth/rbac";
import { ROLE_LABELS, type Role } from "@/types";
import Icon, { type IconName } from "@/components/ui/Icon";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { AcademicYearSelect } from "@/components/layout/AcademicYearSelect";
import { useCopilotContext } from "@/providers/copilot-context";
import CopilotSheet from "@/components/features/copilot/CopilotSheet";
import { useNotificationsContext } from "@/providers/notifications-context";
import NotificationsSheet from "@/components/features/notifications/NotificationsSheet";
import {
    ImpersonationBanner,
    default as SwitchAccountMenu,
} from "@/components/layout/SwitchAccountMenu";
import SchoolScopeRequiredBanner from "@/components/layout/SchoolScopeRequiredBanner";
import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupContent,
    SidebarHeader,
    SidebarFooter,
    SidebarMenu,
    SidebarMenuBadge,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarMenuSub,
    SidebarMenuSubButton,
    SidebarMenuSubItem,
    SidebarProvider,
    SidebarTrigger,
} from "@/components/ui/sidebar";

const NAV_GROUP_ICONS: Record<string, IconName> = {
    Academic: "school",
    People: "guardian",
    Services: "chat",
    "Operations & Insights": "trending",
};

export default function AppLayout({ children }: { children: React.ReactNode }) {
    const { user, logout } = useAuth();
    const router = useRouter();
    const pathname = usePathname();
    const [navigationSearch, setNavigationSearch] = useState("");
    const [isSearchFocused, setIsSearchFocused] = useState(false);
    const { toggle: toggleCopilot } = useCopilotContext();
    const { toggle: toggleNotifications } = useNotificationsContext();

    // Provide a helper to check if the user has ANY of the item's permissions
    const checkItemAccess = useCallback(
        (permissions?: string[]) => {
            if (!permissions || permissions.length === 0) return true;
            if (!user) return false;
            // Check against user.permissions[] populated from the backend API
            return permissions.some((p) => hasPermission(user.permissions, p));
        },
        [user],
    );

    const primaryRole = user?.role?.toUpperCase() ?? "STAFF";
    const roleLabel = ROLE_LABELS[primaryRole as Role] ?? primaryRole;

    const isSystemAdmin =
        user?.role?.toUpperCase() === "SYSTEM_ADMIN" ||
        (user?.roles ?? []).some((r) => r.toUpperCase() === "SYSTEM_ADMIN");

    // The header's school context: a platform account (system_admin) wears the
    // platform's own name; every other account wears its own school's name - and a
    // platform account that picked one school in "Switch account" wears *that*
    // school's name, because that is the data it is looking at.
    const schoolLabel = user
        ? user.schoolScope && user.schoolName
            ? titleCase(user.schoolName)
            : isSystemAdmin
              ? "EduConnect School"
              : titleCase(user.schoolName)
        : "";

    // What the page is *showing*, as opposed to who the header says you are. A
    // switch changes the account or only the school; either way the rows on screen
    // have to change with it, so the main area is keyed on this - a new key
    // remounts the page, and a page that fetches in a plain effect refetches
    // instead of keeping the previous school's data until a manual reload.
    const viewKey = [
        user?.id ?? "anonymous",
        user?.schoolId ?? "all-schools",
        user?.impersonatedBy?.id ?? "",
    ].join(":");

    const filteredNavGroups = useMemo(() => {
        return NAV_GROUPS.map((group) => ({
            ...group,
            items: group.items.filter(
                (item) =>
                    (!item.roles || hasAnyRole(user?.roles, item.roles)) &&
                    checkItemAccess(item.permissions),
            ),
        })).filter((group) => group.items.length > 0);
    }, [checkItemAccess, user?.roles]);

    const navigationItems = useMemo(
        () =>
            filteredNavGroups.flatMap((group) =>
                group.items.map((item) => ({ ...item, groupTitle: group.title })),
            ),
        [filteredNavGroups],
    );
    const dashboardItem = navigationItems.find((item) => item.to === "/dashboard");
    const sidebarGroups = useMemo(
        () => filteredNavGroups.filter((group) => group.title !== "Dashboard"),
        [filteredNavGroups],
    );
    const searchQuery = navigationSearch.trim().toLowerCase();
    const searchResults = useMemo(
        () =>
            searchQuery
                ? navigationItems
                      .filter((item) => item.label.toLowerCase().includes(searchQuery))
                      .slice(0, 6)
                : [],
        [navigationItems, searchQuery],
    );
    const isRouteActive = useCallback(
        (to: string) => pathname === to || (to !== "/dashboard" && pathname.startsWith(`${to}/`)),
        [pathname],
    );
    const activeGroup = sidebarGroups.find((group) =>
        group.items.some((item) => isRouteActive(item.to)),
    );
    const [groupOverride, setGroupOverride] = useState<{
        pathname: string;
        title: string | null;
    } | null>(null);
    const expandedGroup =
        groupOverride?.pathname === pathname ? groupOverride.title : (activeGroup?.title ?? null);

    async function handleLogout() {
        await logout();
        router.push("/");
    }

    function openNavigationPage(path: string) {
        setNavigationSearch("");
        setIsSearchFocused(false);
        router.push(path);
    }

    function handleNavigationSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
        if (event.key === "Escape") {
            setNavigationSearch("");
            setIsSearchFocused(false);
        } else if (event.key === "Enter" && searchResults[0]) {
            event.preventDefault();
            openNavigationPage(searchResults[0].to);
        }
    }

    // Keep page accents consistent with the school-area navigation groups.
    function moduleForPath(path: string): string {
        const seg = path.split("/")[2] ?? "dashboard";
        const map: Record<string, string> = {
            dashboard: "dashboard",
            notifications: "dashboard",
            "ai-copilot": "dashboard",
            students: "academic",
            attendance: "academic",
            academics: "academic",
            exams: "academic",
            homework: "academic",
            classroom: "academic",
            timetable: "academic",
            "exam-results": "academic",
            teachers: "people",
            staff: "people",
            payroll: "people",
            chat: "services",
            library: "services",
            transport: "services",
            meetings: "services",
            tickets: "services",
            leave: "services",
            finance: "operations",
            operations: "operations",
            reports: "operations",
            settings: "operations",
        };
        return map[seg] ?? "dashboard";
    }

    return (
        <SidebarProvider className="app-shell">
            {/* Shadcn Sidebar replaces the custom <aside className="sidebar"> */}
            <Sidebar collapsible="icon" variant="floating" className="edu-sidebar">
                <SidebarHeader className="app-sidebar-header flex flex-row items-center gap-2 p-4 group-data-[collapsible=icon]:justify-center group-data-[collapsible=icon]:p-2">
                    <span className="app-brand-mark group-data-[collapsible=icon]:hidden">
                        <Image
                            src="/logo.png"
                            alt=""
                            width={28}
                            height={28}
                            className="h-7 w-7 shrink-0"
                        />
                    </span>
                    <span className="app-brand-name group-data-[collapsible=icon]:hidden">
                        EduConnect
                    </span>
                    {/* <SidebarTrigger className="app-sidebar-trigger ml-auto hidden group-data-[collapsible=icon]:ml-0 md:inline-flex" /> */}
                </SidebarHeader>

                <SidebarContent>
                    {dashboardItem && (
                        <SidebarGroup>
                            <SidebarGroupContent>
                                <SidebarMenu>
                                    <SidebarMenuItem>
                                        <SidebarMenuButton
                                            render={<Link href={dashboardItem.to} />}
                                            isActive={isRouteActive(dashboardItem.to)}
                                            tooltip={dashboardItem.label}
                                            aria-label={dashboardItem.label}
                                            data-nav-group="dashboard"
                                        >
                                            <Icon name={dashboardItem.icon} size={18} />
                                            <span className="group-data-[collapsible=icon]:hidden">
                                                {dashboardItem.label}
                                            </span>
                                        </SidebarMenuButton>
                                    </SidebarMenuItem>
                                </SidebarMenu>
                            </SidebarGroupContent>
                        </SidebarGroup>
                    )}
                    {sidebarGroups.map((group) => {
                        const groupId = `sidebar-group-${group.title
                            .toLowerCase()
                            .replace(/[^a-z0-9]+/g, "-")}`;
                        const navGroup = groupId.slice("sidebar-group-".length);
                        const isExpanded = expandedGroup === group.title;

                        return (
                            <SidebarGroup key={group.title}>
                                <SidebarGroupContent>
                                    <SidebarMenu>
                                        <SidebarMenuItem>
                                            <SidebarMenuButton
                                                type="button"
                                                onClick={() => {
                                                    setGroupOverride({
                                                        pathname,
                                                        title: isExpanded ? null : group.title,
                                                    });
                                                }}
                                                isActive={group.items.some((item) =>
                                                    isRouteActive(item.to),
                                                )}
                                                tooltip={group.title}
                                                aria-label={group.title}
                                                data-nav-group={navGroup}
                                                aria-expanded={isExpanded}
                                                aria-controls={groupId}
                                                id={`${groupId}-trigger`}
                                            >
                                                <Icon
                                                    name={NAV_GROUP_ICONS[group.title] ?? "more"}
                                                    size={18}
                                                />
                                                <span className="group-data-[collapsible=icon]:hidden">
                                                    {group.title}
                                                </span>
                                                <ChevronDown
                                                    aria-hidden="true"
                                                    className={`ml-auto size-4 shrink-0 transition-transform duration-200 ${
                                                        isExpanded ? "rotate-180" : ""
                                                    } group-data-[collapsible=icon]:hidden`}
                                                />
                                            </SidebarMenuButton>
                                            <SidebarMenuSub
                                                id={groupId}
                                                aria-labelledby={`${groupId}-trigger`}
                                                className={isExpanded ? "" : "hidden"}
                                                aria-hidden={!isExpanded}
                                            >
                                                {group.items.map((item) => (
                                                    <SidebarMenuSubItem key={item.to}>
                                                        <SidebarMenuSubButton
                                                            render={<Link href={item.to} />}
                                                            isActive={isRouteActive(item.to)}
                                                            data-nav-group={navGroup}
                                                        >
                                                            <Icon name={item.icon} size={16} />
                                                            <span>{item.label}</span>
                                                        </SidebarMenuSubButton>
                                                        {item.badge !== undefined &&
                                                            item.badge > 0 && (
                                                                <SidebarMenuBadge className="bg-primary text-primary-foreground rounded-full">
                                                                    {item.badge}
                                                                </SidebarMenuBadge>
                                                            )}
                                                    </SidebarMenuSubItem>
                                                ))}
                                            </SidebarMenuSub>
                                        </SidebarMenuItem>
                                    </SidebarMenu>
                                </SidebarGroupContent>
                            </SidebarGroup>
                        );
                    })}
                </SidebarContent>

                <SidebarFooter className="app-sidebar-footer">
                    <SidebarMenu>
                        <SidebarMenuItem>
                            <SidebarMenuButton
                                onClick={() => void handleLogout()}
                                tooltip="Log out"
                            >
                                <LogOut aria-hidden="true" />
                                <span className="group-data-[collapsible=icon]:hidden">
                                    Log out
                                </span>
                            </SidebarMenuButton>
                        </SidebarMenuItem>
                    </SidebarMenu>
                </SidebarFooter>
            </Sidebar>

            <div className="app-layout-content flex min-w-0 flex-1 flex-col">
                {/* Topbar */}
                <header
                    className="app-topbar sticky top-0 z-30 flex min-h-18 items-center gap-3 px-1 sm:px-6"
                    data-module={moduleForPath(pathname)}
                >
                    <SidebarTrigger className="app-topbar-control shrink-0 md:hidden" />
                    {/* The bar names the **school**, not the page: the sidebar already says
                        which page you are on. The name is the one word that should read from
                        across the room, so it takes all the width the controls leave. */}
                    <div className="min-w-0 flex-1" data-testid="app-topbar-school">
                        <h1 className="app-school-name truncate" title={schoolLabel || roleLabel}>
                            {schoolLabel || roleLabel}
                        </h1>
                        <div className="mt-1 flex min-w-0 items-center justify-start">
                            <AcademicYearSelect />
                        </div>
                    </div>

                    <div
                        className="app-navigation-search relative mx-auto hidden w-full max-w-sm items-center gap-2 lg:flex"
                        role="search"
                        onBlur={(event) => {
                            const nextTarget = event.relatedTarget;
                            if (
                                !(nextTarget instanceof Node) ||
                                !event.currentTarget.contains(nextTarget)
                            ) {
                                setIsSearchFocused(false);
                            }
                        }}
                    >
                        <Icon name="search" size={17} />
                        <input
                            type="search"
                            aria-label="Search navigation pages"
                            placeholder="Search pages..."
                            value={navigationSearch}
                            onChange={(event) => setNavigationSearch(event.target.value)}
                            onFocus={() => setIsSearchFocused(true)}
                            onKeyDown={handleNavigationSearchKeyDown}
                        />
                        {isSearchFocused && searchQuery && (
                            <div
                                id="app-navigation-search-results"
                                className="app-navigation-results"
                            >
                                {searchResults.length > 0 ? (
                                    <ul>
                                        {searchResults.map((item, index) => (
                                            <li key={item.to}>
                                                <Link
                                                    href={item.to}
                                                    onMouseDown={(event) => event.preventDefault()}
                                                    onClick={() => openNavigationPage(item.to)}
                                                    className="app-navigation-result"
                                                    id={
                                                        index === 0
                                                            ? "app-navigation-first-result"
                                                            : undefined
                                                    }
                                                >
                                                    <Icon name={item.icon} size={16} />
                                                    <span className="min-w-0 flex-1 truncate">
                                                        {item.label}
                                                    </span>
                                                    <span className="app-navigation-result-group">
                                                        {item.groupTitle}
                                                    </span>
                                                </Link>
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    <p className="app-navigation-empty">
                                        No pages match “{navigationSearch.trim()}”.
                                    </p>
                                )}
                            </div>
                        )}
                    </div>

                    <div className="ml-auto flex shrink-0 items-center gap-1.5 sm:gap-2">
                        {/* Super-admin account switcher: before the theme toggle,
                            and it renders nothing at all for other roles. */}
                        <SwitchAccountMenu />

                        <ThemeToggle className="app-topbar-control" />

                        <button
                            onClick={toggleNotifications}
                            className="app-topbar-control relative"
                            aria-label="Notifications"
                        >
                            <Icon name="bell" size={18} />
                            <span className="app-notification-dot" />
                        </button>

                        <button
                            onClick={toggleCopilot}
                            className="app-topbar-control hidden xl:inline-flex"
                            aria-label="AI Copilot"
                        >
                            <Icon name="ai" size={18} />
                        </button>

                        <div className="app-user-chip hidden items-center gap-2.5 lg:flex">
                            <div className="app-user-avatar">{user?.fullName?.[0] ?? "U"}</div>
                            <div className="hidden min-w-0 flex-col xl:flex">
                                <span className="max-w-36 truncate text-sm leading-none font-semibold">
                                    {user?.fullName}
                                </span>
                                <span className="app-user-role mt-1 truncate text-xs">
                                    {roleLabel}
                                </span>
                            </div>
                        </div>
                    </div>
                </header>

                <ImpersonationBanner />
                <SchoolScopeRequiredBanner />

                {/* Main Content Area */}
                <main
                    key={viewKey}
                    data-module={moduleForPath(pathname)}
                    className="app-main aurora-bg flex-1 overflow-auto p-4 sm:p-6 md:p-8"
                >
                    {children}
                </main>
            </div>

            <CopilotSheet />
            <NotificationsSheet />
        </SidebarProvider>
    );
}
