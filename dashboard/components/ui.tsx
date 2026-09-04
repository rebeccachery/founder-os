export function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    new: "bg-emerald-500/20 text-emerald-400",
    draft: "bg-violet-500/20 text-violet-400",
    approved: "bg-blue-500/20 text-blue-400",
    posted: "bg-emerald-500/20 text-emerald-400",
    skipped: "bg-zinc-500/20 text-zinc-400",
    reviewed: "bg-blue-500/20 text-blue-400",
    applied: "bg-amber-500/20 text-amber-400",
    passed: "bg-zinc-500/20 text-zinc-400",
    archived: "bg-zinc-600/20 text-zinc-500",
  };
  return (
    <span
      className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${colors[status] || colors.new}`}
    >
      {status}
    </span>
  );
}

const FRESHNESS_STYLES: Record<string, { label: string; className: string }> = {
  recurring: { label: "Recurring", className: "bg-violet-500/20 text-violet-300" },
  expired: { label: "Expired", className: "bg-red-500/20 text-red-400" },
  expiring_soon: { label: "Closing soon", className: "bg-amber-500/20 text-amber-400" },
  active: { label: "Open", className: "bg-emerald-500/20 text-emerald-400" },
  unknown: { label: "Unconfirmed", className: "bg-zinc-500/20 text-zinc-400" },
};

export function FreshnessBadge({ freshness }: { freshness: string | null | undefined }) {
  const style = FRESHNESS_STYLES[freshness ?? "unknown"] ?? FRESHNESS_STYLES.unknown;
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${style.className}`}>
      {style.label}
    </span>
  );
}

export function ExternalLink({ url, children }: { url: string | null; children: React.ReactNode }) {
  if (!url) return <>{children}</>;
  return (
    <a href={url} target="_blank" rel="noopener noreferrer" className="text-sky-400 hover:underline">
      {children}
    </a>
  );
}

export function formatDate(dateStr: string | null) {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
