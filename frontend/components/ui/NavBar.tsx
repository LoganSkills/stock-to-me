"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/alerts", label: "Alerts" },
];

export default function NavBar() {
  const pathname = usePathname();
  return (
    <nav className="border-b bg-white px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-6">
        <Link href="/dashboard" className="font-bold text-lg">
          Stock To Me
        </Link>
        {NAV.map((n) => (
          <Link
            key={n.href}
            href={n.href}
            className={`text-sm ${pathname === n.href ? "font-semibold text-primary" : "text-muted-foreground hover:text-foreground"}`}
          >
            {n.label}
          </Link>
        ))}
      </div>
      <div className="flex items-center gap-4">
        <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
          Sign Out
        </Link>
      </div>
    </nav>
  );
}
