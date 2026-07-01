"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { deleteAssistantTrack, upsertAssistantTrack } from "@/lib/api";

export function ScoutTrackButton({
  opportunityId,
  tracked,
}: {
  opportunityId: number;
  tracked: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setBusy(true);
    setError(null);
    try {
      if (tracked) {
        await deleteAssistantTrack(opportunityId);
      } else {
        await upsertAssistantTrack(opportunityId, { track_application: true });
      }
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <span className="inline-flex flex-col items-start gap-0.5">
      <button
        type="button"
        disabled={busy}
        onClick={handleClick}
        className={`rounded px-2 py-0.5 text-xs font-medium transition disabled:opacity-50 ${
          tracked
            ? "bg-emerald-500/15 text-emerald-400"
            : "bg-zinc-800 text-zinc-400 hover:text-white"
        }`}
      >
        {busy ? "…" : tracked ? "Tracked" : "Track"}
      </button>
      {error && <span className="text-xs text-red-400">{error}</span>}
    </span>
  );
}
