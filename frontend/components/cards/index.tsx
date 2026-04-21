"use client";

import Link from "next/link";
import { TRAP_LABELS, trapLabel, formatMarketCap } from "@/types";
import type { TopTrapItem } from "@/types";

interface Props {
  items: TopTrapItem[];
}

function TrapBadge({ score }: { score: number }) {
  const label = trapLabel(score);
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${TRAP_LABELS[label]}`}>
      {label}
    </span>
  );
}

export function TopTrapsCard({ items }: Props) {
  return (
    <div className="bg-white rounded-lg border p-4">
      <h2 className="text-lg font-semibold mb-3">Top Trap Scores</h2>
      {items.length === 0 ? (
        <p className="text-sm text-muted-foreground">No data yet. Run a scan to populate.</p>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <Link
              key={item.ticker}
              href={`/stocks/${item.ticker}`}
              className="flex items-center justify-between p-2 rounded hover:bg-muted transition"
            >
              <div>
                <span className="font-mono font-bold text-sm">{item.ticker}</span>
                <span className="text-xs text-muted-foreground ml-2">{item.name}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-xs text-muted-foreground">
                  DP {item.dilution_pressure_score.toFixed(0)}
                </span>
                <span className="text-xs text-muted-foreground">
                  CN {item.cash_need_score.toFixed(0)}
                </span>
                <span className="font-bold text-sm w-8 text-right">
                  {item.trap_score.toFixed(0)}
                </span>
                <TrapBadge score={item.trap_score} />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function NewFilingsCard({ items }: { items: unknown[] }) {
  if (!items || items.length === 0) {
    return (
      <div className="bg-white rounded-lg border p-4">
        <h2 className="text-lg font-semibold mb-3">New Filings</h2>
        <p className="text-sm text-muted-foreground">No recent filings.</p>
      </div>
    );
  }
  return (
    <div className="bg-white rounded-lg border p-4">
      <h2 className="text-lg font-semibold mb-3">New Filings (7d)</h2>
      <div className="space-y-2">
        {(items as Array<{ ticker: string; name: string; filing_type: string; filed_at: string; tags: string[] }>).map((f, i) => (
          <Link
            key={i}
            href={`/stocks/${f.ticker}`}
            className="flex items-center justify-between p-2 rounded hover:bg-muted transition"
          >
            <div>
              <span className="font-mono text-sm">{f.ticker}</span>
              <span className="text-xs text-muted-foreground ml-2">{f.filing_type}</span>
            </div>
            <div className="text-xs text-muted-foreground">
              {new Date(f.filed_at).toLocaleDateString()}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function OverviewCards({ overview }: { overview: Record<string, unknown> }) {
  const cards = [
    { label: "Companies Tracked", value: (overview as { total_companies: number }).total_companies ?? "—" },
    { label: "High Risk Names", value: (overview as { high_trap_count: number }).high_trap_count ?? "—" },
    { label: "New Filings Today", value: (overview as { new_filings_today: number }).new_filings_today ?? "—" },
    { label: "Active Alerts", value: (overview as { active_alerts: number }).active_alerts ?? "—" },
  ];
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div key={c.label} className="bg-white rounded-lg border p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">{c.label}</p>
          <p className="text-2xl font-bold mt-1">{c.value}</p>
        </div>
      ))}
    </div>
  );
}

interface ScoreCardProps {
  label: string;
  value: number;
  description?: string;
}

export function ScoreCard({ label, value, description }: ScoreCardProps) {
  const pct = Math.round(value);
  let color = "bg-green-500";
  if (pct >= 85) color = "bg-red-700";
  else if (pct >= 70) color = "bg-red-500";
  else if (pct >= 50) color = "bg-orange-500";
  else if (pct >= 25) color = "bg-yellow-500";

  return (
    <div className="bg-white rounded-lg border p-4">
      <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
      <div className="flex items-end gap-2 mt-2">
        <span className="text-2xl font-bold">{pct}</span>
        <span className="text-xs text-muted-foreground mb-1">/100</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-1.5 mt-2">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
      {description && <p className="text-xs text-muted-foreground mt-2">{description}</p>}
    </div>
  );
}
