"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ExternalLink } from "@/components/ui";
import { BriefingDeadlineCell } from "@/components/DeadlineEditor";
import { type BriefingItem, upsertAssistantTrack } from "@/lib/api";

function dismissUntil(days: number) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

export function PriorityList({ items }: { items: BriefingItem[] }) {
  const router = useRouter();
  const [busyKey, setBusyKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handlePin(item: BriefingItem) {
    if (item.source_table !== "scout_opportunities" || item.source_id == null) return;
    const key = `pin-${item.source_id}`;
    setBusyKey(key);
    setError(null);
    try {
      await upsertAssistantTrack(item.source_id, {
        pin_priority: !item.pin_priority,
        track_application: true,
        clear_dismissed: true,
      });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusyKey(null);
    }
  }

  async function handleDismiss(item: BriefingItem) {
    if (item.source_table !== "scout_opportunities" || item.source_id == null) return;
    const key = `dismiss-${item.source_id}`;
    setBusyKey(key);
    setError(null);
    try {
      await upsertAssistantTrack(item.source_id, {
        dismissed_until: dismissUntil(7),
        pin_priority: false,
      });
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setBusyKey(null);
    }
  }

  const canManage = (item: BriefingItem) =>
    item.source_table === "scout_opportunities" && item.source_id != null;

  return (
    <div>
      {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
      <ol className="space-y-3">
        {items.map((item, index) => (
          <li
            key={`${item.title}-${item.source_id}-${index}`}
            className="flex gap-4 rounded-lg border border-zinc-800 bg-zinc-950/50 p-4"
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-sky-500/20 text-sm font-semibold text-sky-400">
              {index + 1}
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-white">
                  {item.url ? (
                    <ExternalLink url={item.url}>{item.title}</ExternalLink>
                  ) : (
                    item.title
                  )}
                </span>
                <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-xs text-zinc-400">
                  {item.category}
                </span>
                {item.priority_source === "pinned" ? (
                  <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-300">
                    Pinned
                  </span>
                ) : (
                  <span className="rounded-full bg-zinc-800 px-2 py-0.5 text-xs text-zinc-500">
                    Auto
                  </span>
                )}
                <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-300">
                  {item.priority_score.toFixed(0)} pts
                </span>
              </div>
              <p className="mt-1 text-sm text-zinc-400">{item.reason}</p>
              <div className="mt-1 text-xs text-zinc-500">
                Due{" "}
                <BriefingDeadlineCell
                  dueAt={item.due_at}
                  sourceId={item.source_id}
                  sourceTable={item.source_table ?? null}
                />
              </div>
              {canManage(item) && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    type="button"
                    disabled={busyKey !== null}
                    onClick={() => handlePin(item)}
                    className={`rounded-lg px-2 py-1 text-xs font-medium transition disabled:opacity-50 ${
                      item.pin_priority
                        ? "bg-amber-500/20 text-amber-300"
                        : "bg-zinc-800 text-zinc-400 hover:text-white"
                    }`}
                  >
                    {busyKey === `pin-${item.source_id}`
                      ? "…"
                      : item.pin_priority
                        ? "Unpin"
                        : "Pin"}
                  </button>
                  {item.priority_source !== "pinned" && (
                    <button
                      type="button"
                      disabled={busyKey !== null}
                      onClick={() => handleDismiss(item)}
                      className="rounded-lg bg-zinc-800 px-2 py-1 text-xs font-medium text-zinc-400 hover:text-white disabled:opacity-50"
                    >
                      {busyKey === `dismiss-${item.source_id}` ? "…" : "Dismiss 7d"}
                    </button>
                  )}
                </div>
              )}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
