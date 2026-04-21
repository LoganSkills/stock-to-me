"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import Link from "next/link";
import type { Alert } from "@/types";

const SEVERITY_COLORS: Record<string, string> = {
  info: "bg-blue-50 text-blue-700",
  caution: "bg-yellow-50 text-yellow-700",
  high: "bg-orange-50 text-orange-700",
  severe: "bg-red-50 text-red-800 font-bold",
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  const load = () =>
    api.getAlerts(false, 50).then(setAlerts).catch(console.error).finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  if (loading) {
    return <div className="flex items-center justify-center h-64"><p className="text-muted-foreground">Loading…</p></div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Alerts</h1>
        <button onClick={load} className="text-sm text-muted-foreground hover:text-foreground">
          ↻ Refresh
        </button>
      </div>

      {alerts.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">No alerts. You're all clear.</div>
      ) : (
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`rounded-lg border p-4 ${SEVERITY_COLORS[alert.severity] || ""}`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="font-semibold text-sm">{alert.title}</p>
                  <p className="text-sm mt-1 opacity-80">{alert.body}</p>
                  <p className="text-xs mt-2 opacity-60">
                    {new Date(alert.triggered_at).toLocaleString()} · {alert.alert_type}
                  </p>
                </div>
                {!alert.is_read && (
                  <button
                    onClick={() => api.markAlertRead(alert.id).then(load)}
                    className="text-xs px-2 py-1 bg-white border rounded hover:bg-gray-50 ml-4"
                  >
                    Mark read
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
