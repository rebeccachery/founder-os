import { ExternalLink, formatDate } from "@/components/ui";
import type { BriefingConflict } from "@/lib/api";

const severityStyles: Record<string, string> = {
  high: "border-amber-500/40 bg-amber-500/10",
  medium: "border-orange-500/30 bg-orange-500/5",
};

export function ConflictAlert({ conflicts }: { conflicts: BriefingConflict[] }) {
  return (
    <div className="space-y-3">
      {conflicts.map((conflict, index) => (
        <div
          key={`${conflict.summary}-${index}`}
          className={`rounded-lg border p-4 ${severityStyles[conflict.severity] || severityStyles.medium}`}
        >
          <p className="font-medium text-amber-200">{conflict.summary}</p>
          <ul className="mt-2 space-y-1 text-sm text-amber-100/80">
            {conflict.items.map((item, itemIndex) => (
              <li key={`${item.title}-${itemIndex}`}>
                {item.url ? (
                  <ExternalLink url={item.url}>{item.title}</ExternalLink>
                ) : (
                  item.title
                )}
                {item.due_at && ` — ${formatDate(item.due_at)}`}
                <span className="text-amber-200/60"> ({item.category})</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
