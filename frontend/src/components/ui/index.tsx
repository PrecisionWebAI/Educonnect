"use client";

import {
    type ReactNode,
    type InputHTMLAttributes,
    type SelectHTMLAttributes,
    type TextareaHTMLAttributes,
    type ButtonHTMLAttributes,
} from "react";
import { Loader2 } from "lucide-react";
import { Button as ShadcnButton } from "./button";
import { Badge as ShadcnBadge } from "./badge";
import {
    Card as ShadcnCard,
    CardHeader as ShadcnCardHeader,
    CardTitle as ShadcnCardTitle,
    CardContent as ShadcnCardContent,
} from "./card";
import { Input as ShadcnInput } from "./input";
import { Textarea as ShadcnTextarea } from "./textarea";
import { Label as ShadcnLabel } from "./label";
import {
    Table as ShadcnTable,
    TableHeader,
    TableRow,
    TableHead,
    TableBody,
    TableCell,
} from "./table";
import { Tabs as ShadcnTabs, TabsList, TabsTrigger } from "./tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "./dialog";
import {
    Pagination as ShadcnPagination,
    PaginationContent,
    PaginationItem,
    PaginationLink,
    PaginationPrevious,
    PaginationNext,
    PaginationEllipsis,
} from "./pagination";

// ============================================================
// EduConnect UI kit — Adapter using Shadcn UI
// ============================================================

/* ---------- Button ---------- */

export type ButtonVariant = "primary" | "outline" | "ghost" | "danger" | "success";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: ButtonVariant;
    size?: "sm" | "md";
    icon?: string;
    loading?: boolean;
}

export function Button({
    variant = "primary",
    size = "md",
    icon,
    loading,
    children,
    className = "",
    disabled,
    ...rest
}: ButtonProps) {
    const variantMap: Record<
        ButtonVariant,
        "default" | "outline" | "ghost" | "destructive" | "secondary"
    > = {
        primary: "default",
        outline: "outline",
        ghost: "ghost",
        danger: "destructive",
        success: "secondary", // fallback mapping
    };

    const sizeMap: Record<"sm" | "md", "default" | "sm"> = {
        sm: "sm",
        md: "default",
    };

    return (
        <ShadcnButton
            variant={variantMap[variant]}
            size={sizeMap[size]}
            className={className}
            disabled={disabled || loading}
            {...rest}
        >
            {loading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : icon ? (
                <span className="mr-2">{icon}</span>
            ) : null}
            {children}
        </ShadcnButton>
    );
}

/* ---------- Badge ---------- */
export type BadgeTone = "accent" | "green" | "red" | "amber" | "muted" | "teal" | "violet";

export function Badge({
    tone = "accent",
    className = "",
    children,
}: {
    tone?: BadgeTone;
    className?: string;
    children: ReactNode;
}) {
    // Custom tones: soft-tinted chips; dark mode uses translucent tints + hairline rings
    // (same language as the attendance status chips).
    const toneMap: Record<BadgeTone, string> = {
        accent: "bg-violet-100 text-violet-800 dark:bg-violet-500/12 dark:text-violet-200 dark:ring-1 dark:ring-inset dark:ring-violet-300/25",
        green: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/12 dark:text-emerald-300 dark:ring-1 dark:ring-inset dark:ring-emerald-400/25",
        red: "bg-red-100 text-red-800 dark:bg-red-500/12 dark:text-red-300 dark:ring-1 dark:ring-inset dark:ring-red-400/25",
        amber: "bg-amber-100 text-amber-800 dark:bg-amber-500/12 dark:text-amber-300 dark:ring-1 dark:ring-inset dark:ring-amber-400/25",
        muted: "bg-slate-100 text-slate-800 dark:bg-white/6 dark:text-slate-300 dark:ring-1 dark:ring-inset dark:ring-white/10",
        teal: "bg-teal-100 text-teal-800 dark:bg-teal-500/12 dark:text-teal-300 dark:ring-1 dark:ring-inset dark:ring-teal-400/25",
        violet: "bg-violet-100 text-violet-800 dark:bg-violet-500/12 dark:text-violet-300 dark:ring-1 dark:ring-inset dark:ring-violet-400/25",
    };

    return (
        <ShadcnBadge
            variant="secondary"
            className={`${toneMap[tone]} hover:bg-opacity-80 border-none ${className}`}
        >
            {children}
        </ShadcnBadge>
    );
}

/* ---------- Card ---------- */
export function Card({
    title,
    action,
    children,
    className = "",
}: {
    title?: string;
    action?: ReactNode;
    children: ReactNode;
    className?: string;
}) {
    return (
        <ShadcnCard className={className}>
            {title !== undefined && (
                <ShadcnCardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <ShadcnCardTitle className="text-md font-medium">{title}</ShadcnCardTitle>
                    {action && <div>{action}</div>}
                </ShadcnCardHeader>
            )}
            <ShadcnCardContent>{children}</ShadcnCardContent>
        </ShadcnCard>
    );
}

/* ---------- StatCard ---------- */
export function StatCard({
    icon,
    label,
    value,
    delta,
    hint,
}: {
    icon?: ReactNode;
    label: string;
    value: string;
    delta: number;
    hint?: string;
}) {
    const up = delta >= 0;
    return (
        <ShadcnCard>
            <ShadcnCardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <ShadcnCardTitle className="text-sm font-medium">{label}</ShadcnCardTitle>
                {icon && <span className="text-muted-foreground">{icon}</span>}
            </ShadcnCardHeader>
            <ShadcnCardContent>
                <div className="text-2xl font-bold">{value}</div>
                <div className="mt-1 flex items-center space-x-2">
                    <Badge tone={up ? "green" : "red"}>
                        {up ? "▲" : "▼"} {Math.abs(delta).toFixed(1)}%
                    </Badge>
                    {hint && <p className="text-muted-foreground text-xs">{hint}</p>}
                </div>
            </ShadcnCardContent>
        </ShadcnCard>
    );
}

/* ---------- Inputs ---------- */
interface FieldProps {
    label?: string;
    hint?: string;
    error?: string;
}

export function Input({
    label,
    hint,
    error,
    id,
    ...rest
}: FieldProps & InputHTMLAttributes<HTMLInputElement>) {
    return (
        <div className="space-y-2">
            {label && <ShadcnLabel htmlFor={id}>{label}</ShadcnLabel>}
            <ShadcnInput
                id={id}
                className={error ? "border-red-500 focus-visible:ring-red-500" : ""}
                {...rest}
            />
            {error ? (
                <p className="text-[0.8rem] font-medium text-red-500">{error}</p>
            ) : hint ? (
                <p className="text-muted-foreground text-[0.8rem]">{hint}</p>
            ) : null}
        </div>
    );
}

export function Select({
    label,
    hint,
    id,
    children,
    ...rest
}: FieldProps & SelectHTMLAttributes<HTMLSelectElement>) {
    return (
        <div className="space-y-2">
            {label && <ShadcnLabel htmlFor={id}>{label}</ShadcnLabel>}
            <select
                id={id}
                className="border-input focus-visible:ring-ring flex h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:ring-1 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
                {...rest}
            >
                {children}
            </select>
            {hint && <p className="text-muted-foreground text-[0.8rem]">{hint}</p>}
        </div>
    );
}

export function Textarea({
    label,
    hint,
    id,
    ...rest
}: FieldProps & TextareaHTMLAttributes<HTMLTextAreaElement>) {
    return (
        <div className="space-y-2">
            {label && <ShadcnLabel htmlFor={id}>{label}</ShadcnLabel>}
            <ShadcnTextarea id={id} {...rest} />
            {hint && <p className="text-muted-foreground text-[0.8rem]">{hint}</p>}
        </div>
    );
}

/* ---------- PageHeader ---------- */
export function PageHeader({
    title,
    subtitle,
    actions,
}: {
    title: string;
    subtitle?: string;
    actions?: ReactNode;
}) {
    return (
        <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div>
                <div className="flex items-center gap-2.5">
                    <span
                        aria-hidden="true"
                        className="h-7 w-1.5 shrink-0 rounded-full"
                        style={{
                            background: "var(--module-accent, var(--primary))",
                            boxShadow: "0 4px 14px -4px var(--module-accent, var(--primary))",
                        }}
                    />
                    <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
                </div>
                {subtitle && <p className="text-muted-foreground mt-1.5">{subtitle}</p>}
            </div>
            {actions && <div className="flex items-center gap-2">{actions}</div>}
        </div>
    );
}

/* ---------- Table ---------- */
export interface Column<T> {
    key: string;
    header: string;
    render?: (row: T) => ReactNode;
    align?: "left" | "right";
}

export function Table<T>({
    columns,
    rows,
    rowKey,
    empty,
}: {
    columns: Column<T>[];
    rows: T[];
    rowKey: (row: T) => React.Key;
    empty?: string;
}) {
    if (rows.length === 0) {
        return <EmptyState title={empty ?? "No records yet."} icon="🗂️" />;
    }
    return (
        <div className="rounded-md border">
            <ShadcnTable>
                <TableHeader>
                    <TableRow>
                        {columns.map((c) => (
                            <TableHead
                                key={c.key}
                                className={c.align === "right" ? "text-right" : ""}
                            >
                                {c.header}
                            </TableHead>
                        ))}
                    </TableRow>
                </TableHeader>
                <TableBody>
                    {rows.map((r) => (
                        <TableRow key={rowKey(r)}>
                            {columns.map((c) => (
                                <TableCell
                                    key={c.key}
                                    className={c.align === "right" ? "text-right" : ""}
                                >
                                    {c.render
                                        ? c.render(r)
                                        : String((r as Record<string, unknown>)[c.key] ?? "")}
                                </TableCell>
                            ))}
                        </TableRow>
                    ))}
                </TableBody>
            </ShadcnTable>
        </div>
    );
}

/* ---------- Tabs ---------- */
export function Tabs({
    tabs,
    active,
    onChange,
}: {
    tabs: string[];
    active: string;
    onChange: (tab: string) => void;
}) {
    return (
        <ShadcnTabs value={active} onValueChange={onChange} className="mb-6 w-full">
            <TabsList>
                {tabs.map((t) => (
                    <TabsTrigger key={t} value={t}>
                        {t}
                    </TabsTrigger>
                ))}
            </TabsList>
        </ShadcnTabs>
    );
}

/* ---------- Modal ---------- */
export function Modal({
    open,
    title,
    onClose,
    children,
}: {
    open: boolean;
    title: string;
    onClose: () => void;
    children: ReactNode;
}) {
    return (
        <Dialog open={open} onOpenChange={(val) => !val && onClose()}>
            <DialogContent className="sm:max-w-106.25">
                <DialogHeader>
                    <DialogTitle>{title}</DialogTitle>
                </DialogHeader>
                <div className="py-4">{children}</div>
            </DialogContent>
        </Dialog>
    );
}

/* ---------- Spinner ---------- */
export function Spinner() {
    return (
        <div className="flex h-40 w-full items-center justify-center" aria-label="Loading">
            <Loader2 className="text-muted-foreground h-8 w-8 animate-spin" />
        </div>
    );
}

/* ---------- Empty state ---------- */
export function EmptyState({
    icon = "🗂️",
    title,
    body,
}: {
    icon?: string;
    title: string;
    body?: string;
}) {
    return (
        <div className="animate-in fade-in-50 flex flex-col items-center justify-center rounded-md border border-dashed p-8 text-center">
            <div className="bg-muted mx-auto flex h-12 w-12 items-center justify-center rounded-full text-2xl">
                {icon}
            </div>
            <h3 className="mt-4 text-lg font-semibold">{title}</h3>
            {body && <p className="text-muted-foreground mt-2 mb-4 text-sm">{body}</p>}
        </div>
    );
}

/* ---------- Pagination ---------- */
export interface PaginationProps {
    currentPage: number;
    totalItems: number;
    pageSize: number;
    onPageChange: (page: number) => void;
}

export function Pagination({ currentPage, totalItems, pageSize, onPageChange }: PaginationProps) {
    if (totalItems <= 0) return null;
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));

    const start = Math.min((currentPage - 1) * pageSize + 1, totalItems);
    const end = Math.min(currentPage * pageSize, totalItems);

    const pages: (number | string)[] = [];
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
            pages.push(i);
        } else if (pages[pages.length - 1] !== "...") {
            pages.push("...");
        }
    }

    return (
        <div className="flex items-center justify-between py-4">
            <div className="text-muted-foreground text-sm">
                Showing <span className="font-medium">{start}</span> to{" "}
                <span className="font-medium">{end}</span> of{" "}
                <span className="font-medium">{totalItems}</span> entries
            </div>
            <ShadcnPagination className="mx-0 w-auto">
                <PaginationContent>
                    <PaginationItem>
                        <PaginationPrevious
                            href="#"
                            onClick={(e) => {
                                e.preventDefault();
                                if (currentPage > 1) onPageChange(currentPage - 1);
                            }}
                            className={currentPage <= 1 ? "pointer-events-none opacity-50" : ""}
                        />
                    </PaginationItem>

                    {pages.map((p, idx) => (
                        <PaginationItem key={idx}>
                            {typeof p === "number" ? (
                                <PaginationLink
                                    href="#"
                                    isActive={p === currentPage}
                                    onClick={(e) => {
                                        e.preventDefault();
                                        onPageChange(p);
                                    }}
                                >
                                    {p}
                                </PaginationLink>
                            ) : (
                                <PaginationEllipsis />
                            )}
                        </PaginationItem>
                    ))}

                    <PaginationItem>
                        <PaginationNext
                            href="#"
                            onClick={(e) => {
                                e.preventDefault();
                                if (currentPage < totalPages) onPageChange(currentPage + 1);
                            }}
                            className={
                                currentPage >= totalPages ? "pointer-events-none opacity-50" : ""
                            }
                        />
                    </PaginationItem>
                </PaginationContent>
            </ShadcnPagination>
        </div>
    );
}

// Ensure Shadcn UI components are also directly available
export * from "./button";
export * from "./card";
export * from "./badge";
export * from "./input";
export * from "./textarea";
export * from "./label";
export * from "./table";
export * from "./tabs";
export * from "./dialog";
export * from "./pagination";
export * from "./skeleton";
export * from "./sidebar";
