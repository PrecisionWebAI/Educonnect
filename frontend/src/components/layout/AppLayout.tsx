"use client";

import { useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-context";
import { NAV_GROUPS } from "@/lib/constants/nav";
import { hasAnyRole } from "@/lib/auth/rbac";
import { ROLE_LABELS } from "@/types";
import Icon from "@/components/ui/Icon";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarHeader,
    SidebarMenu,
    SidebarMenuBadge,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarProvider,
    SidebarTrigger,
} from "@/components/ui/sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
    const { user, logout } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    const primaryRole = user?.roles[0] ?? "STAFF";
    const roleLabel = ROLE_LABELS[primaryRole] ?? primaryRole;

    const filteredNavGroups = useMemo(() => {
        return NAV_GROUPS.map((group) => ({
            ...group,
            items: group.items.filter((item) => hasAnyRole(user?.roles, item.roles)),
        })).filter((group) => group.items.length > 0);
    }, [user?.roles]);

    async function handleLogout() {
        await logout();
        router.push("/auth");
    }

    // Map the current route to an Aurora module accent (blueprint column colors).
    function moduleForPath(path: string): string {
        const seg = path.split("/")[2] ?? "dashboard";
        const map: Record<string, string> = {
            dashboard: "dashboard",
            notifications: "dashboard",
            "ai-copilot": "dashboard",
            chat: "dashboard",
            students: "academics",
            attendance: "attendance",
            academics: "academics",
            exams: "academics",
            homework: "academics",
            classroom: "classroom",
            timetable: "timetable",
            teachers: "hr",
            payroll: "finance",
            finance: "finance",
            library: "library",
            transport: "transport",
            meetings: "meetings",
            tickets: "tickets",
            leave: "leave",
            reports: "reports",
            settings: "dashboard",
        };
        return map[seg] ?? "dashboard";
    }

    return (
        <SidebarProvider>
            {/* Shadcn Sidebar replaces the custom <aside className="sidebar"> */}
            <Sidebar collapsible="icon">
                <SidebarHeader className="flex flex-row items-center gap-2 p-4 group-data-[collapsible=icon]:p-2 group-data-[collapsible=icon]:justify-center">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src="/logo.png" alt="EduConnect" className="h-8 w-8 shrink-0" />
                    <span className="text-lg font-bold tracking-tight group-data-[collapsible=icon]:hidden">EduConnect</span>
                </SidebarHeader>

                <SidebarContent>
                    {filteredNavGroups.map((group) => (
                        <SidebarGroup key={group.title}>
                            <SidebarGroupLabel>{group.title}</SidebarGroupLabel>
                            <SidebarGroupContent>
                                <SidebarMenu>
                                    {group.items.map((item) => (
                                        <SidebarMenuItem key={item.to}>
                                            <SidebarMenuButton
                                                render={<Link href={item.to} />}
                                                isActive={pathname === item.to}
                                                tooltip={item.label}
                                            >
                                                <Icon name={item.icon} size={18} />
                                                <span className="group-data-[collapsible=icon]:hidden">{item.label}</span>
                                            </SidebarMenuButton>
                                            {item.badge !== undefined && item.badge > 0 && (
                                                <SidebarMenuBadge className="bg-primary text-primary-foreground rounded-full">
                                                    {item.badge}
                                                </SidebarMenuBadge>
                                            )}
                                        </SidebarMenuItem>
                                    ))}
                                </SidebarMenu>
                            </SidebarGroupContent>
                        </SidebarGroup>
                    ))}
                </SidebarContent>
            </Sidebar>

            <div className="bg-background flex min-w-0 flex-1 flex-col">
                {/* Topbar */}
                <header className="bg-background/80 sticky top-0 z-30 flex h-14 items-center gap-4 border-b px-4 backdrop-blur-md sm:px-6">
                    <SidebarTrigger />
                    <div className="flex flex-1 items-center space-x-2">
                        <Icon
                            name="search"
                            size={16}
                            className="text-muted-foreground hidden sm:block"
                        />
                        <input
                            type="text"
                            placeholder="Search students, classes, modules… (⌘K)"
                            className="hidden w-full max-w-75 border-none bg-transparent text-sm outline-none focus:ring-0 sm:block"
                        />
                    </div>

                    <div className="flex items-center space-x-4">
                        <ThemeToggle />

                        <Link
                            href="/dashboard/notifications"
                            className="hover:bg-accent text-muted-foreground hover:text-foreground relative flex items-center justify-center rounded-md p-2 transition-colors"
                            aria-label="Notifications"
                        >
                            <Icon name="bell" size={18} />
                            <span className="absolute top-1 right-1 flex h-2 w-2 rounded-full bg-red-500"></span>
                        </Link>

                        <Link
                            href="/dashboard/ai-copilot"
                            className="hover:bg-accent text-muted-foreground hover:text-foreground flex items-center justify-center rounded-md p-2 transition-colors"
                            aria-label="AI Copilot"
                        >
                            <Icon name="ai" size={18} />
                        </Link>

                        <div className="hidden items-center gap-2 px-2 md:flex">
                            <div className="bg-primary/10 text-primary flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium">
                                {user?.fullName?.[0] ?? "U"}
                            </div>
                            <div className="flex flex-col">
                                <span className="text-sm leading-none font-medium">
                                    {user?.fullName}
                                </span>
                                <span className="text-muted-foreground mt-1 text-xs">
                                    {roleLabel}
                                </span>
                            </div>
                        </div>

                        <button
                            className="text-muted-foreground hover:text-foreground text-sm font-medium transition-colors"
                            onClick={() => void handleLogout()}
                        >
                            Log out
                        </button>
                    </div>
                </header>

                {/* Main Content Area */}
                <main
                    data-module={moduleForPath(pathname)}
                    className="aurora-bg flex-1 overflow-auto p-4 sm:p-6 md:p-8"
                >
                    {children}
                </main>
            </div>
        </SidebarProvider>
    );
}
