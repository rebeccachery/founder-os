import Link from "next/link";

const links = [
  { href: "/", label: "Overview" },
  { href: "/scout", label: "Scout" },
  { href: "/oss", label: "OSS" },
  { href: "/social", label: "Social" },
  { href: "/investors", label: "Investors" },
  { href: "/assistant", label: "Assistant" },
];

export function Nav() {
  return (
    <nav className="border-b border-zinc-800 bg-zinc-900/50">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight text-white">
          Founder OS
        </Link>
        <div className="flex flex-wrap gap-4 text-sm">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="text-zinc-400 transition hover:text-white"
            >
              {link.label}
            </Link>
          ))}
        </div>
      </div>
    </nav>
  );
}
