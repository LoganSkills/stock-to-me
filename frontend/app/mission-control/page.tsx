"use client";

import { useEffect, useState } from "react";
import { setTokenGetter } from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8765";

interface Agent {
  id: string;
  name: string;
  role: string;
  department: string;
  status: string;
  desk_x: number;
  desk_y: number;
  current_task: string | null;
  mission: string;
}

interface Meeting {
  id: string;
  type: string;
  topic: string;
  participants: string[];
}

const invaderSVG = (
  <svg viewBox="0 0 11 8" style={{ width: "100%", height: "100%" }}>
    <path
      fill="currentColor"
      d="M1 0h1v1h1v1h2V1h1V0h1v1h1v1h1v1h-1v1h-1v1h-1V4H5v1H4v1H3V4H2V3H1V2H0V1h1V0zm2 6h1v1h1v1H4V7H3V6z"
    />
  </svg>
);

const STATUS_COLORS: Record<string, string> = {
  active: "#00ff88",
  idle: "#ffaa00",
  busy: "#ff4444",
  offline: "#666",
};

const AGENT_COLORS: Record<string, string> = {
  alex: "#00ff88",
  jordan: "#00cc66",
  sam: "#00ccff",
  taylor: "#0099cc",
  morgan: "#ffaa00",
  casey: "#ff8800",
  riley: "#cc88ff",
  broker: "#ff6688",
};

export default function MissionControlPage() {
  const [agents, setAgents] = useState<Record<string, Agent>>({});
  const [tasks, setTasks] = useState<Record<string, unknown>>({});
  const [meetings, setMeetings] = useState<Record<string, Meeting>>({});
  const [logs, setLogs] = useState<Array<{ time: string; msg: string; type: string }>>([]);
  const [wsConnected, setWsConnected] = useState(false);

  const log = (msg: string, type: "info" | "warn" | "error" = "info") => {
    const time = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev.slice(-49), { time, msg, type }]);
  };

  // ── WebSocket ──────────────────────────────────────────────────────────────────

  useEffect(() => {
    let ws: WebSocket | null = null;

    function connect() {
      ws = new WebSocket(`ws://${window.location.host}/ws`);
      ws.onopen = () => {
        setWsConnected(true);
        log("WebSocket connected", "info");
      };
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "state_update") {
          setAgents((msg.data as { agents: Record<string, Agent> }).agents || {});
          setTasks((msg.data as { tasks: Record<string, unknown> }).tasks || {});
          setMeetings((msg.data as { meetings: Record<string, Meeting> }).meetings || {});
        }
      };
      ws.onclose = () => {
        setWsConnected(false);
        log("WebSocket disconnected — reconnecting in 3s", "warn");
        setTimeout(connect, 3000);
      };
    }

    connect();
    return () => ws?.close();
  }, []);

  // ── Helpers ─────────────────────────────────────────────────────────────────────

  const agentList = Object.values(agents);

  const counts = {
    active: agentList.filter((a) => a.status === "active").length,
    idle: agentList.filter((a) => a.status === "idle").length,
    busy: agentList.filter((a) => a.status === "busy").length,
  };

  const getMeetingLabel = (m: Meeting) =>
    m.type === "team"
      ? "Team Meeting"
      : m.type === "broker-research"
      ? "Broker → Research"
      : "Pair Meeting";

  const sendAction = async (
    action: string,
    params: Record<string, string> = {}
  ) => {
    try {
      const qs = new URLSearchParams({ action, ...params }).toString();
      await fetch(`${API_BASE}/api?${qs}`, { method: "POST" });
    } catch (_) {}
  };

  const startBrokerResearch = () => {
    sendAction("start_broker_research");
    log("Broker requested research collaboration with Sam + Taylor", "info");
  };

  const startTeamMeeting = async () => {
    const participants = ["alex", "jordan", "sam", "casey"].join(",");
    try {
      await fetch(
        `${API_BASE}/api/meetings?meeting_type=team&participants=${participants}&location=conference&topic=Sprint Planning`
      );
    } catch (_) {}
  };

  const createTask = async () => {
    const title = prompt("Task title:");
    if (!title) return;
    try {
      await fetch(
        `${API_BASE}/api/tasks?title=${encodeURIComponent(title)}&priority=1`
      );
    } catch (_) {}
  };

  // ── Render ───────────────────────────────────────────────────────────────────────

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", background: "#0a0a1a", color: "#fff", minHeight: "100vh" }}>
      {/* Header */}
      <div
        style={{
          background: "linear-gradient(180deg, #1a1a3a 0%, #0a0a1a 100%)",
          padding: "15px 30px",
          borderBottom: "2px solid #00ff88",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h1 style={{ fontSize: "1.5rem", color: "#00ff88", letterSpacing: "3px", margin: 0 }}>
          🎯 MISSION CONTROL — Stock To Me Edition
        </h1>
        <div style={{ display: "flex", gap: "20px", alignItems: "center", fontSize: "0.9rem" }}>
          <span style={{ color: "#00ff88" }}>
            ● {counts.active} Active
          </span>
          <span style={{ color: "#ffaa00" }}>
            ● {counts.idle} Idle
          </span>
          <span style={{ color: "#ff4444" }}>
            ● {counts.busy} Busy
          </span>
          <span
            style={{
              background: wsConnected ? "#00ff88" : "#ff4444",
              color: "#000",
              padding: "5px 15px",
              borderRadius: "20px",
              fontWeight: "bold",
              fontSize: "0.8rem",
            }}
          >
            {wsConnected ? "● LIVE" : "OFFLINE"}
          </span>
        </div>
      </div>

      {/* Main layout */}
      <div style={{ display: "flex", height: "calc(100vh - 70px)" }}>
        {/* Office canvas */}
        <div
          style={{
            flex: 1,
            position: "relative",
            background: "linear-gradient(180deg, #1a1a2e 0%, #0f0f1a 100%)",
            overflow: "hidden",
          }}
        >
          {/* Grid */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundImage:
                "linear-gradient(90deg, rgba(0,255,136,0.03) 1px, transparent 1px), linear-gradient(rgba(0,255,136,0.03) 1px, transparent 1px)",
              backgroundSize: "40px 40px",
              pointerEvents: "none",
            }}
          />

          {/* Department zone labels */}
          <div style={{ position: "absolute", top: 20, left: 50, fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "2px", color: "#00ffff", fontWeight: 600 }}>
            Development
          </div>
          <div style={{ position: "absolute", top: 20, right: 50, fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "2px", color: "#00ffff", fontWeight: 600 }}>
            Research
          </div>
          <div style={{ position: "absolute", bottom: 120, left: 50, fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "2px", color: "#ff6688", fontWeight: 600 }}>
            Trading
          </div>
          <div style={{ position: "absolute", bottom: 120, left: 300, fontSize: "0.7rem", textTransform: "uppercase", letterSpacing: "2px", color: "#ffaa00", fontWeight: 600 }}>
            Operations
          </div>

          {/* Conference table */}
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              width: 250,
              height: 150,
              background: "linear-gradient(145deg, #2a2a4a 0%, #1a1a3a 100%)",
              borderRadius: 15,
              border: `2px solid ${Object.keys(meetings).length > 0 ? "#00ff88" : "#3a3a5a"}`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow:
                Object.keys(meetings).length > 0
                  ? "0 0 30px rgba(0,255,136,0.2)"
                  : "none",
            }}
          >
            <span style={{ fontSize: "0.7rem", letterSpacing: "2px", color: "rgba(0,255,136,0.3)" }}>
              CONFERENCE
            </span>
          </div>

          {/* PM Office label */}
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -240px)",
              fontSize: "0.65rem",
              textTransform: "uppercase",
              letterSpacing: "2px",
              color: "#cc88ff",
              fontWeight: 600,
            }}
          >
            Management
          </div>

          {/* Agents & Desks */}
          {agentList.map((agent) => {
            const isBroker = agent.id === "broker";
            const isPM = agent.id === "riley";
            const color = AGENT_COLORS[agent.id] || "#00ff88";
            return (
              <div key={agent.id}>
                {/* Desk */}
                <div
                  style={{
                    position: "absolute",
                    left: agent.desk_x,
                    top: agent.desk_y,
                    width: isBroker || isPM ? 140 : 120,
                    height: isBroker || isPM ? 70 : 80,
                    background: `linear-gradient(145deg, #2a2a4a 0%, #1a1a3a 100%)`,
                    borderRadius: 4,
                    border: `1px solid ${agent.status === "busy" ? color : "#3a3a5a"}`,
                    boxShadow:
                      agent.status === "busy"
                        ? `0 0 20px ${color}40`
                        : "0 4px 8px rgba(0,0,0,0.5)",
                  }}
                />
                {/* Agent */}
                <div
                  style={{
                    position: "absolute",
                    left: agent.desk_x + (isBroker || isPM ? 52 : 42),
                    top: agent.desk_y + 22,
                    width: 36,
                    height: 36,
                    color: STATUS_COLORS[agent.status] || "#666",
                    cursor: "pointer",
                    transition: "transform 0.3s",
                  }}
                >
                  {invaderSVG}
                </div>
                {/* Label */}
                <div
                  style={{
                    position: "absolute",
                    left: agent.desk_x + 5,
                    top: (isBroker || isPM ? agent.desk_y + 75 : agent.desk_y + 85),
                    fontSize: "0.7rem",
                    color: "#aaa",
                    background: "rgba(0,0,0,0.8)",
                    padding: "2px 6px",
                    borderRadius: 4,
                    whiteSpace: "nowrap",
                  }}
                >
                  {agent.name}{" "}
                  <span style={{ color }}>
                    ({agent.role.split(" ")[0]})
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Side panel */}
        <div
          style={{
            width: 350,
            background: "#0f0f1a",
            borderLeft: "1px solid #2a2a4a",
            display: "flex",
            flexDirection: "column",
            overflowY: "auto",
          }}
        >
          {/* Active Tasks */}
          <div style={{ padding: 20, borderBottom: "1px solid #1a1a3a" }}>
            <h3 style={{ color: "#00ff88", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "2px", marginBottom: 15 }}>
              📋 Active Tasks
            </h3>
            <div style={{ maxHeight: 180, overflowY: "auto" }}>
              {Object.values(tasks).length === 0 ? (
                <p style={{ color: "#666", fontSize: "0.85rem" }}>No active tasks</p>
              ) : (
                Object.values(tasks).map((task: unknown) => (
                  <div
                    key={(task as { id: string }).id}
                    style={{
                      background: "#1a1a3a",
                      padding: "10px",
                      marginBottom: 8,
                      borderRadius: 4,
                      borderLeft: `3px solid ${
                        (task as { status: string }).status === "in-progress" ? "#00ff88" : "#ffaa00"
                      }`,
                    }}
                  >
                    <div style={{ color: "#fff", fontSize: "0.85rem" }}>
                              {(task as { title: string }).title}
                    </div>
                    <div style={{ color: "#666", fontSize: "0.75rem", marginTop: 4 }}>
                              {(task as { assigned_to: string }).assigned_to
                                ? `👤 ${(task as { assigned_to: string }).assigned_to}`
                                : "Unassigned"}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Meetings */}
          <div style={{ padding: 20, borderBottom: "1px solid #1a1a3a" }}>
            <h3 style={{ color: "#00ff88", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "2px", marginBottom: 15 }}>
              🤝 Active Meetings
            </h3>
            <div style={{ maxHeight: 150, overflowY: "auto" }}>
              {Object.values(meetings).length === 0 ? (
                <p style={{ color: "#666", fontSize: "0.85rem" }}>No active meetings</p>
              ) : (
                Object.values(meetings).map((m) => (
                  <div key={m.id} style={{ background: "#1a1a3a", padding: 10, marginBottom: 8, borderRadius: 4 }}>
                    <div style={{ color: "#00ff88", fontSize: "0.75rem", textTransform: "uppercase" }}>
                              {getMeetingLabel(m)}
                    </div>
                    <div style={{ color: "#fff", fontSize: "0.85rem", margin: "4px 0" }}>
                              {m.topic}
                    </div>
                    <div style={{ color: "#666", fontSize: "0.75rem" }}>
                              {m.participants.map((p) => agents[p]?.name || p).join(", ")}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Broker Actions */}
          <div style={{ padding: 20, borderBottom: "1px solid #1a1a3a" }}>
            <h3 style={{ color: "#ff6688", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "2px", marginBottom: 15 }}>
              📈 Broker Actions
            </h3>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <button
                onClick={startBrokerResearch}
                style={{
                  background: "#1a1a3a",
                  border: "1px solid #ff6688",
                  color: "#ff6688",
                  padding: "8px 15px",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: "0.85rem",
                }}
              >
                🔬 Request Research Analysis
              </button>
              <button
                onClick={() => log("Broker analyzing: CRSP small-cap universe + EDGAR S-1 filings", "info")}
                style={{
                  background: "#1a1a3a",
                  border: "1px solid #3a3a5a",
                  color: "#ccc",
                  padding: "8px 15px",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: "0.85rem",
                }}
              >
                📊 Scan Small-Cap Universe
              </button>
              <button
                onClick={() => log("Broker: Flagged 3 high-trap-score names for review", "info")}
                style={{
                  background: "#1a1a3a",
                  border: "1px solid #3a3a5a",
                  color: "#ccc",
                  padding: "8px 15px",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: "0.85rem",
                }}
              >
                🚨 View Trap Score Alerts
              </button>
            </div>
          </div>

          {/* Quick Actions */}
          <div style={{ padding: 20, borderBottom: "1px solid #1a1a3a" }}>
            <h3 style={{ color: "#00ff88", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "2px", marginBottom: 15 }}>
              ⚡ Quick Actions
            </h3>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button
                onClick={startTeamMeeting}
                style={{
                  background: "#1a1a3a",
                  border: "1px solid #3a3a5a",
                  color: "#fff",
                  padding: "8px 15px",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: "0.8rem",
                }}
              >
                Team Meeting
              </button>
              <button
                onClick={createTask}
                style={{
                  background: "#1a1a3a",
                  border: "1px solid #3a3a5a",
                  color: "#fff",
                  padding: "8px 15px",
                  borderRadius: 4,
                  cursor: "pointer",
                  fontSize: "0.8rem",
                }}
              >
                New Task
              </button>
            </div>
          </div>

          {/* System Log */}
          <div style={{ flex: 1, padding: 20, overflowY: "auto" }}>
            <h3 style={{ color: "#00ff88", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "2px", marginBottom: 15 }}>
              📜 System Log
            </h3>
            <div style={{ fontFamily: "'Courier New', monospace", fontSize: "0.75rem" }}>
              {logs.map((entry, i) => (
                <div
                  key={i}
                  style={{
                    marginBottom: 5,
                    color:
                      entry.type === "info"
                        ? "#00ff88"
                        : entry.type === "warn"
                        ? "#ffaa00"
                        : "#ff4444",
                  }}
                >
                  <span style={{ color: "#4a4a6a" }}>[{entry.time}]</span> {entry.msg}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
