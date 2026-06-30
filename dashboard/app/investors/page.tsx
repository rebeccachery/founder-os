import { DataTable } from "@/components/DataTable";
import { ExternalLink, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";

export default async function InvestorsPage() {
  let rows: Awaited<ReturnType<typeof api.investors>> = [];
  try {
    rows = await api.investors();
  } catch {
    /* empty state */
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Investors</h1>
      <p className="mt-1 text-zinc-400">VCs and angels discovered by the investors agent.</p>
      <div className="mt-6">
        <DataTable
          rows={rows}
          columns={[
            {
              key: "name",
              label: "Name",
              render: (row) => (
                <ExternalLink url={row.url as string | null}>{row.name as string}</ExternalLink>
              ),
            },
            { key: "firm", label: "Firm" },
            { key: "stage", label: "Stage" },
            {
              key: "thesis",
              label: "Thesis",
              render: (row) => {
                const t = row.thesis as string | null;
                return t ? (t.length > 80 ? `${t.slice(0, 80)}…` : t) : "—";
              },
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
