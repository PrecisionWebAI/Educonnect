"use client";

import * as React from "react";
import { CalendarIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Label } from "@/components/ui/label";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover";
import { cn } from "cn";

/* ============================================================
   DatePicker — themed calendar picker (Popover + Calendar).
   Works with "yyyy-MM-dd" strings so it is a drop-in match
   for the native <input type="date"> values used app-wide.
   ============================================================ */

function toISODate(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, "0");
    const d = String(date.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
}

function parseISODate(value: string): Date | undefined {
    if (!value) return undefined;
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? undefined : date;
}

function formatDisplayDate(date: Date): string {
    return date.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
    });
}

export interface DatePickerProps {
    /** Selected date as "yyyy-MM-dd" (same format as <input type="date">). */
    value?: string;
    onChange?: (value: string) => void;
    label?: string;
    placeholder?: string;
    disabled?: boolean;
    id?: string;
    className?: string;
}

export function DatePicker({
    value,
    onChange,
    label,
    placeholder = "Pick a date",
    disabled = false,
    id,
    className,
}: DatePickerProps) {
    const [open, setOpen] = React.useState(false);
    const selected = parseISODate(value ?? "");

    return (
        <div className={cn("w-full", className)}>
            {label && <Label htmlFor={id}>{label}</Label>}
            <Popover open={open} onOpenChange={setOpen}>
                <PopoverTrigger
                    render={
                        <Button
                            id={id}
                            type="button"
                            variant="outline"
                            disabled={disabled}
                            aria-label={label ?? "Select date"}
                            className={cn(
                                "border-input dark:bg-input/30 dark:hover:bg-input/50 w-full justify-between px-2.5 font-normal",
                                !value && "text-muted-foreground",
                            )}
                        >
                            {selected ? formatDisplayDate(selected) : placeholder}
                            <CalendarIcon className="text-muted-foreground size-4" />
                        </Button>
                    }
                />
                <PopoverContent align="start" className="w-auto p-0">
                    <Calendar
                        mode="single"
                        selected={selected}
                        defaultMonth={selected}
                        onSelect={(date) => {
                            onChange?.(date ? toISODate(date) : "");
                            setOpen(false);
                        }}
                    />
                </PopoverContent>
            </Popover>
        </div>
    );
}
