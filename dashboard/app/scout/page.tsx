import { DataTable } from "@/components/DataTable";
import { ExternalLink, StatusBadge, formatDate } from "@/components/ui";
import { api } from "@/lib/api";

function formatCategory(category: string) {
  return category.replace(/_/g, " ");
}

export default async function ScoutPage() {
  let rows: Awaited<ReturnType<typeof api.scout>> = [];
  try {
    rows = await api.scout();
  } catch {
    /* handled by empty state */
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Funding Scout</h1>
      <p className="mt-1 text-zinc-400">
        Ranked for pre-seed EdTech · translation · pronunciation · underresourced languages · NYC
      </p>
      <div className="mt-6">
        <DataTable
          rows={rows}
          columns={[
            {
              key: "score_total",
              label: "Score",
              render: (row) =>
                row.score_total != null ? (
                  <span className="font-medium text-emerald-400">{Number(row.score_total).toFixed(1)}</span>
                ) : (
                  "—"
                ),
            },
            {
              key: "name",
              label: "Name",
              render: (row) => (
                <ExternalLink url={row.url as string | null}>{row.name as string}</ExternalLink>
              ),
            },
            {
              key: "category",
              label: "Category",
              render: (row) => formatCategory(row.category as string),
            },
            {
              key: "rank_reason",
              label: "Fit",
            },
            {
              key: "deadline_at",
              label: "Deadline",
              render: (row) =>
                row.deadline_at ? formatDate(row.deadline_at as string) : "—",
            },
            {
              key: "status",
              label: "Status",
              render: (row) => <StatusBadge status={row.status as string} />,
            },
          ]}
        />
      </div>
    </div>
  );
}
