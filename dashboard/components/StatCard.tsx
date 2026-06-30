interface StatCardProps {
  label: string;
  value: number;
  href?: string;
}

export function StatCard({ label, value, href }: StatCardProps) {
  const content = (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-4">
      <p className="text-sm text-zinc-400">{label}</p>
      <p className="mt-1 text-3xl font-semibold text-white">{value}</p>
    </div>
  );

  if (href) {
    return (
      <a href={href} className="block transition hover:border-zinc-600">
        {content}
      </a>
    );
  }
  return content;
}
