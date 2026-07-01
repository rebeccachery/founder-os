"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { ExternalLink, StatusBadge, formatDate } from "@/components/ui";
import { BriefingDeadlineCell } from "@/components/DeadlineEditor";
import {
  type BriefingItem,
  getApplicationDraft,
  saveApplicationDraft,
} from "@/lib/api";

function formatCategory(category: string) {
  return category.replace(/_/g, " ");
}

function copyText(text: string) {
  return navigator.clipboard.writeText(text);
}

export function ApplicationDraftCard({ item }: { item: BriefingItem }) {
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const [body, setBody] = useState("");
  const [savedBody, setSavedBody] = useState("");
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  const canDraft =
    item.source_table != null &&
    item.source_id != null &&
    ["scout_opportunities", "grants", "competitions"].includes(item.source_table);

  const dirty = body !== savedBody;

  useEffect(() => {
    if (!expanded || !canDraft) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    getApplicationDraft(item.source_table!, item.source_id!)
      .then((draft) => {
        if (cancelled) return;
        setBody(draft.body);
        setSavedBody(draft.body);
        setSavedAt(draft.updated_at ?? null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load draft");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [expanded, canDraft, item.source_table, item.source_id]);

  async function handleSave() {
    if (!canDraft) return;
    setBusy(true);
    setError(null);
    try {
      const draft = await saveApplicationDraft(
        item.source_table!,
        item.source_id!,
        body
      );
      setSavedBody(draft.body);
      setSavedAt(draft.updated_at ?? null);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save draft");
    } finally {
      setBusy(false);
    }
  }

  async function handleCopy() {
    setError(null);
    try {
      await copyText(body);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not copy to clipboard");
    }
  }

  function handleCollapse() {
    if (dirty) {
      const discard = window.confirm(
        "You have unsaved changes. Discard them and collapse?"
      );
      if (!discard) return;
    }
    setExpanded(false);
    setError(null);
  }

  return (
    <article className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-sky-400/80">
            {formatCategory(item.category)}
          </p>
          <h3 className="mt-1 font-medium text-white">
            {item.url ? (
              <ExternalLink url={item.url}>{item.title}</ExternalLink>
            ) : (
              item.title
            )}
          </h3>
          <p className="mt-1 text-sm text-zinc-500">{item.reason}</p>
        </div>
        <div className="flex flex-col items-end gap-2">
          {item.status && <StatusBadge status={item.status} />}
          {item.has_draft && !expanded && (
            <span className="text-xs text-emerald-400">Draft saved</span>
          )}
          {dirty && expanded && (
            <span className="text-xs text-amber-400">Unsaved changes</span>
          )}
        </div>
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-zinc-400">
        <div className="inline-flex flex-wrap items-center gap-1">
          <span>Due:</span>
          <BriefingDeadlineCell
            dueAt={item.due_at}
            sourceId={item.source_id}
            sourceTable={item.source_table ?? null}
          />
        </div>
        {item.draft_preview && !expanded && (
          <span className="max-w-md truncate text-zinc-500">
            {item.draft_preview}
          </span>
        )}
      </div>

      {canDraft && (
        <div className="mt-4">
          {!expanded ? (
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="text-sm text-sky-400 hover:underline"
            >
              {item.has_draft ? "Edit response draft" : "Write response draft"}
            </button>
          ) : (
            <div className="space-y-3">
              {loading ? (
                <p className="text-sm text-zinc-500">Loading draft…</p>
              ) : (
                <>
                  <textarea
                    value={body}
                    onChange={(e) => setBody(e.target.value)}
                    rows={8}
                    placeholder="Write your application response draft here…"
                    className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-sky-500 focus:outline-none"
                  />
                  <p className="text-xs text-zinc-600">
                    {body.length.toLocaleString()} characters
                  </p>
                </>
              )}
              {savedAt && !dirty && (
                <p className="text-xs text-zinc-500">
                  Last saved {formatDate(savedAt)}
                </p>
              )}
              {error && <p className="text-sm text-red-400">{error}</p>}
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy || loading || !dirty}
                  onClick={handleSave}
                  className="rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {busy ? "Saving…" : "Save draft"}
                </button>
                <button
                  type="button"
                  disabled={loading || !body.trim()}
                  onClick={handleCopy}
                  className="rounded-lg bg-zinc-800 px-3 py-1.5 text-sm font-medium text-white hover:bg-zinc-700 disabled:opacity-50"
                >
                  {copied ? "Copied!" : "Copy"}
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={handleCollapse}
                  className="rounded-lg border border-zinc-700 px-3 py-1.5 text-sm text-zinc-400 hover:border-zinc-500"
                >
                  Collapse
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </article>
  );
}
