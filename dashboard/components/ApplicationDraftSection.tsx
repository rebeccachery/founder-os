"use client";

import { useMemo, useState } from "react";

import {
  ApplicationDraftCard,
} from "@/components/ApplicationDraftCard";
import type { BriefingItem } from "@/lib/api";

type DraftFilter = "all" | "has_draft" | "no_draft";

const FILTERS: { id: DraftFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "has_draft", label: "Has draft" },
  { id: "no_draft", label: "Needs draft" },
];

function filterApplications(items: BriefingItem[], filter: DraftFilter) {
  if (filter === "has_draft") {
    return items.filter((item) => item.has_draft);
  }
  if (filter === "no_draft") {
    return items.filter((item) => !item.has_draft);
  }
  return items;
}

export function ApplicationDraftSection({ items }: { items: BriefingItem[] }) {
  const [filter, setFilter] = useState<DraftFilter>("all");

  const counts = useMemo(
    () => ({
      all: items.length,
      has_draft: items.filter((item) => item.has_draft).length,
      no_draft: items.filter((item) => !item.has_draft).length,
    }),
    [items]
  );

  const filtered = useMemo(
    () => filterApplications(items, filter),
    [items, filter]
  );

  if (items.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-zinc-700 p-8 text-center text-zinc-400">
        No open applications. Check Scout for new opportunities.
      </p>
    );
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((option) => (
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
      </div>

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
