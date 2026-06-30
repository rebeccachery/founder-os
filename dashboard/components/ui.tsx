export function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    new: "bg-emerald-500/20 text-emerald-400",
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
