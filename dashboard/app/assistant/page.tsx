import { AddOpportunityForm } from "@/components/AddOpportunityForm";
import { ApplicationDraftSection } from "@/components/ApplicationDraftSection";
import { BriefingDeadlineCell } from "@/components/DeadlineEditor";
import { BriefingSection } from "@/components/BriefingSection";
import { ConflictAlert } from "@/components/ConflictAlert";
import { DataTable } from "@/components/DataTable";
import { PriorityList } from "@/components/PriorityList";
import { ExternalLink, StatusBadge, formatDate } from "@/components/ui";
import { api } from "@/lib/api";

function formatGeneratedAt(iso: string) {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default async function AssistantPage() {
  let briefing: Awaited<ReturnType<typeof api.briefing>> | null = null;
  let error: string | null = null;

  try {
    briefing = await api.briefing();
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to load briefing";
  }

  const itemColumns = [
    {
      key: "title",
      label: "Title",
      render: (row: Record<string, unknown>) =>
        row.url ? (
          <ExternalLink url={row.url as string}>{row.title as string}</ExternalLink>
        ) : (
          (row.title as string)
        ),
    },
    { key: "category", label: "Type" },
    {
      key: "due_at",
      label: "Due",
      render: (row: Record<string, unknown>) => (
        <BriefingDeadlineCell
          dueAt={row.due_at as string | null}
          sourceId={row.source_id as number | null}
          sourceTable={row.source_table as string | null}
        />
      ),
    },
    {
      key: "reason",
      label: "Note",
    },
    {
      key: "status",
      label: "Status",
      render: (row: Record<string, unknown>) =>
        row.status ? <StatusBadge status={row.status as string} /> : "—",
    },
  ];

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Executive Assistant</h1>
      <p className="mt-1 text-zinc-400">
        Your morning briefing — priorities, conflicts, follow-ups, deadlines, meetings, and
        applications.
      </p>

      {error && (
        <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-200">
          API unavailable: {error}. Start the backend with{" "}
          <code className="text-amber-100">uvicorn api.main:app --reload</code>
        </div>
      )}

      {briefing && (
        <p className="mt-3 text-sm text-zinc-500">
          Briefing for {formatDate(briefing.briefing_date)} · Updated{" "}
          {formatGeneratedAt(briefing.generated_at)}
        </p>
      )}

      <div className="mt-6">
        <AddOpportunityForm />
      </div>

      <div className="mt-8 space-y-6">
        <BriefingSection
          title="Today's priorities"
          description="Top actions ranked by urgency and fit."
          isEmpty={!briefing?.priorities.length}
          emptyMessage="No urgent priorities today. Review applications below."
        >
          {briefing && <PriorityList items={briefing.priorities} />}
        </BriefingSection>

        <BriefingSection
          title="Potential conflicts"
          description="Scheduling overlaps and competing deadlines."
          isEmpty={!briefing?.conflicts.length}
          emptyMessage="No conflicts detected."
        >
          {briefing && <ConflictAlert conflicts={briefing.conflicts} />}
        </BriefingSection>

        <div className="grid gap-6 lg:grid-cols-2">
          <BriefingSection
            title="Follow-ups"
            description="CRM contacts due for outreach."
            isEmpty={!briefing?.follow_ups.length}
            emptyMessage="No follow-ups in the next two weeks."
          >
            {briefing && (
              <DataTable rows={briefing.follow_ups} columns={itemColumns.slice(0, 4)} />
            )}
          </BriefingSection>

          <BriefingSection
            title="Meetings"
            description="Interviews, calls, and calendar events."
            isEmpty={!briefing?.meetings.length}
            emptyMessage="No meetings scheduled. Add calendar events in Phase 2."
          >
            {briefing && (
              <DataTable rows={briefing.meetings} columns={itemColumns.slice(0, 4)} />
            )}
          </BriefingSection>
        </div>

        <BriefingSection
          title="Deadlines"
          description="Grants, fellowships, competitions, launches, and CRM dates — next 14 days."
          isEmpty={!briefing?.deadlines.length}
          emptyMessage="No upcoming deadlines. Run daily agents to discover opportunities."
        >
          {briefing && <DataTable rows={briefing.deadlines} columns={itemColumns} />}
        </BriefingSection>

        <BriefingSection
          title="Applications"
          description="Open grant, fellowship, and competition applications to review or submit."
          isEmpty={!briefing?.applications.length}
          emptyMessage="No open applications. Check Scout for new opportunities."
        >
          {briefing && <ApplicationDraftSection items={briefing.applications} />}
        </BriefingSection>
      </div>
    </div>
  );
}
