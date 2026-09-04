"use client";

import { Card } from "@/components/ui";
import Icon from "@/components/ui/Icon";

// Stitch: attendance_management_desktop → "Attention Required" list.
export default function AttentionList({ alerts }: { alerts: { name: string; reason: string }[] }) {
    return (
        <Card title="Attention Required">
            {alerts.length === 0 ? (
                <p style={{ color: "var(--muted)", fontSize: "0.88rem" }}>
                    All good — no flags today.
                </p>
            ) : (
                <ul className="feed">
                    {alerts.map((a) => (
                        <li key={a.name} className="feed-item">
                            <span className="feed-ico feed-ico-warn">
                                <Icon name="warning" size={16} />
                            </span>
                            <div className="feed-body">
                                <span className="feed-title">{a.name}</span>
                                <span className="feed-sub">{a.reason}</span>
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </Card>
    );
}
