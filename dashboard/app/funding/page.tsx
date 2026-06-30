import { DataTable } from "@/components/DataTable";
import { ExternalLink, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";

export default async function FundingPage() {
  let rows: Awaited<ReturnType<typeof api.funding>> = [];
  try {
    rows = await api.funding();
  } catch {
    /* handled by empty state */
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Funding</h1>
      <p className="mt-1 text-zinc-400">Accelerators, programs, and funding opportunities.</p>
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
            { key: "organization", label: "Organization" },
            { key: "amount", label: "Amount" },
            { key: "stage", label: "Stage" },
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
