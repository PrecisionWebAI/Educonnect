"use client";

import { useState } from "react";
import {
    Badge,
    Button,
    Input,
    Label,
    Select,
    Spinner,
    Table,
    Tabs,
    type BadgeTone,
} from "@/components/ui";
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from "@/components/ui/sheet";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { titleCase } from "@/lib/format";
import {
    getStaffAudit,
    type CertificationInput,
    type EmploymentInput,
    type ExperienceInput,
    type QualificationInput,
} from "@/services";
import type { StaffAuditEntry, StaffDocumentRow, StaffProfileDetail } from "@/types";
import { useStaffProfile } from "./useStaffProfile";

/**
 * The profile drawer: one member of staff, everything the school holds about them.
 *
 * It opens from a directory row and reads `GET /teachers/{id}/profile` once - the
 * person, the post and the four lists together - so a tab can never show
 * something the row behind it does not.
 *
 * Two rules keep it honest:
 *
 * * **a leaver's drawer is read-only.** The record stays readable (the office still
 *   asks when they joined) but every edit control is gone and the banner says why;
 * * **a refused write is printed.** A duplicate degree is a `409` naming the pair it
 *   found, and an HOD outside their department is a `403` - both are the drawer's
 *   message, never a silent no-op.
 */
const BASE_TABS = [
    "Overview",
    "Qualifications",
    "Experience",
    "Certifications",
    "Documents",
    "History",
] as const;

/** `Activity` is added only for a caller who may read the audit trail. */
type ProfileTab = (typeof BASE_TABS)[number] | "Activity";

const STATUS_TONE: Record<StaffProfileDetail["status"], BadgeTone> = {
    Active: "green",
    "On Leave": "amber",
    Inactive: "muted",
};

const EMPLOYMENT_TYPES = ["Full-time", "Part-time", "Contract", "Guest"];

function initials(name: string): string {
    return name
        .split(" ")
        .map((part) => part[0])
        .slice(0, 2)
        .join("")
        .toUpperCase();
}

/** A stored value as the school writes it, or "—" when nothing is recorded. */
function shown(value: string | null | undefined): string {
    return value && value.trim() ? titleCase(value) : "—";
}

/** A date exactly as stored, or "—". */
function day(value: string | null | undefined): string {
    return value ?? "—";
}

function Detail({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <div className="text-muted-foreground text-xs">{label}</div>
            <div className="text-foreground text-sm font-medium">{value}</div>
        </div>
    );
}

export default function StaffProfileSheet({
    teacherId,
    onClose,
    canEdit,
    canViewAudit = false,
}: {
    teacherId: string | null;
    onClose: () => void;
    /** `teachers.update` - the drawer hides the forms without it. */
    canEdit: boolean;
    /** `teachers.audit_read` - the Activity tab is not even offered without it. */
    canViewAudit?: boolean;
}) {
    const s = useStaffProfile(teacherId);
    const [tab, setTab] = useState<ProfileTab>("Overview");

    const profile = s.profile;
    const offTheRoll = profile?.status === "Inactive";
    const editable = canEdit && !offTheRoll;
    const tabs: ProfileTab[] = canViewAudit ? [...BASE_TABS, "Activity"] : [...BASE_TABS];

    return (
        <Sheet open={teacherId !== null} onOpenChange={(open) => !open && onClose()} modal={false}>
            <SheetContent
                side="right"
                hideOverlay
                className="flex w-full flex-col border-l border-(--border-subtle) bg-linear-to-br from-(--background)/30 to-(--background)/10 p-0 shadow-[-20px_0_60px_-15px_rgba(0,0,0,0.3)] backdrop-blur-3xl sm:max-w-2xl"
            >
                <div className="flex-1 overflow-y-auto p-6">
                    <SheetHeader className="mb-6 text-left">
                        <div className="flex items-center gap-4">
                            <div className="bg-primary/20 text-primary flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl text-2xl font-bold">
                                {initials(profile?.name ?? "")}
                            </div>
                            <div>
                                <SheetTitle className="text-2xl font-bold">
                                    {profile ? shown(profile.name) : "Staff profile"}
                                </SheetTitle>
                                <SheetDescription className="text-muted-foreground">
                                    {profile
                                        ? `${profile.staffCode} · ${shown(profile.department)}`
                                        : "Loading…"}
                                </SheetDescription>
                            </div>
                        </div>
                    </SheetHeader>

                    {s.loading && <Spinner />}

                    {s.loadError !== null && (
                        <p style={{ color: "var(--danger, #b42318)" }}>
                            {errorMessage(s.loadError, "This profile could not be loaded.")}
                        </p>
                    )}

                    {profile && (
                        <>
                            {offTheRoll && (
                                <div className="mb-4 rounded-lg border border-(--border-subtle) bg-(--accent-surface) p-3 text-sm">
                                    This person is off the staff roll, so the profile is read-only.
                                    Reactivate them on the staff screen to edit it.
                                </div>
                            )}

                            <Tabs
                                tabs={[...tabs]}
                                active={tab}
                                onChange={(next) => setTab(next as ProfileTab)}
                            />

                            {s.error !== null && (
                                <p
                                    className="mb-3 text-sm"
                                    style={{ color: "var(--danger, #b42318)" }}
                                >
                                    {errorMessage(s.error, "That change was not saved.")}
                                </p>
                            )}

                            {tab === "Overview" && (
                                <Overview
                                    profile={profile}
                                    editable={editable}
                                    busy={s.busy === "employment"}
                                    onSave={s.saveEmployment}
                                    revealed={s.revealed}
                                    onReveal={s.showKyc}
                                />
                            )}
                            {tab === "Qualifications" && (
                                <QualificationsTab
                                    profile={profile}
                                    editable={editable}
                                    busy={s.busy === "qualification"}
                                    onAdd={s.addQualification}
                                    onRemove={s.removeQualification}
                                />
                            )}
                            {tab === "Experience" && (
                                <ExperienceTab
                                    profile={profile}
                                    editable={editable}
                                    busy={s.busy === "experience"}
                                    onAdd={s.addExperience}
                                    onRemove={s.removeExperience}
                                />
                            )}
                            {tab === "Certifications" && (
                                <CertificationsTab
                                    profile={profile}
                                    editable={editable}
                                    busy={s.busy === "certification"}
                                    onAdd={s.addCertification}
                                    onRemove={s.removeCertification}
                                />
                            )}
                            {tab === "Documents" && (
                                <DocumentsTab
                                    profile={profile}
                                    editable={editable}
                                    busy={s.busy}
                                    onUpload={s.uploadDocument}
                                    onVerify={s.verifyDocument}
                                    onRemove={s.removeDocument}
                                    onDownload={s.downloadDocument}
                                />
                            )}
                            {tab === "History" && <HistoryTab profile={profile} />}
                            {tab === "Activity" && canViewAudit && (
                                <ActivityTab teacherId={profile.id} />
                            )}
                        </>
                    )}
                </div>
            </SheetContent>
        </Sheet>
    );
}

/* ---------- Qualifications ---------- */

function QualificationsTab({
    profile,
    editable,
    busy,
    onAdd,
    onRemove,
}: {
    profile: StaffProfileDetail;
    editable: boolean;
    busy: boolean;
    onAdd: (input: QualificationInput) => Promise<boolean>;
    onRemove: (rowId: string) => Promise<boolean>;
}) {
    const [degree, setDegree] = useState("");
    const [institution, setInstitution] = useState("");
    const [year, setYear] = useState("");
    const [grade, setGrade] = useState("");

    async function add() {
        if (!degree.trim()) return;
        const saved = await onAdd({
            degree: degree.trim(),
            institution: institution.trim() || null,
            yearCompleted: year.trim() ? Number(year) : null,
            grade: grade.trim() || null,
        });
        if (saved) {
            setDegree("");
            setInstitution("");
            setYear("");
            setGrade("");
        }
    }

    return (
        <div className="flex flex-col gap-4">
            <Table
                columns={[
                    { key: "degree", header: "Degree", render: (r) => shown(r.degree) },
                    {
                        key: "institution",
                        header: "Institution",
                        render: (r) => shown(r.institution),
                    },
                    {
                        key: "year",
                        header: "Year",
                        // A missing year is a blank, not the year 0.
                        render: (r) => (r.yearCompleted ? String(r.yearCompleted) : "—"),
                    },
                    { key: "grade", header: "Grade", render: (r) => r.grade ?? "—" },
                    {
                        key: "actions",
                        header: "",
                        align: "right" as const,
                        render: (r) =>
                            editable ? (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    disabled={busy}
                                    onClick={() => onRemove(r.id)}
                                >
                                    Remove
                                </Button>
                            ) : null,
                    },
                ]}
                rows={profile.qualifications}
                rowKey={(r) => r.id}
                empty="No qualification recorded yet."
            />

            {editable && (
                <div className="glass-card flex flex-col gap-3 border border-(--border-subtle) p-5">
                    <div className="form-grid">
                        <div>
                            <Label>Degree</Label>
                            <Input
                                value={degree}
                                placeholder="B.Ed"
                                onChange={(event) => setDegree(event.target.value)}
                            />
                        </div>
                        <div>
                            <Label>Institution</Label>
                            <Input
                                value={institution}
                                placeholder="Delhi University"
                                onChange={(event) => setInstitution(event.target.value)}
                            />
                        </div>
                        <div>
                            <Label>Year completed</Label>
                            <Input
                                type="number"
                                min={1900}
                                max={2100}
                                value={year}
                                onChange={(event) => setYear(event.target.value)}
                            />
                        </div>
                        <div>
                            <Label>Grade</Label>
                            <Input
                                value={grade}
                                placeholder="First class"
                                onChange={(event) => setGrade(event.target.value)}
                            />
                        </div>
                    </div>
                    <div className="modal-actions">
                        <Button loading={busy} disabled={!degree.trim()} onClick={add}>
                            Add qualification
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ---------- Experience ---------- */

function ExperienceTab({
    profile,
    editable,
    busy,
    onAdd,
    onRemove,
}: {
    profile: StaffProfileDetail;
    editable: boolean;
    busy: boolean;
    onAdd: (input: ExperienceInput) => Promise<boolean>;
    onRemove: (rowId: string) => Promise<boolean>;
}) {
    const [employer, setEmployer] = useState("");
    const [role, setRole] = useState("");
    const [fromDate, setFromDate] = useState("");
    const [toDate, setToDate] = useState("");

    async function add() {
        if (!employer.trim() || !fromDate) return;
        const saved = await onAdd({
            employer: employer.trim(),
            designation: role.trim() || null,
            fromDate,
            toDate: toDate || null,
        });
        if (saved) {
            setEmployer("");
            setRole("");
            setFromDate("");
            setToDate("");
        }
    }

    return (
        <div className="flex flex-col gap-4">
            <Table
                columns={[
                    { key: "employer", header: "Employer", render: (r) => shown(r.employer) },
                    {
                        key: "designation",
                        header: "Designation",
                        render: (r) => shown(r.designation),
                    },
                    {
                        key: "period",
                        header: "Period",
                        // An open end date is "still there", not a missing value.
                        render: (r) => `${r.fromDate} → ${r.toDate ?? "present"}`,
                    },
                    { key: "note", header: "Note", render: (r) => r.note ?? "—" },
                    {
                        key: "actions",
                        header: "",
                        align: "right" as const,
                        render: (r) =>
                            editable ? (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    disabled={busy}
                                    onClick={() => onRemove(r.id)}
                                >
                                    Remove
                                </Button>
                            ) : null,
                    },
                ]}
                rows={profile.experiences}
                rowKey={(r) => r.id}
                empty="No earlier employment recorded."
            />

            {editable && (
                <div className="glass-card flex flex-col gap-3 border border-(--border-subtle) p-5">
                    <div className="form-grid">
                        <div>
                            <Label>Employer</Label>
                            <Input
                                value={employer}
                                placeholder="Delhi Public School"
                                onChange={(event) => setEmployer(event.target.value)}
                            />
                        </div>
                        <div>
                            <Label>Designation</Label>
                            <Input
                                value={role}
                                placeholder="PGT Physics"
                                onChange={(event) => setRole(event.target.value)}
                            />
                        </div>
                        <div>
                            <Label>From</Label>
                            <Input
                                type="date"
                                value={fromDate}
                                onChange={(event) => setFromDate(event.target.value)}
                            />
                        </div>
                        <div>
                            <Label>To</Label>
                            <Input
                                type="date"
                                value={toDate}
                                onChange={(event) => setToDate(event.target.value)}
                            />
                        </div>
                    </div>
                    <div className="modal-actions">
                        <Button
                            loading={busy}
                            disabled={!employer.trim() || !fromDate}
                            onClick={add}
                        >
                            Add experience
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ---------- Certifications ---------- */

function CertificationsTab({
    profile,
    editable,
    busy,
    onAdd,
    onRemove,
}: {
    profile: StaffProfileDetail;
    editable: boolean;
    busy: boolean;
    onAdd: (input: CertificationInput) => Promise<boolean>;
    onRemove: (rowId: string) => Promise<boolean>;
}) {
    const [name, setName] = useState("");
    const [issuer, setIssuer] = useState("");
    const [issuedOn, setIssuedOn] = useState("");
    const [validTill, setValidTill] = useState("");

    async function add() {
        if (!name.trim()) return;
        const saved = await onAdd({
            name: name.trim(),
            issuer: issuer.trim() || null,
            issuedOn: issuedOn || null,
            validTill: validTill || null,
        });
        if (saved) {
            setName("");
            setIssuer("");
            setIssuedOn("");
            setValidTill("");
        }
    }

    return (
        <div className="flex flex-col gap-4">
            <Table
                columns={[
                    { key: "name", header: "Certificate", render: (r) => shown(r.name) },
                    { key: "issuer", header: "Issued by", render: (r) => shown(r.issuer) },
                    { key: "issued", header: "Issued", render: (r) => r.issuedOn ?? "—" },
                    {
                        key: "valid",
                        header: "Valid till",
                        // An expiry is a date the principal can read, not a status
                        // somebody has to remember to change.
                        render: (r) => r.validTill ?? "No expiry",
                    },
                    {
                        key: "actions",
                        header: "",
                        align: "right" as const,
                        render: (r) =>
                            editable ? (
                                <Button
                                    variant="ghost"
                                    size="sm"
                                    disabled={busy}
                                    onClick={() => onRemove(r.id)}
                                >
                                    Remove
                                </Button>
                            ) : null,
                    },
                ]}
                rows={profile.certifications}
                rowKey={(r) => r.id}
                empty="No certificate recorded yet."
            />

            {editable && (
                <div className="glass-card flex flex-col gap-3 border border-(--border-subtle) p-5">
                    <div className="form-grid">
                        <div>
                            <Label>Certificate</Label>
                            <Input
                                value={name}
                                placeholder="First aid"
                                onChange={(event) => setName(event.target.value)}
                            />
                        </div>
                        <div>
                            <Label>Issued by</Label>
                            <Input
                                value={issuer}
                                placeholder="Red Cross"
                                onChange={(event) => setIssuer(event.target.value)}
                            />
                        </div>
                        <div>
                            <Label>Issued on</Label>
                            <Input
                                type="date"
                                value={issuedOn}
                                onChange={(event) => setIssuedOn(event.target.value)}
                            />
                        </div>
                        <div>
                            <Label>Valid till</Label>
                            <Input
                                type="date"
                                value={validTill}
                                onChange={(event) => setValidTill(event.target.value)}
                            />
                        </div>
                    </div>
                    <div className="modal-actions">
                        <Button loading={busy} disabled={!name.trim()} onClick={add}>
                            Add certificate
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ---------- History (append-only) ---------- */

function HistoryTab({ profile }: { profile: StaffProfileDetail }) {
    return (
        <div className="flex flex-col gap-3">
            <Table
                columns={[
                    { key: "event", header: "Event", render: (r) => r.event },
                    { key: "effective", header: "Effective", render: (r) => r.effectiveOn },
                    {
                        key: "change",
                        header: "Change",
                        // "Teacher → Senior Teacher" is the fact a salary or a
                        // seniority question is argued from, so the old value stays.
                        render: (r) =>
                            r.fromValue || r.toValue
                                ? `${shown(r.fromValue)} → ${shown(r.toValue)}`
                                : "—",
                    },
                    { key: "note", header: "Note", render: (r) => r.note ?? "—" },
                    {
                        key: "by",
                        header: "Recorded by",
                        render: (r) => shown(r.recordedBy),
                    },
                ]}
                rows={profile.history}
                rowKey={(r) => r.id}
                empty="Nothing has happened to this employment yet."
            />
            <p className="text-muted-foreground text-xs">
                History is a record, not a form: entries are added, never edited or deleted.
            </p>
        </div>
    );
}

/* ---------- Overview: the person and the post ---------- */

function Overview({
    profile,
    editable,
    busy,
    onSave,
    revealed,
    onReveal,
}: {
    profile: StaffProfileDetail;
    editable: boolean;
    busy: boolean;
    onSave: (input: EmploymentInput) => Promise<boolean>;
    /** True once the drawer asked for the unmasked Aadhaar / PAN / bank. */
    revealed: boolean;
    onReveal: () => void;
}) {
    const [editing, setEditing] = useState(false);
    const [designation, setDesignation] = useState(profile.designation ?? "");
    const [employmentType, setEmploymentType] = useState(profile.employmentType ?? "");
    const [probationEnd, setProbationEnd] = useState(profile.probationEnd ?? "");

    async function save() {
        const saved = await onSave({
            designation: designation.trim() || null,
            employmentType: employmentType || null,
            probationEnd: probationEnd || null,
        });
        if (saved) setEditing(false);
    }

    return (
        <div className="flex flex-col gap-4">
            <div className="grid grid-cols-3 gap-3">
                <div className="glass-card p-3 text-center">
                    <div className="text-muted-foreground mb-1 text-xs">Status</div>
                    <Badge tone={STATUS_TONE[profile.status]}>{profile.status}</Badge>
                </div>
                <div className="glass-card p-3 text-center">
                    <div className="text-muted-foreground mb-1 text-xs">Periods / week</div>
                    <div className="text-foreground text-lg font-bold">{profile.workload}</div>
                </div>
                <div className="glass-card p-3 text-center">
                    <div className="text-muted-foreground mb-1 text-xs">Utilisation</div>
                    <div className="text-foreground text-lg font-bold">
                        {/* No timetable yet means no percentage - not 0%. */}
                        {profile.capacity > 0 ? `${profile.utilisation}%` : "—"}
                    </div>
                </div>
            </div>

            <div className="glass-card grid grid-cols-2 gap-4 border border-(--border-subtle) p-5">
                <Detail label="Designation" value={shown(profile.designation)} />
                <Detail label="Employment type" value={shown(profile.employmentType)} />
                <Detail label="Department" value={shown(profile.department)} />
                <Detail label="Joined" value={day(profile.joiningDate)} />
                <Detail label="Probation ends" value={day(profile.probationEnd)} />
                <Detail label="Reports to" value={shown(profile.reportsTo)} />
                <Detail label="Qualification" value={shown(profile.qualification)} />
                <Detail label="Experience" value={`${profile.experienceYears} yr`} />
                <Detail label="Subjects" value={profile.subjects.map(shown).join(", ") || "—"} />
                <Detail label="Classes" value={profile.classes.join(", ") || "—"} />
                <Detail label="Phone" value={profile.phone || "—"} />
                <Detail label="Email" value={profile.email || "—"} />
            </div>

            {/* Aadhaar / PAN / bank - masked until somebody asks, and the ask is
                written to the audit trail (`profile.service.kyc_read`). */}
            <div className="glass-card border border-(--border-subtle) p-5">
                <div className="mb-3 flex items-center justify-between">
                    <div className="text-foreground text-sm font-semibold">Identity And Bank</div>
                    {profile.kyc.canReveal && !revealed && (
                        <Button variant="outline" size="sm" onClick={onReveal}>
                            Show Full
                        </Button>
                    )}
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <Detail label="Aadhaar Number" value={profile.kyc.aadhaarNo ?? "—"} />
                    <Detail label="PAN Number" value={profile.kyc.panNo ?? "—"} />
                    <Detail label="Bank Name" value={shown(profile.kyc.bankName)} />
                    <Detail label="Bank Account" value={profile.kyc.bankAccountNo ?? "—"} />
                    <Detail label="IFSC" value={profile.kyc.ifsc ?? "—"} />
                </div>
                <p className="text-muted-foreground mt-3 text-xs">
                    {profile.kyc.masked
                        ? profile.kyc.canReveal
                            ? "Only the last characters are shown. Revealing the full numbers is written to the staff activity trail."
                            : "Only the last characters are shown. Your role may not view the full numbers."
                        : "Shown in full for this open profile. The reveal is recorded in the staff activity trail."}
                </p>
            </div>

            {editable && !editing && (
                <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
                    Edit post
                </Button>
            )}

            {editable && editing && (
                <div className="glass-card flex flex-col gap-3 border border-(--border-subtle) p-5">
                    <div className="form-grid">
                        <div>
                            <Label>Designation</Label>
                            <Input
                                value={designation}
                                placeholder="Senior Teacher"
                                onChange={(event) => setDesignation(event.target.value)}
                            />
                        </div>
                        <div>
                            <Label>Employment type</Label>
                            <Select
                                value={employmentType}
                                onChange={(event) => setEmploymentType(event.target.value)}
                            >
                                <option value="">Not recorded</option>
                                {EMPLOYMENT_TYPES.map((type) => (
                                    <option key={type} value={type}>
                                        {type}
                                    </option>
                                ))}
                            </Select>
                        </div>
                        <div>
                            <Label>Probation ends</Label>
                            <Input
                                type="date"
                                value={probationEnd}
                                onChange={(event) => setProbationEnd(event.target.value)}
                            />
                        </div>
                    </div>
                    <p className="text-muted-foreground text-xs">
                        A designation change is appended to the history, so the previous title stays
                        on the record.
                    </p>
                    <div className="modal-actions">
                        <Button variant="ghost" onClick={() => setEditing(false)}>
                            Cancel
                        </Button>
                        <Button loading={busy} onClick={save}>
                            Save post
                        </Button>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ---------- Documents ---------- */

/**
 * The document types the API accepts (`labels.DOC_TYPES` on the server).
 *
 * A copy on purpose, like `EMPLOYMENT_TYPES`: the drawer has to offer the list
 * before it can read a row. The server refuses anything outside its own
 * vocabulary, so a stale copy fails loudly (`400`) instead of silently.
 */
const DOCUMENTS = [
    { value: "aadhaar", label: "Aadhaar Card" },
    { value: "pan", label: "PAN Card" },
    { value: "bank_proof", label: "Bank Proof" },
    { value: "degree", label: "Degree" },
    { value: "certificate", label: "Certificate" },
    { value: "experience_letter", label: "Experience Letter" },
    { value: "medical", label: "Medical Record" },
    { value: "contract", label: "Contract" },
    { value: "photo", label: "Photograph" },
    { value: "other", label: "Other" },
];

/** `212 KB` / `1.4 MB` - a size a person can judge, or "—" when unknown. */
function sizeLabel(bytes: number): string {
    if (!bytes) return "—";
    const kb = bytes / 1024;
    return kb >= 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${Math.round(kb)} KB`;
}

function DocumentsTab({
    profile,
    editable,
    busy,
    onUpload,
    onVerify,
    onRemove,
    onDownload,
}: {
    profile: StaffProfileDetail;
    editable: boolean;
    busy: string | null;
    onUpload: (input: { file: File; docType: string; title?: string }) => Promise<boolean>;
    onVerify: (rowId: string, verified?: boolean) => Promise<boolean>;
    onRemove: (rowId: string) => Promise<boolean>;
    onDownload: (rowId: string, fileName: string) => Promise<boolean>;
}) {
    const [docType, setDocType] = useState("aadhaar");
    const [title, setTitle] = useState("");
    const [file, setFile] = useState<File | null>(null);
    // A file input cannot be cleared from React, so a saved upload remounts it.
    const [pick, setPick] = useState(0);

    async function upload() {
        if (!file) return;
        const saved = await onUpload({ file, docType, title });
        if (saved) {
            setFile(null);
            setTitle("");
            setPick((count) => count + 1);
        }
    }

    const columns = [
        {
            key: "docTypeLabel",
            header: "Type",
            render: (row: StaffDocumentRow) => (
                <div style={{ lineHeight: 1.2 }}>
                    <div>{row.docTypeLabel || row.docType}</div>
                    {row.title && (
                        <div style={{ color: "var(--muted)", fontSize: "0.74rem" }}>
                            {row.title}
                        </div>
                    )}
                </div>
            ),
        },
        { key: "fileName", header: "File" },
        {
            key: "sizeBytes",
            header: "Size",
            render: (row: StaffDocumentRow) => sizeLabel(row.sizeBytes),
        },
        {
            key: "verifiedOn",
            header: "Verified",
            render: (row: StaffDocumentRow) =>
                row.verifiedOn ? (
                    <Badge tone="green">{row.verifiedOn}</Badge>
                ) : (
                    <Badge tone="amber">Pending</Badge>
                ),
        },
        {
            key: "actions",
            header: "Actions",
            render: (row: StaffDocumentRow) => (
                <div className="flex gap-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        loading={busy === `download-${row.id}`}
                        onClick={() => onDownload(row.id, row.fileName)}
                    >
                        Download
                    </Button>
                    {editable && (
                        <>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => onVerify(row.id, !row.verifiedOn)}
                            >
                                {row.verifiedOn ? "Un-Verify" : "Verify"}
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => onRemove(row.id)}>
                                Delete
                            </Button>
                        </>
                    )}
                </div>
            ),
        },
    ];

    return (
        <div className="flex flex-col gap-4">
            {editable && (
                <div className="glass-card flex flex-col gap-3 border border-(--border-subtle) p-5">
                    <div className="form-grid">
                        <div>
                            <Label>Document Type</Label>
                            <Select
                                value={docType}
                                onChange={(event) => setDocType(event.target.value)}
                            >
                                {DOCUMENTS.map((type) => (
                                    <option key={type.value} value={type.value}>
                                        {type.label}
                                    </option>
                                ))}
                            </Select>
                        </div>
                        <div>
                            <Label>Title</Label>
                            <Input
                                value={title}
                                placeholder="Front Side"
                                onChange={(event) => setTitle(event.target.value)}
                            />
                        </div>
                        <div>
                            <Label>File</Label>
                            <Input
                                key={pick}
                                type="file"
                                accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
                                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                            />
                        </div>
                    </div>
                    <p className="text-muted-foreground text-xs">
                        A PDF, Word document or image. The file is kept on the school server in this
                        person&apos;s own folder; only this row is listed.
                    </p>
                    <div className="modal-actions">
                        <Button loading={busy === "document"} disabled={!file} onClick={upload}>
                            Upload Document
                        </Button>
                    </div>
                </div>
            )}

            <Table
                columns={columns}
                rows={profile.documents}
                rowKey={(row) => row.id}
                empty="No Documents Filed Yet."
            />
        </div>
    );
}

/* ---------- Activity (the audit trail) ---------- */

/**
 * Who changed what on this profile, newest first.
 *
 * Chronology, not alphabetical order: the one list on this screen that answers
 * "what happened last" rather than "what is in it". Readable only with
 * `teachers.audit_read`, and the tab is not offered without it.
 */
function ActivityTab({ teacherId }: { teacherId: string }) {
    const query = useApiQuery(["staff", "audit", teacherId], () =>
        getStaffAudit({ employeeId: teacherId, limit: 100 }),
    );

    const columns = [
        {
            key: "createdAt",
            header: "When",
            render: (row: StaffAuditEntry) => row.createdAt?.replace("T", " ").slice(0, 16) ?? "—",
        },
        { key: "section", header: "Section" },
        { key: "action", header: "Action" },
        { key: "summary", header: "What Changed" },
        {
            key: "changedBy",
            header: "By",
            render: (row: StaffAuditEntry) => row.changedBy ?? "—",
        },
    ];

    if (query.isPending) return <Spinner />;
    if (query.error) {
        return (
            <p className="text-sm" style={{ color: "var(--danger, #b42318)" }}>
                {errorMessage(query.error, "The activity trail could not be loaded.")}
            </p>
        );
    }

    return (
        <Table
            columns={columns}
            rows={query.data ?? []}
            rowKey={(row) => row.id}
            empty="No Activity Recorded Yet."
        />
    );
}
