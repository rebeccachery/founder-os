import Link from "next/link";

export function ScoutSourceFilter({ active }: { active: "all" | "manual" | "agent" }) {
  const tabs = [
    { id: "all" as const, label: "All", href: "/scout" },
    { id: "manual" as const, label: "My saves", href: "/scout?source=manual" },
    { id: "agent" as const, label: "Agent-found", href: "/scout?source=agent" },
  ];

  return (
    <div className="flex gap-2">
      {tabs.map((tab) => (
        <Link
          key={tab.id}
          href={tab.href}
          className={`rounded-full px-3 py-1 text-sm transition ${
            active === tab.id
              ? "bg-sky-500/20 text-sky-300"
              : "text-zinc-400 hover:bg-zinc-800 hover:text-white"
          }`}
        >
          {tab.label}
        </Link>
      ))}
    </div>
  );
}
