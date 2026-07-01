"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { ApplicationDraftCard } from "@/components/ApplicationDraftCard";
import { ExternalLink, formatDate } from "@/components/ui";
import {
  type BriefingItem,
  fetchScoutPicker,
  type ScoutOpportunity,
  upsertAssistantTrack,
} from "@/lib/api";

type DraftFilter = "tracked" | "has_draft";

function formatCategory(category: string) {
  return category.replace(/_/g, " ");
}

export function ApplicationDraftSection({ items }: { items: BriefingItem[] }) {
  const router = useRouter();
  const [filter, setFilter] = useState<DraftFilter>("tracked");
  const [pickerOpen, setPickerOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [pickerRows, setPickerRows] = useState<ScoutOpportunity[]>([]);
  const [pickerLoading, setPickerLoading] = useState(false);
  const [pickerError, setPickerError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const counts = useMemo(
    () => ({
      tracked: items.filter((item) => item.tracked_application).length,
      has_draft: items.filter((item) => item.has_draft).length,
    }),
    [items]
  );

  const filtered = useMemo(() => {
    if (filter === "has_draft") {
      return items.filter((item) => item.has_draft);
    }
    return items;
  }, [items, filter]);

  async function openPicker() {
    setPickerOpen(true);
    setPickerLoading(true);
    setPickerError(null);
    try {
      setPickerRows(await fetchScoutPicker());
    } catch (err) {
      setPickerError(err instanceof Error ? err.message : "Failed to load opportunities");
    } finally {
      setPickerLoading(false);
    }
  }

  async function handleTrack(sourceId: number) {
    setBusyId(sourceId);
    setPickerError(null);
    try {
      await upsertAssistantTrack(sourceId, { track_application: true });
      setPickerOpen(false);
      setQuery("");
      router.refresh();
    } catch (err) {
      setPickerError(err instanceof Error ? err.message : "Failed to track");
    } finally {
      setBusyId(null);
    }
  }

  const pickerMatches = pickerRows.filter((row) => {
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return (
      row.name.toLowerCase().includes(q) ||
      row.category.toLowerCase().includes(q) ||
      (row.rank_reason ?? "").toLowerCase().includes(q)
    );
  });

  if (items.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-zinc-700 p-8 text-center">
        <p className="text-zinc-400">No applications tracked yet.</p>
        <p className="mt-2 text-sm text-zinc-500">
          Track opportunities you&apos;re actively applying to, or save a draft from Scout.
        </p>
        <button
          type="button"
          onClick={openPicker}
          className="mt-4 rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-500"
        >
          + Add application
        </button>
        {pickerOpen && (
          <PickerPanel
            query={query}
            setQuery={setQuery}
            rows={pickerMatches}
            loading={pickerLoading}
            error={pickerError}
            busyId={busyId}
            onTrack={handleTrack}
            onClose={() => setPickerOpen(false)}
          />
        )}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {(
          [
            { id: "tracked" as const, label: "Tracked" },
            { id: "has_draft" as const, label: "Has draft" },
          ] as const
        ).map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => setFilter(option.id)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              filter === option.id
                ? "bg-sky-500/20 text-sky-400"
                : "bg-zinc-800 text-zinc-400 hover:text-white"
            }`}
          >
            {option.label}
            <span className="ml-1.5 text-xs opacity-70">({counts[option.id]})</span>
          </button>
        ))}
        <button
          type="button"
          onClick={openPicker}
          className="ml-auto rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-500"
        >
          + Add
        </button>
      </div>

      {pickerOpen && (
        <PickerPanel
          query={query}
          setQuery={setQuery}
          rows={pickerMatches}
          loading={pickerLoading}
          error={pickerError}
          busyId={busyId}
          onTrack={handleTrack}
          onClose={() => setPickerOpen(false)}
        />
      )}

      {filtered.length === 0 ? (
        <p className="rounded-lg border border-dashed border-zinc-700 p-6 text-center text-sm text-zinc-500">
          No applications match this filter.
        </p>
      ) : (
        <div className="space-y-3">
          {filtered.map((item) => (
            <ApplicationDraftCard
              key={`${item.source_table}-${item.source_id}-${item.title}`}
              item={item}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function PickerPanel({
  query,
  setQuery,
  rows,
  loading,
  error,
  busyId,
  onTrack,
  onClose,
}: {
  query: string;
  setQuery: (value: string) => void;
  rows: ScoutOpportunity[];
  loading: boolean;
  error: string | null;
  busyId: number | null;
  onTrack: (id: number) => void;
  onClose: () => void;
}) {
  return (
    <div className="mb-4 rounded-lg border border-zinc-700 bg-zinc-950 p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-white">Add from Scout</p>
        <button type="button" onClick={onClose} className="text-sm text-zinc-500 hover:text-zinc-300">
          Close
        </button>
      </div>
      <input
        type="search"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search by name, category, fit…"
        className="mt-3 w-full rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-sky-500 focus:outline-none"
      />
      {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
      {loading ? (
        <p className="mt-4 text-sm text-zinc-500">Loading opportunities…</p>
      ) : rows.length === 0 ? (
        <p className="mt-4 text-sm text-zinc-500">No untracked opportunities found.</p>
      ) : (
        <ul className="mt-3 max-h-64 space-y-2 overflow-y-auto">
          {rows.slice(0, 30).map((row) => (
            <li
              key={row.id}
              className="flex items-start justify-between gap-3 rounded-lg border border-zinc-800 bg-zinc-900/60 px-3 py-2"
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-white">
                  {row.url ? (
                    <ExternalLink url={row.url}>{row.name}</ExternalLink>
                  ) : (
                    row.name
                  )}
                </p>
                <p className="mt-0.5 text-xs text-zinc-500">
                  {formatCategory(row.category)}
                  {row.score_total != null && ` · ${row.score_total.toFixed(1)} pts`}
                  {row.deadline_at && ` · due ${formatDate(row.deadline_at)}`}
                </p>
              </div>
              <button
                type="button"
                disabled={busyId === row.id}
                onClick={() => onTrack(row.id)}
                className="shrink-0 rounded bg-sky-600 px-2 py-1 text-xs font-medium text-white hover:bg-sky-500 disabled:opacity-50"
              >
                {busyId === row.id ? "…" : "Track"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
