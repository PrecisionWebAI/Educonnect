"use client";

import { useState } from "react";
import { Button, Modal } from "@/components/ui";
import type { LoginCredential } from "@/types";

// The logins an admission created: the student's school address and the
// guardian's, with the first-time password.
//
// The password only exists at the moment a login is created (or reset) - the
// database keeps a hash - so this panel is the one chance to hand it over. Each
// row therefore has a Reset button for when that chance was missed.
//
// A row with `created: false` is a login that already existed: the same parent's
// second child shares it, so no new password was issued.

// The panel is shared by admission (student + guardian logins) and staff hiring
// (teacher / staff logins), so the label is looked up by role codename.
const ROLE_LABEL: Record<string, string> = {
    student: "Student login",
    guardian: "Guardian login",
    teacher: "Teacher login",
    class_teacher: "Class teacher login",
    subject_teacher: "Subject teacher login",
    hod: "HOD login",
    vice_principal: "Vice principal login",
    principal: "Principal login",
    accountant: "Accounts login",
    librarian: "Library login",
    transport: "Transport login",
    staff: "Staff login",
};

export default function AdmissionCredentials({
    open,
    title,
    note,
    credentials,
    resetting,
    onReset,
    onClose,
}: {
    open: boolean;
    title: string;
    /** Optional wording - staff hiring passes its own instead of the admission text. */
    note?: string;
    credentials: LoginCredential[];
    /** The role being reset right now, so only that button shows progress. */
    resetting: LoginCredential["role"] | null;
    onReset: (target: LoginCredential["role"]) => void;
    onClose: () => void;
}) {
    const [copied, setCopied] = useState<string | null>(null);

    async function copy(label: string, value: string) {
        try {
            await navigator.clipboard.writeText(value);
            setCopied(label);
            window.setTimeout(() => setCopied(null), 1500);
        } catch {
            setCopied(null);
        }
    }

    return (
        <Modal open={open} title={title} onClose={onClose}>
            <div className="space-y-4">
                <p className="text-muted-foreground text-sm">
                    {note ?? (
                        <>
                            These logins were created for this admission. A first-time password is
                            shown <strong>only now</strong> - only its hash is stored - so copy it
                            and hand it to the family. Press Reset on a row to issue a new one (the
                            old password stops working).
                        </>
                    )}
                </p>

                {credentials.map((credential) => (
                    <CredentialRow
                        key={credential.role}
                        credential={credential}
                        copied={copied}
                        resetting={resetting}
                        onCopy={copy}
                        onReset={onReset}
                    />
                ))}

                <div className="flex justify-end">
                    <Button variant="primary" onClick={onClose}>
                        Done
                    </Button>
                </div>
            </div>
        </Modal>
    );
}

function CredentialRow({
    credential,
    copied,
    resetting,
    onCopy,
    onReset,
}: {
    credential: LoginCredential;
    copied: string | null;
    resetting: LoginCredential["role"] | null;
    onCopy: (label: string, value: string) => void;
    onReset: (target: LoginCredential["role"]) => void;
}) {
    return (
        <div className="space-y-2 rounded-lg border border-[var(--border)] p-3">
            <div className="flex items-baseline justify-between gap-2">
                <div>
                    <div className="text-sm font-semibold">
                        {ROLE_LABEL[credential.role] ?? `${credential.role} login`}
                    </div>
                    <div className="text-muted-foreground text-xs">{credential.fullName}</div>
                </div>
                {!credential.created && (
                    <span className="text-muted-foreground text-xs">
                        existing login - shared with their other children
                    </span>
                )}
            </div>

            <div className="flex items-center justify-between gap-2">
                <code className="text-sm break-all">{credential.email}</code>
                <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onCopy(`${credential.role}-email`, credential.email)}
                >
                    {copied === `${credential.role}-email` ? "Copied" : "Copy"}
                </Button>
            </div>

            <div className="flex items-center justify-between gap-2">
                {credential.password ? (
                    <code className="text-sm font-semibold tracking-wide">
                        {credential.password}
                    </code>
                ) : (
                    <span className="text-muted-foreground text-sm">
                        password already handed over
                    </span>
                )}
                <div className="flex gap-2">
                    {credential.password && (
                        <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                                onCopy(`${credential.role}-password`, credential.password ?? "")
                            }
                        >
                            {copied === `${credential.role}-password` ? "Copied" : "Copy"}
                        </Button>
                    )}
                    <Button
                        size="sm"
                        variant="ghost"
                        disabled={resetting === credential.role}
                        onClick={() => onReset(credential.role)}
                    >
                        {resetting === credential.role ? "Resetting…" : "Reset"}
                    </Button>
                </div>
            </div>
        </div>
    );
}
