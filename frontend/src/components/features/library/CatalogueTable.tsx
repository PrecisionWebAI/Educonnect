"use client";
import { Table, Badge } from "@/components/ui";
import type { LibraryBook } from "@/types";

export default function CatalogueTable({ rows }: { rows: LibraryBook[] }) {
    const columns = [
        {
            key: "isbn",
            header: "ISBN",
            render: (r: LibraryBook) => (
                <span style={{ color: "var(--muted)", fontSize: "0.8rem" }}>{r.isbn}</span>
            ),
        },
        { key: "title", header: "Title" },
        { key: "author", header: "Author" },
        {
            key: "category",
            header: "Category",
            render: (r: LibraryBook) => <Badge tone="accent">{r.category}</Badge>,
        },
        { key: "copies", header: "Copies" },
        {
            key: "available",
            header: "Available",
            render: (r: LibraryBook) => (
                <b style={{ color: r.available > 0 ? "var(--text)" : "#fda4af" }}>{r.available}</b>
            ),
        },
    ];
    return (
        <Table
            columns={columns}
            rows={rows}
            rowKey={(r) => r.id}
            empty="No books match the search."
        />
    );
}
