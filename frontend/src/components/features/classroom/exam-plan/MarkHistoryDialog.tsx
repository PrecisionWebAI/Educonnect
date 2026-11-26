"use client";

import { Button, Modal, Spinner } from "@/components/ui";
import { errorMessage } from "@/lib/api/client";
import { useApiQuery } from "@/lib/api/use-api-query";
import { changeText } from "@/lib/exams/marksSheet";
import { getMarkHistory } from "@/services";

// The corrections made to a paper's published marks: who changed which mark, when, from
// what to what, and why. Only the people who run the paper can open it - a family never
// sees this trail, only the message that tells them their child's mark changed.

export default function MarkHistoryDialog({
    paperId,
    open,
    onClose,
}: {
    paperId: string;
    open: boolean;
    onClose: () => void;
}) {
    return (
        <Modal open={open} title="Corrections to published marks" onClose={onClose}>
            {open && <Body paperId={paperId} onClose={onClose} />}
        </Modal>
    );
}

function Body({ paperId, onClose }: { paperId: string; onClose: () => void }) {
    const query = useApiQuery(["exams", "marks-history", paperId], () => getMarkHistory(paperId));
    if (query.isPending) return <Spinner />;
    if (query.isError) {
        return (
            <p className="text-sm text-red-500" role="alert">
                {errorMessage(query.error, "Could not read the corrections.")}
            </p>
        );
    }
    const items = query.data ?? [];
    return (
        <div className="space-y-3 text-sm">
            {items.length === 0 ? (
                <p className="text-muted-foreground">No published mark has been corrected.</p>
            ) : (
                <ul className="space-y-2">
                    {items.map((item) => (
                        <li
                            key={`${item.studentId}-${item.changedAt}`}
                            className="glass-tile rounded-xl p-3"
                        >
                            <p className="font-medium">
                                {item.studentName} · {changeText(item)}
                            </p>
                            <p className="text-muted-foreground text-xs">
                                {item.changedBy ?? "Someone"} ·{" "}
                                {new Date(item.changedAt).toLocaleString()}
                                {item.reason ? ` · ${item.reason}` : ""}
                            </p>
                        </li>
                    ))}
                </ul>
            )}
            <div className="modal-actions">
                <Button variant="ghost" onClick={onClose}>
                    Close
                </Button>
            </div>
        </div>
    );
}
