import { ReactNode } from "react";

export function BriefingSection({
  title,
  description,
  children,
  emptyMessage,
  isEmpty,
}: {
  title: string;
  description?: string;
  children: ReactNode;
  emptyMessage?: string;
  isEmpty?: boolean;
}) {
  return (
    <section className="rounded-lg border border-zinc-800 bg-zinc-900/40 p-5">
      <h2 className="text-lg font-medium text-white">{title}</h2>
      {description && <p className="mt-1 text-sm text-zinc-400">{description}</p>}
      <div className="mt-4">
        {isEmpty ? (
          <p className="rounded-lg border border-dashed border-zinc-700 p-6 text-center text-sm text-zinc-500">
            {emptyMessage || "Nothing scheduled."}
          </p>
        ) : (
          children
        )}
      </div>
    </section>
  );
}
