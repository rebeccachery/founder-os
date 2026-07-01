import { ExternalLink } from "@/components/ui";
import { BriefingDeadlineCell } from "@/components/DeadlineEditor";
import type { BriefingItem } from "@/lib/api";

export function PriorityList({ items }: { items: BriefingItem[] }) {
  return (
    <ol className="space-y-3">
      {items.map((item, index) => (
        <li
          key={`${item.title}-${item.due_at}-${index}`}
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
          </div>
        </li>
      ))}
    </ol>
  );
}
