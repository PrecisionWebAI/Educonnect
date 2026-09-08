"use client";
import { useEffect, useMemo, useState } from "react";
import {
    PageHeader,
    Tabs,
    Spinner,
    Table,
    Badge,
    Card,
    Button,
    Input,
    Select,
    type BadgeTone,
} from "@/components/ui";
import { useAuth } from "@/providers/auth-context";
import { hasAnyRole, LEADERSHIP_ROLES } from "@/lib/auth/rbac";
import { getGateways } from "@/services";
import { useApiQuery } from "@/lib/api/use-api-query";
import type { GatewayStatus } from "@/types";
import { useSettings, type SettingsTab } from "./useSettings";
import type { SettingUser } from "@/types";

const ALL_TABS: SettingsTab[] = [
    "Users & Roles",
    "School Profile",
    "Security",
    "Integrations & Prefs",
];
const roleTone: Record<SettingUser["role"], BadgeTone> = {
    Admin: "red",
    Teacher: "teal",
    Accountant: "violet",
    Staff: "accent",
};
const statusTone: Record<SettingUser["status"], BadgeTone> = {
    Active: "green",
    Invited: "amber",
    Disabled: "red",
};

export default function SettingsPage() {
    const s = useSettings();
    const { user } = useAuth();
    const canManageUsers = hasAnyRole(user?.roles, LEADERSHIP_ROLES);

    const allowedTabs = useMemo(() => {
        if (canManageUsers) return ALL_TABS;
        return ["Security" as SettingsTab, "Integrations & Prefs" as SettingsTab];
    }, [canManageUsers]);

    const activeTab = allowedTabs.includes(s.tab) ? s.tab : allowedTabs[0];
    const gatewaysQuery = useApiQuery(["settings", "gateways"], getGateways);
    const gateways = gatewaysQuery.data ?? [];

    const gwTone: Record<GatewayStatus["status"], BadgeTone> = {
        Connected: "green",
        Degraded: "amber",
        Down: "red",
    };

    const userCols = [
        { key: "name", header: "Name", render: (u: SettingUser) => <b>{u.name}</b> },
        { key: "email", header: "Email" },
        {
            key: "role",
            header: "Role",
            render: (u: SettingUser) => <Badge tone={roleTone[u.role]}>{u.role}</Badge>,
        },
        {
            key: "status",
            header: "Status",
            render: (u: SettingUser) => <Badge tone={statusTone[u.status]}>{u.status}</Badge>,
        },
    ];

    return (
        <div>
            <PageHeader
                title="Settings & Configuration"
                subtitle="Manage users, school profile and security."
            />

            {s.loading ? (
                <Spinner />
            ) : (
                <>
                    <div className="stat-tiles">
                        <div className="stat-tile">
                            <b>{s.activeCount}</b>
                            <span>Active users</span>
                        </div>
                        <div className="stat-tile">
                            <b>{s.pendingCount}</b>
                            <span>Pending invites</span>
                        </div>
                        <div className="stat-tile">
                            <b>{s.logs.length}</b>
                            <span>Security events</span>
                        </div>
                    </div>

                    <Tabs
                        tabs={allowedTabs}
                        active={activeTab}
                        onChange={(t) => s.setTab(t as SettingsTab)}
                    />

                    {activeTab === "Users & Roles" && canManageUsers && (
                        <>
                            <div className="toolbar" style={{ margin: "16px 0" }}>
                                <Input placeholder="Search users..." />
                                <Button variant="primary">Invite user</Button>
                            </div>
                            <Table
                                columns={userCols}
                                rows={s.users}
                                rowKey={(u) => u.id}
                                empty="No users yet."
                            />
                        </>
                    )}

                    {activeTab === "School Profile" && canManageUsers && (
                        <>
                            <div className="kpi-grid">
                                {s.info.map((i) => (
                                    <Card key={i.id} title={i.label}>
                                        <p>{i.value}</p>
                                    </Card>
                                ))}
                            </div>
                            <div className="modal-actions">
                                <Button variant="primary">Save changes</Button>
                            </div>
                        </>
                    )}

                    {activeTab === "Integrations & Prefs" && (
                        <>
                            <h3 style={{ margin: "16px 0 12px" }}>Integrations</h3>
                            <Table
                                columns={[
                                    {
                                        key: "name",
                                        header: "Service",
                                        render: (g: GatewayStatus) => <b>{g.name}</b>,
                                    },
                                    { key: "type", header: "Type" },
                                    {
                                        key: "status",
                                        header: "Status",
                                        render: (g: GatewayStatus) => (
                                            <Badge tone={gwTone[g.status]}>{g.status}</Badge>
                                        ),
                                    },
                                    { key: "quota", header: "Usage / quota" },
                                ]}
                                rows={gateways}
                                rowKey={(g) => g.id}
                                empty="No integrations configured."
                            />

                            <h3 style={{ margin: "24px 0 12px" }}>My preferences</h3>
                            <Card title="Personal preferences">
                                <div className="form-grid">
                                    <Select label="Language">
                                        <option>English</option>
                                        <option>हिन्दी</option>
                                        <option>मराठी</option>
                                    </Select>
                                    <Select label="Theme" defaultValue="system">
                                        <option value="system">System</option>
                                        <option value="dark">Dark</option>
                                        <option value="light">Light</option>
                                    </Select>
                                    <Select label="Notification channel">
                                        <option>In-app + WhatsApp</option>
                                        <option>In-app only</option>
                                        <option>Email digest</option>
                                    </Select>
                                    <Select label="Density">
                                        <option>Comfortable</option>
                                        <option>Compact</option>
                                    </Select>
                                </div>
                                <div className="modal-actions">
                                    <Button
                                        variant="primary"
                                        onClick={() => alert("Preferences saved (mock).")}
                                    >
                                        Save preferences
                                    </Button>
                                </div>
                            </Card>
                        </>
                    )}
                    {activeTab === "Security" && (
                        <div style={{ marginTop: 16 }}>
                            <Table
                                columns={[
                                    {
                                        key: "event",
                                        header: "Event",
                                        render: (l) => <b>{l.event}</b>,
                                    },
                                    { key: "user", header: "User" },
                                    { key: "when", header: "When" },
                                ]}
                                rows={s.logs}
                                rowKey={(l) => l.id}
                                empty="No security events."
                            />
                        </div>
                    )}
                </>
            )}
        </div>
    );
}
