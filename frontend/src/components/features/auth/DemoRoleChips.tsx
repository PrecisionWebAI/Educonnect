"use client";

import { Button } from "@/components/ui";

// Quick demo role access chips connected to backend seeded accounts.
const ACCOUNTS = [
    { label: "Admin / Director", identifier: "admin@eduverse.com", password: "admin123" },
    { label: "Principal", identifier: "principal@eduverse.com", password: "password" },
    { label: "Teacher", identifier: "teacher@eduverse.com", password: "password" },
    { label: "Student", identifier: "student@eduverse.com", password: "password" },
    { label: "Parent", identifier: "parent@eduverse.com", password: "password" },
];

export default function DemoRoleChips({
    disabled,
    onPick,
}: {
    disabled: boolean;
    onPick: (identifier: string, password: string) => void;
}) {
    return (
        <div className="demo-grid">
            {ACCOUNTS.map((d) => (
                <Button
                    key={d.label}
                    type="button"
                    variant="outline"
                    size="sm"
                    className="demo-chip h-auto justify-center py-2"
                    disabled={disabled}
                    onClick={() => onPick(d.identifier, d.password)}
                >
                    {d.label}
                </Button>
            ))}
        </div>
    );
}
