"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { formatDate } from "@/components/ui";
import { type DeadlineSourceTable, updateDeadline } from "@/lib/api";

const EDITABLE_TABLES: DeadlineSourceTable[] = [
  "scout_opportunities",
  "grants",
  "competitions",
];

interface DeadlineEditorProps {
  sourceTable: DeadlineSourceTable;
  sourceId: number;
  deadlineAt: string | null;
  compact?: boolean;
}

export function DeadlineEditor({
  sourceTable,
  sourceId,
  deadlineAt,
  compact = false,
}: DeadlineEditorProps) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(deadlineAt?.slice(0, 10) ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!editing) {
      setValue(deadlineAt?.slice(0, 10) ?? "");
    }
  }, [deadlineAt, editing]);

  async function handleSave(nextValue: string | null) {
    setBusy(true);
    setError(null);
    try {
      await updateDeadline(sourceTable, sourceId, {
        deadline_at: nextValue,
      });
      setEditing(false);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save deadline");
    } finally {
      setBusy(false);
    }
  }

  const Wrapper = compact ? "span" : "div";

  if (!editing) {
    return (
      <Wrapper className={compact ? "inline-flex items-center gap-1" : "flex items-center gap-2"}>
        <span className="text-zinc-300">
          {deadlineAt ? formatDate(deadlineAt) : "—"}
        </span>
        <button
          type="button"
          onClick={() => {
            setValue(deadlineAt?.slice(0, 10) ?? "");
            setEditing(true);
            setError(null);
          }}
          className="text-xs text-sky-400 hover:underline"
        >
          {deadlineAt ? "Edit" : "Add"}
        </button>
        {error && <span className="text-xs text-red-400">{error}</span>}
      </Wrapper>
    );
  }

  return (
    <Wrapper className={compact ? "inline-flex flex-wrap items-center gap-2" : "flex flex-wrap items-center gap-2"}>
      <input
        type="date"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={busy}
        className="rounded border border-zinc-700 bg-zinc-950 px-2 py-1 text-sm text-white focus:border-sky-500 focus:outline-none"
      />
      <button
        type="button"
        disabled={busy || !value}
        onClick={() => handleSave(value)}
        className="rounded bg-sky-600 px-2 py-1 text-xs font-medium text-white hover:bg-sky-500 disabled:opacity-50"
      >
        {busy ? "…" : "Save"}
      </button>
      {deadlineAt && (
        <button
          type="button"
          disabled={busy}
          onClick={() => handleSave(null)}
          className="rounded border border-zinc-700 px-2 py-1 text-xs text-zinc-400 hover:border-zinc-500"
        >
          Clear
        </button>
      )}
      <button
        type="button"
        disabled={busy}
        onClick={() => {
          setEditing(false);
          setError(null);
        }}
        className="text-xs text-zinc-500 hover:text-zinc-300"
      >
        Cancel
      </button>
      {error && <span className="text-xs text-red-400">{error}</span>}
    </Wrapper>
  );
}

interface BriefingDeadlineCellProps {
  dueAt: string | null;
  sourceId: number | null;
  sourceTable: string | null;
}

export function BriefingDeadlineCell({
  dueAt,
  sourceId,
  sourceTable,
}: BriefingDeadlineCellProps) {
  if (
    sourceId != null &&
    sourceTable &&
    EDITABLE_TABLES.includes(sourceTable as DeadlineSourceTable)
  ) {
    return (
      <DeadlineEditor
        sourceTable={sourceTable as DeadlineSourceTable}
        sourceId={sourceId}
        deadlineAt={dueAt}
        compact
      />
    );
  }
  return <span>{dueAt ? formatDate(dueAt) : "—"}</span>;
}
