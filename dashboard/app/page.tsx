import { StatCard } from "@/components/StatCard";
import { DataTable } from "@/components/DataTable";
import { StatusBadge, formatDate } from "@/components/ui";
import { api } from "@/lib/api";

export default async function HomePage() {
  let stats = {
    investors: 0,
    funding: 0,
    grants: 0,
    competitions: 0,
    scout: 0,
    oss: 0,
    social: 0,
    deadlines_upcoming: 0,
    contacts: 0,
    new_items: 0,
  };
  let deadlines: Awaited<ReturnType<typeof api.deadlines>> = [];
  let error: string | null = null;

  try {
    [stats, deadlines] = await Promise.all([api.stats(), api.deadlines(14)]);
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to connect to API";
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Overview</h1>
      <p className="mt-1 text-zinc-400">Your founder operating system at a glance.</p>

      {error && (
        <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-200">
          API unavailable: {error}. Start the backend with{" "}
          <code className="text-amber-100">uvicorn api.main:app --reload</code>
        </div>
      )}

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Scout picks" value={stats.scout} href="/scout" />
        <StatCard label="OSS resources" value={stats.oss} href="/oss" />
        <StatCard label="Social drafts" value={stats.social} href="/social" />
        <StatCard label="Investors" value={stats.investors} href="/investors" />
      </div>

      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Funding" value={stats.funding} href="/funding" />
        <StatCard label="Grants" value={stats.grants} href="/grants" />
        <StatCard label="Competitions" value={stats.competitions} href="/competitions" />
        <StatCard label="Upcoming deadlines (30d)" value={stats.deadlines_upcoming} href="/assistant" />
      </div>

      <div className="mt-4">
        <StatCard label="New items to review" value={stats.new_items} />
      </div>

      <section className="mt-10">
        <h2 className="mb-4 text-lg font-medium text-white">Deadlines — next 14 days</h2>
        <DataTable
          rows={deadlines.slice(0, 10)}
          columns={[
            { key: "title", label: "Title" },
            { key: "category", label: "Type" },
            {
              key: "deadline_at",
              label: "Due",
              render: (row) => formatDate(row.deadline_at as string),
            },
            {
              key: "status",
              label: "Status",
              render: (row) => <StatusBadge status={row.status as string} />,
            },
          ]}
        />
      </section>
    </div>
  );
}
