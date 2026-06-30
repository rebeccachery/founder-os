import { DataTable } from "@/components/DataTable";
import { ExternalLink, StatusBadge, formatDate } from "@/components/ui";
import { api } from "@/lib/api";

export default async function GrantsPage() {
  let rows: Awaited<ReturnType<typeof api.grants>> = [];
  try {
    rows = await api.grants();
  } catch {
    /* empty state */
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Grants</h1>
      <p className="mt-1 text-zinc-400">Grant programs and application deadlines.</p>
      <div className="mt-6">
        <DataTable
          rows={rows}
          columns={[
            {
              key: "name",
              label: "Grant",
              render: (row) => (
                <ExternalLink url={row.url as string | null}>{row.name as string}</ExternalLink>
              ),
            },
            { key: "funder", label: "Funder" },
            { key: "amount", label: "Amount" },
            {
              key: "deadline_at",
              label: "Deadline",
              render: (row) => formatDate(row.deadline_at as string | null),
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
