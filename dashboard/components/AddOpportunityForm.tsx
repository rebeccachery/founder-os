"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createSavedOpportunity } from "@/lib/api";

const CATEGORIES = [
  { value: "", label: "Auto-detect" },
  { value: "fellowships", label: "Fellowship" },
  { value: "grants", label: "Grant" },
  { value: "startup_competitions", label: "Competition" },
  { value: "accelerators", label: "Accelerator" },
  { value: "hackathons", label: "Hackathon" },
  { value: "cloud_credits", label: "Cloud credits" },
  { value: "university_programs", label: "University program" },
  { value: "ai_research_funding", label: "AI research funding" },
  { value: "other", label: "Other" },
];

export function AddOpportunityForm() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [paste, setPaste] = useState("");
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [deadline, setDeadline] = useState("");
  const [tweetUrl, setTweetUrl] = useState("");
  const [sharedBy, setSharedBy] = useState("");

  function resetForm() {
    setPaste("");
    setUrl("");
    setName("");
    setCategory("");
    setDeadline("");
    setTweetUrl("");
    setSharedBy("");
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setSuccess(null);

    try {
      const result = await createSavedOpportunity({
        url: url.trim() || undefined,
        name: name.trim() || undefined,
        category: category || undefined,
        deadline_at: deadline || undefined,
        description: paste.trim() || undefined,
        source_tweet_url: tweetUrl.trim() || undefined,
        shared_by: sharedBy.trim() || undefined,
      });

      setSuccess(
        result.created
          ? `Saved "${result.name}" — score ${result.score_total?.toFixed(1) ?? "—"}`
          : `Updated existing entry for "${result.name}"`
      );
      resetForm();
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900/40">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
      >
        <div>
          <p className="font-medium text-white">Add opportunity</p>
          <p className="mt-0.5 text-sm text-zinc-400">
            Paste a tweet or link — appears in Scout, deadlines, and priorities.
          </p>
        </div>
        <span className="text-zinc-400">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <form onSubmit={handleSubmit} className="border-t border-zinc-800 px-5 py-4">
          <div className="space-y-4">
            <label className="block">
              <span className="text-sm text-zinc-300">Paste tweet or notes</span>
              <textarea
                value={paste}
                onChange={(e) => setPaste(e.target.value)}
                rows={4}
                placeholder="Paste the full tweet text — we'll extract links and deadlines…"
                className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-sky-500 focus:outline-none"
              />
            </label>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-sm text-zinc-300">Application URL</span>
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  placeholder="https://…"
                  className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-sky-500 focus:outline-none"
                />
              </label>

              <label className="block">
                <span className="text-sm text-zinc-300">Title</span>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Auto-detected from paste"
                  className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-sky-500 focus:outline-none"
                />
              </label>

              <label className="block">
                <span className="text-sm text-zinc-300">Category</span>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-sky-500 focus:outline-none"
                >
                  {CATEGORIES.map((opt) => (
                    <option key={opt.value || "auto"} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block">
                <span className="text-sm text-zinc-300">Deadline</span>
                <input
                  type="date"
                  value={deadline}
                  onChange={(e) => setDeadline(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-white focus:border-sky-500 focus:outline-none"
                />
              </label>

              <label className="block">
                <span className="text-sm text-zinc-300">Tweet URL (optional)</span>
                <input
                  type="url"
                  value={tweetUrl}
                  onChange={(e) => setTweetUrl(e.target.value)}
                  placeholder="https://x.com/…"
                  className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-sky-500 focus:outline-none"
                />
              </label>

              <label className="block">
                <span className="text-sm text-zinc-300">Shared by (optional)</span>
                <input
                  type="text"
                  value={sharedBy}
                  onChange={(e) => setSharedBy(e.target.value)}
                  placeholder="@handle"
                  className="mt-1 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-sky-500 focus:outline-none"
                />
              </label>
            </div>
          </div>

          {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
          {success && <p className="mt-3 text-sm text-emerald-400">{success}</p>}

          <div className="mt-4 flex gap-3">
            <button
              type="submit"
              disabled={busy || (!paste.trim() && !url.trim())}
              className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-sky-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {busy ? "Saving…" : "Save opportunity"}
            </button>
            <button
              type="button"
              onClick={() => {
                resetForm();
                setOpen(false);
              }}
              className="rounded-lg border border-zinc-700 px-4 py-2 text-sm text-zinc-300 transition hover:border-zinc-500"
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
