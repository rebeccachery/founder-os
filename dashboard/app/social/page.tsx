import Link from "next/link";

import { RunSocialAgentButton, SocialDraftCard } from "@/components/SocialDraftCard";
import { api, type SocialPostStatus } from "@/lib/api";

const STATUSES: { id: SocialPostStatus | "all"; label: string }[] = [
  { id: "draft", label: "Drafts" },
  { id: "approved", label: "Approved" },
  { id: "posted", label: "Posted" },
  { id: "skipped", label: "Skipped" },
  { id: "archived", label: "Archived" },
  { id: "all", label: "All" },
];

const CONTENT_ORDER = [
  "linkedin_post",
  "twitter_thread",
  "demo_idea",
  "launch_announcement",
];

const CONTENT_TYPE_LABELS: Record<string, string> = {
  twitter_thread: "Twitter thread",
  linkedin_post: "LinkedIn post",
  demo_idea: "Demo idea",
  launch_announcement: "Launch announcement",
};

function tabHref(status: string) {
  return status === "draft" ? "/social" : `/social?status=${status}`;
}

function groupPosts(posts: Awaited<ReturnType<typeof api.social>>) {
  const groups = new Map<string, typeof posts>();
  for (const type of CONTENT_ORDER) {
    const matches = posts.filter((p) => p.content_type === type);
    if (matches.length) groups.set(type, matches);
  }
  for (const post of posts) {
    if (!CONTENT_ORDER.includes(post.content_type)) {
      const existing = groups.get(post.content_type) || [];
      groups.set(post.content_type, [...existing, post]);
    }
  }
  return groups;
}

export default async function SocialPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string }>;
}) {
  const params = await searchParams;
  const statusParam = params.status || "draft";
  const status = statusParam as SocialPostStatus | "all";

  let posts: Awaited<ReturnType<typeof api.social>> = [];
  let error: string | null = null;

  try {
    posts = await api.social(status === "all" ? {} : { status });
  } catch (e) {
    error = e instanceof Error ? e.message : "Failed to connect to API";
  }

  const grouped = groupPosts(posts);

  return (
    <div>
      <h1 className="text-2xl font-semibold text-white">Social Content</h1>
      <p className="mt-1 text-zinc-400">
        Review social drafts generated from your configured product repos.
      </p>

      {error && (
        <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-amber-200">
          <p>API unavailable: {error}</p>
          <p className="mt-2">
            Start the backend from the repo root:
          </p>
          <pre className="mt-2 overflow-x-auto rounded bg-zinc-900/80 p-3 text-sm text-amber-100">
            {`source .venv/bin/activate\nuvicorn api.main:app --reload`}
          </pre>
        </div>
      )}

      <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap gap-2">
          {STATUSES.map((s) => (
            <Link
              key={s.id}
              href={tabHref(s.id)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition ${
                status === s.id
                  ? "bg-violet-500/20 text-violet-400"
                  : "bg-zinc-800 text-zinc-400 hover:text-white"
              }`}
            >
              {s.label}
            </Link>
          ))}
        </div>
        {!error && <RunSocialAgentButton />}
      </div>

      {!error && posts.length === 0 && (
        <div className="mt-10 rounded-lg border border-dashed border-zinc-700 bg-zinc-900/40 p-8 text-center">
          <p className="text-zinc-300">No {status === "all" ? "" : status} posts yet.</p>
          <p className="mt-2 text-sm text-zinc-500">
            Run the social agent to generate Twitter threads, LinkedIn posts, demo ideas, and launch copy.
          </p>
          <div className="mt-4 flex justify-center">
            <RunSocialAgentButton />
          </div>
          <p className="mt-4 text-xs text-zinc-600">
            Or from the terminal:{" "}
            <code className="text-zinc-500">python workflows/run_agent.py --agent social</code>
          </p>
        </div>
      )}

      <div className="mt-8 space-y-10">
        {Array.from(grouped.entries()).map(([contentType, items]) => (
          <section key={contentType}>
            <h2 className="mb-4 text-lg font-medium text-white">
              {CONTENT_TYPE_LABELS[contentType] || contentType}
            </h2>
            <div className="grid gap-4 lg:grid-cols-2">
              {items.map((post) => (
                <SocialDraftCard key={post.id} post={post} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
