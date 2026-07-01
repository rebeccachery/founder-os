import { DataTable } from "@/components/DataTable";
import { DeadlineEditor } from "@/components/DeadlineEditor";
import { ExternalLink, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";

export default async function CompetitionsPage() {
  let rows: Awaited<ReturnType<typeof api.competitions>> = [];
  try {
    rows = await api.competitions();
  } catch {
    /* empty state */
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Competitions</h1>
      <p className="mt-1 text-zinc-400">Pitch competitions, hackathons, and innovation challenges.</p>
      <div className="mt-6">
        <DataTable
          rows={rows}
          columns={[
            {
              key: "name",
              label: "Competition",
              render: (row) => (
                <ExternalLink url={row.url as string | null}>{row.name as string}</ExternalLink>
              ),
            },
            { key: "organizer", label: "Organizer" },
            { key: "prize", label: "Prize" },
            {
              key: "deadline_at",
              label: "Deadline",
              render: (row) => (
                <DeadlineEditor
                  sourceTable="competitions"
                  sourceId={row.id as number}
                  deadlineAt={row.deadline_at as string | null}
                />
              ),
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
