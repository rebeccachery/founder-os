import { DataTable } from "@/components/DataTable";
import { ExternalLink, StatusBadge, formatDate } from "@/components/ui";
import { api } from "@/lib/api";

export default async function DeadlinesPage() {
  let rows: Awaited<ReturnType<typeof api.deadlines>> = [];
  try {
    rows = await api.deadlines(90);
  } catch {
    /* empty state */
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Deadlines</h1>
      <p className="mt-1 text-zinc-400">
        Unified view of grant, competition, and CRM follow-up dates.
      </p>
      <div className="mt-6">
        <DataTable
          rows={rows}
          columns={[
            {
              key: "title",
              label: "Title",
              render: (row) =>
                row.url ? (
                  <ExternalLink url={row.url as string}>{row.title as string}</ExternalLink>
                ) : (
                  (row.title as string)
                ),
            },
            { key: "category", label: "Category" },
            {
              key: "deadline_at",
              label: "Deadline",
              render: (row) => formatDate(row.deadline_at as string),
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
