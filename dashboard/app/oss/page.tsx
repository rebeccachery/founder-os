import Link from "next/link";

import { DataTable } from "@/components/DataTable";
import { ExternalLink, StatusBadge, formatDate } from "@/components/ui";
import { api, type OssView } from "@/lib/api";

const VIEWS: { id: OssView; label: string; description: string }[] = [
  {
    id: "recent",
    label: "Recent",
    description: "Updated or newly discovered in the last 90 days",
  },
  {
    id: "reference",
    label: "Reference",
    description: "Benchmarks & eval tools — evergreen, any age",
  },
  { id: "all", label: "All", description: "Full stored catalog" },
];

const TYPES = [
  { id: "", label: "All types" },
  { id: "dataset", label: "Datasets" },
  { id: "model", label: "Models" },
  { id: "repo", label: "Repos" },
  { id: "benchmark", label: "Benchmarks" },
  { id: "eval_tool", label: "Eval tools" },
];

function formatType(type: string) {
  return type.replace(/_/g, " ");
}

function tabHref(view: string, type: string) {
  const params = new URLSearchParams();
  if (view !== "recent") params.set("view", view);
  if (type) params.set("type", type);
  const qs = params.toString();
  return qs ? `/oss?${qs}` : "/oss";
}

export default async function OssPage({
  searchParams,
}: {
  searchParams: Promise<{ view?: string; type?: string }>;
}) {
  const params = await searchParams;
  const view = (params.view as OssView) || "recent";
  const type = params.type || "";

  let rows: Awaited<ReturnType<typeof api.oss>> = [];
  let error: string | null = null;
  try {
    rows = await api.oss({
      view,
      resourceType: type || undefined,
    });
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to connect to API";
  }

  const activeView = VIEWS.find((v) => v.id === view) ?? VIEWS[0];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">OSS Discovery</h1>
      <p className="mt-1 text-zinc-400">
        Haitian Creole · speech · translation · pronunciation · benchmarks · eval tools
      </p>

      {error && (
        <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-200">
          <p>API unavailable: {error}</p>
          <p className="mt-2">
            Start the backend from the repo root using the project venv (not system Python):
          </p>
          <pre className="mt-2 overflow-x-auto rounded bg-zinc-900/80 p-3 text-sm text-amber-100">
            {`source .venv/bin/activate\npip install -r requirements.txt\nuvicorn api.main:app --reload\n\n# or:\n./workflows/run_api.sh`}
          </pre>
        </div>
      )}

      <div className="mt-6 flex flex-wrap gap-2">
        {VIEWS.map((v) => (
          <Link
            key={v.id}
            href={tabHref(v.id, type)}
            className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
              view === v.id
                ? "bg-emerald-500/20 text-emerald-400"
                : "bg-zinc-800 text-zinc-400 hover:text-white"
            }`}
          >
            {v.label}
          </Link>
        ))}
      </div>
      <p className="mt-2 text-sm text-zinc-500">{activeView.description}</p>

      <div className="mt-4 flex flex-wrap gap-2">
        {TYPES.map((t) => (
          <Link
            key={t.id || "all"}
            href={tabHref(view, t.id)}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              type === t.id
                ? "bg-sky-500/20 text-sky-400"
                : "bg-zinc-800/80 text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {t.label}
          </Link>
        ))}
      </div>

      <div className="mt-6">
        <DataTable
          rows={rows}
          emptyMessage={
            error
              ? "Could not load OSS resources."
              : view === "recent"
                ? "No recent resources. Try the All tab — or run oss_discovery again."
                : "No OSS resources yet. Run: python workflows/run_agent.py --agent oss_discovery"
          }
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
              key: "resource_type",
              label: "Type",
              render: (row) => formatType(row.resource_type as string),
            },
            {
              key: "rank_reason",
              label: "Fit",
            },
            {
              key: "last_updated_at",
              label: "Updated",
              render: (row) =>
                row.last_updated_at ? formatDate(row.last_updated_at as string) : "—",
            },
            {
              key: "source",
              label: "Source",
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
