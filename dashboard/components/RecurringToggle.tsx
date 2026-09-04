"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { updateScoutRecurring } from "@/lib/api";

export function RecurringToggle({
  opportunityId,
  isRecurring,
}: {
  opportunityId: number;
  isRecurring: boolean;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    setBusy(true);
    setError(null);
    try {
      await updateScoutRecurring(opportunityId, !isRecurring);
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
        title="Mark as an evergreen/rolling program so it's never treated as expired"
        className={`rounded px-2 py-0.5 text-xs font-medium transition disabled:opacity-50 ${
          isRecurring
            ? "bg-violet-500/15 text-violet-300"
            : "bg-zinc-800 text-zinc-400 hover:text-white"
        }`}
      >
        {busy ? "…" : isRecurring ? "Recurring" : "Mark recurring"}
      </button>
      {error && <span className="text-xs text-red-400">{error}</span>}
    </span>
  );
}
