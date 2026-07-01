import Link from "next/link";

import { AddOpportunityForm } from "@/components/AddOpportunityForm";
import { DataTable } from "@/components/DataTable";
import { DeadlineEditor } from "@/components/DeadlineEditor";
import { ScoutSourceFilter } from "@/components/ScoutSourceFilter";
import { ExternalLink, StatusBadge } from "@/components/ui";
import { api } from "@/lib/api";

function formatCategory(category: string) {
  return category.replace(/_/g, " ");
}

function formatSource(source: string | null) {
  if (!source) return "agent";
  if (source === "twitter") return "Twitter";
  if (source === "manual") return "Saved";
  return source;
}

type ScoutSource = "all" | "manual" | "agent";

export default async function ScoutPage({
  searchParams,
}: {
  searchParams: Promise<{ source?: string }>;
}) {
  const params = await searchParams;
  const sourceParam = params.source;
  const activeSource: ScoutSource =
    sourceParam === "manual" ? "manual" : sourceParam === "agent" ? "agent" : "all";

  let rows: Awaited<ReturnType<typeof api.scout>> = [];
  try {
    rows = await api.scout(
      activeSource === "all"
        ? undefined
        : { source: activeSource === "manual" ? "manual" : "agent" }
    );
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
        <AddOpportunityForm />
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
        <ScoutSourceFilter active={activeSource} />
        {activeSource === "manual" && (
          <Link href="/assistant" className="text-sm text-sky-400 hover:underline">
            View in Assistant →
          </Link>
        )}
      </div>

      <div className="mt-4">
        <DataTable
          rows={rows}
          columns={[
            {
              key: "score_total",
              label: "Score",
              render: (row) =>
                row.score_total != null ? (
                  <span className="font-medium text-emerald-400">
                    {Number(row.score_total).toFixed(1)}
                  </span>
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
              key: "source",
              label: "Source",
              render: (row) => (
                <span className="text-zinc-400">{formatSource(row.source as string | null)}</span>
              ),
            },
            {
              key: "rank_reason",
              label: "Fit",
            },
            {
              key: "deadline_at",
              label: "Deadline",
              render: (row) => (
                <DeadlineEditor
                  sourceTable="scout_opportunities"
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
