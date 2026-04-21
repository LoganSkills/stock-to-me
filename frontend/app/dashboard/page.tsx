"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TopTrapsCard, NewFilingsCard, OverviewCards } from "@/components/cards";
import type { DashboardOverview, TopTrapItem } from "@/types";

export default function DashboardPage() {
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [topTraps, setTopTraps] = useState<TopTrapItem[]>([]);
  const [newFilings, setNewFilings] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.getDashboardOverview(),
      api.getTopTraps(20),
      api.getNewFilings(20),
    ])
      .then(([ov, traps, filings]) => {
        setOverview(ov);
        setTopTraps(traps);
        setNewFilings(filings);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Loading dashboard…</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Stock To Me — small-cap intelligence
        </p>
      </div>

      {overview && <OverviewCards overview={overview as unknown as Record<string, unknown>} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TopTrapsCard items={topTraps} />
        <NewFilingsCard items={newFilings} />
      </div>

      <div className="bg-white rounded-lg border p-4">
        <h2 className="text-lg font-semibold mb-3">Trap Score Breakdown</h2>
        {overview && (
          <div className="flex gap-4 flex-wrap">
            {Object.entries((overview as unknown as Record<string, number>).trap_score_breakdown || {}).map(
              ([label, count]) => (
                <div key={label} className="flex items-center gap-2">
                  <span className="text-sm">{label}</span>
                  <span className="font-bold">{count}</span>
                </div>
              )
            )}
          </div>
        )}
      </div>
    </div>
  );
}
