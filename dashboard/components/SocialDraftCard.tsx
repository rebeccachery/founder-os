"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { StatusBadge } from "@/components/ui";
import { type SocialPost, type SocialPostStatus, updateSocialPost } from "@/lib/api";

const CONTENT_TYPE_LABELS: Record<string, string> = {
  twitter_thread: "Twitter thread",
  linkedin_post: "LinkedIn post",
  demo_idea: "Demo idea",
  launch_announcement: "Launch announcement",
};

function copyText(text: string) {
  const hookAndBody = text.trim();
  return navigator.clipboard.writeText(hookAndBody);
}

export function SocialDraftCard({ post }: { post: SocialPost }) {
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const label = CONTENT_TYPE_LABELS[post.content_type] || post.content_type;
  const copyPayload = post.hook ? `${post.hook}\n\n${post.body}` : post.body;

  async function setStatus(status: SocialPostStatus) {
    setBusy(status);
    setError(null);
    try {
      await updateSocialPost(post.id, { status });
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusy(null);
    }
  }

  async function handleCopy() {
    setError(null);
    try {
      await copyText(copyPayload);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setError("Could not copy to clipboard");
    }
  }

  return (
    <article className="rounded-lg border border-zinc-800 bg-zinc-900/80 p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-violet-400">{label}</p>
          <h3 className="mt-1 text-lg font-medium text-white">{post.title || label}</h3>
        </div>
        <StatusBadge status={post.status} />
      </div>

      {post.hook && (
        <p className="mt-4 text-sm font-medium text-zinc-200">{post.hook}</p>
      )}

      <pre className="mt-3 whitespace-pre-wrap font-sans text-sm leading-relaxed text-zinc-400">
        {post.body}
      </pre>

      <div className="mt-4 flex flex-wrap gap-2 text-xs text-zinc-500">
        {post.llm_model && <span>via {post.llm_model}</span>}
        {post.signal_score != null && (
          <span>· signal {Number(post.signal_score).toFixed(1)}</span>
        )}
        <span>· {new Date(post.generated_at).toLocaleDateString()}</span>
      </div>

      {error && <p className="mt-3 text-sm text-red-400">{error}</p>}

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleCopy}
          className="rounded-lg bg-zinc-800 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-zinc-700"
        >
          {copied ? "Copied!" : "Copy"}
        </button>
        {post.status === "draft" && (
          <>
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => setStatus("approved")}
              className="rounded-lg bg-blue-500/20 px-3 py-1.5 text-sm font-medium text-blue-400 transition hover:bg-blue-500/30 disabled:opacity-50"
            >
              {busy === "approved" ? "…" : "Approve"}
            </button>
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => setStatus("skipped")}
              className="rounded-lg bg-zinc-800 px-3 py-1.5 text-sm font-medium text-zinc-400 transition hover:bg-zinc-700 disabled:opacity-50"
            >
              {busy === "skipped" ? "…" : "Skip"}
            </button>
            <button
              type="button"
              disabled={busy !== null}
              onClick={() => setStatus("posted")}
              className="rounded-lg bg-emerald-500/20 px-3 py-1.5 text-sm font-medium text-emerald-400 transition hover:bg-emerald-500/30 disabled:opacity-50"
            >
              {busy === "posted" ? "…" : "Mark posted"}
            </button>
          </>
        )}
        {post.status === "approved" && (
          <button
            type="button"
            disabled={busy !== null}
            onClick={() => setStatus("posted")}
            className="rounded-lg bg-emerald-500/20 px-3 py-1.5 text-sm font-medium text-emerald-400 transition hover:bg-emerald-500/30 disabled:opacity-50"
          >
            {busy === "posted" ? "…" : "Mark posted"}
          </button>
        )}
      </div>
    </article>
  );
}

export function RunSocialAgentButton() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleRun() {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const { runSocialAgent } = await import("@/lib/api");
      const result = await runSocialAgent();
      setMessage(result.message || "Social agent finished.");
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Agent run failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={handleRun}
        disabled={busy}
        className="rounded-lg bg-violet-500/20 px-4 py-2 text-sm font-medium text-violet-300 transition hover:bg-violet-500/30 disabled:opacity-50"
      >
        {busy ? "Running agent…" : "Run social agent"}
      </button>
      {message && <p className="mt-2 text-sm text-emerald-400">{message}</p>}
      {error && <p className="mt-2 text-sm text-red-400">{error}</p>}
    </div>
  );
}
