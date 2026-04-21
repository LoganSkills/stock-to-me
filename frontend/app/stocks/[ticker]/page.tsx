"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { ScoreCard } from "@/components/cards";
import { trapLabel, formatMarketCap, formatShares, TRAP_LABELS } from "@/types";
import type { CompanyDetailOut, ScoreSnapshot, Filing, TimelineEvent, DilutionImpact } from "@/types";
import { formatDistanceToNow } from "date-fns";

interface Props {
  params: Promise<{ ticker: string }>;
}

export default function StockDetailPage({ params }: Props) {
  const { ticker } = use(params);
  const [company, setCompany] = useState<CompanyDetailOut | null>(null);
  const [scores, setScores] = useState<ScoreSnapshot | null>(null);
  const [filings, setFilings] = useState<Filing[]>([]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([]);
  const [dilution, setDilution] = useState<DilutionImpact | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const t = ticker.toUpperCase();
    Promise.all([
      api.getStock(t),
      api.getStockScores(t),
      api.getStockFilings(t, 20),
      api.getStockTimeline(t),
      api.getDilutionImpact(t),
    ])
      .then(([co, sc, fi, tl, di]) => {
        setCompany(co);
        setScores(sc);
        setFilings(fi);
        setTimeline(tl.events || []);
        setDilution(di);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [ticker]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Loading {ticker}…</p>
      </div>
    );
  }

  if (!company) {
    return (
      <div className="text-center py-20">
        <p className="text-lg">Ticker not found: {ticker}</p>
        <Link href="/dashboard" className="text-primary hover:underline mt-2 inline-block">
          ← Back to Dashboard
        </Link>
      </div>
    );
  }

  const label = scores ? trapLabel(scores.trap_score) : "—";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold font-mono">{company.ticker}</h1>
            {scores && (
              <span className={`px-3 py-1 rounded text-sm font-semibold ${TRAP_LABELS[label]}`}>
                {label}
              </span>
            )}
          </div>
          <p className="text-muted-foreground mt-1">{company.name}</p>
          <p className="text-xs text-muted-foreground">
            {company.exchange} · {company.sector || "—"} · {company.industry || "—"}
          </p>
        </div>
        <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
          ← Dashboard
        </Link>
      </div>

      {/* Key Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Market Cap", value: formatMarketCap(company.market_cap) },
          { label: "Price", value: company.current_price ? `$${company.current_price.toFixed(2)}` : "—" },
          { label: "Float", value: formatShares(company.float_shares) },
          { label: "Shares Out", value: formatShares(company.shares_outstanding) },
        ].map((s) => (
          <div key={s.label} className="bg-white rounded-lg border p-4">
            <p className="text-xs text-muted-foreground uppercase">{s.label}</p>
            <p className="text-xl font-bold mt-1">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Score Cards */}
      {scores && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <ScoreCard label="Trap Score" value={scores.trap_score} />
          <ScoreCard label="Dilution Pressure" value={scores.dilution_pressure_score} />
          <ScoreCard label="Cash Need" value={scores.cash_need_score} />
          <ScoreCard label="Pump Setup" value={scores.pump_setup_score} />
          <ScoreCard label="Timing Urgency" value={scores.timing_urgency_score} />
        </div>
      )}

      {/* AI Summary */}
      {scores?.ai_summary && (
        <div className="bg-primary/5 border border-primary/20 rounded-lg p-4">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-primary mb-2">AI Summary</h2>
          <p className="text-sm leading-relaxed">{scores.ai_summary}</p>
        </div>
      )}

      {/* Dilution Impact */}
      {dilution && (dilution.immediate_dilution_pct || dilution.theoretical_price) && (
        <div className="bg-white rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-3">Dilution Impact</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {dilution.immediate_dilution_pct !== null && (
              <div>
                <p className="text-xs text-muted-foreground">Immediate Dilution</p>
                <p className="text-xl font-bold text-orange-600">
                  {dilution.immediate_dilution_pct.toFixed(1)}%
                </p>
              </div>
            )}
            {dilution.potential_total_dilution_pct !== null && (
              <div>
                <p className="text-xs text-muted-foreground">Potential Total</p>
                <p className="text-xl font-bold text-red-600">
                  {dilution.potential_total_dilution_pct.toFixed(1)}%
                </p>
              </div>
            )}
            {dilution.theoretical_price !== null && (
              <div>
                <p className="text-xs text-muted-foreground">Theoretical Price</p>
                <p className="text-xl font-bold">
                  ${dilution.theoretical_price.toFixed(3)}
                </p>
              </div>
            )}
            {dilution.theoretical_price_severe !== null && (
              <div>
                <p className="text-xs text-muted-foreground">Stressed Range</p>
                <p className="text-xl font-bold text-red-700">
                  ${dilution.theoretical_price_severe.toFixed(3)}
                </p>
              </div>
            )}
          </div>
          {dilution.warrant_overhang_notes && (
            <p className="text-sm text-muted-foreground mt-3 italic">{dilution.warrant_overhang_notes}</p>
          )}
          <p className="text-xs text-muted-foreground mt-2">
            * Theoretical price assumes market cap stays constant. Illustrative estimate only.
          </p>
        </div>
      )}

      {/* Timeline */}
      {timeline.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-3">Company Timeline (90d)</h2>
          <div className="space-y-2">
            {timeline.map((evt, i) => (
              <div key={i} className="flex items-start gap-3 text-sm">
                <div className="w-24 shrink-0 text-xs text-muted-foreground mt-0.5">
                  {formatDistanceToNow(new Date(evt.timestamp), { addSuffix: true })}
                </div>
                <div>
                  <span className="font-medium">{evt.label}</span>
                  {evt.detail && <span className="text-muted-foreground"> — {evt.detail}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Filings */}
      {filings.length > 0 && (
        <div className="bg-white rounded-lg border p-4">
          <h2 className="text-lg font-semibold mb-3">Recent Filings</h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-muted-foreground border-b">
                <th className="pb-2">Type</th>
                <th className="pb-2">Filed</th>
                <th className="pb-2">Tags</th>
              </tr>
            </thead>
            <tbody>
              {filings.map((f) => (
                <tr key={f.id} className="border-b last:border-0">
                  <td className="py-2 font-medium">{f.filing_type}</td>
                  <td className="py-2 text-muted-foreground">
                    {new Date(f.filed_at).toLocaleDateString()}
                  </td>
                  <td className="py-2">
                    <div className="flex gap-1 flex-wrap">
                      {f.tags.map((t) => (
                        <span
                          key={t.id}
                          className="px-2 py-0.5 bg-muted rounded text-xs"
                          title={t.tag_value_text || String(t.tag_value_num || "")}
                        >
                          {t.tag_name}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Disclaimer */}
      <p className="text-xs text-muted-foreground border-t pt-4">
        <strong>Disclaimer:</strong> Stock To Me presents structured risk signals and historical pattern
        information only. Nothing here is a guarantee of price movement, manipulation, or future
        performance. All estimates are illustrative. Not financial advice.
      </p>
    </div>
  );
}
