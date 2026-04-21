"""Mission Control server — provides the /api/state, /api/meetings, /api/tasks endpoints
and a WebSocket broadcast channel for the live office floor."""

import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Response

app = FastAPI(title="Mission Control", version="1.0.0")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ─── In-memory state ──────────────────────────────────────────────────────────────

state = {
    "agents": {
        "alex": {
            "id": "alex", "name": "Alex", "role": "Senior Developer",
            "department": "Development", "status": "active",
            "desk_x": 50, "desk_y": 60,
            "current_task": "Building Stock To Me dashboard",
            "mission": "frontend"
        },
        "jordan": {
            "id": "jordan", "name": "Jordan", "role": "Code Reviewer",
            "department": "Development", "status": "active",
            "desk_x": 190, "desk_y": 60,
            "current_task": "Reviewing SEC ingestion service",
            "mission": "frontend"
        },
        "sam": {
            "id": "sam", "name": "Sam", "role": "Research Lead",
            "department": "Research", "status": "active",
            "desk_x": 1110, "desk_y": 60,
            "current_task": "Researching EDGAR API patterns",
            "mission": "intelligence"
        },
        "taylor": {
            "id": "taylor", "name": "Taylor", "role": "Data Analyst",
            "department": "Research", "status": "idle",
            "desk_x": 1270, "desk_y": 60,
            "current_task": None,
            "mission": "intelligence"
        },
        "morgan": {
            "id": "morgan", "name": "Morgan", "role": "Tracker",
            "department": "Operations", "status": "idle",
            "desk_x": 50, "desk_y": 500,
            "current_task": None,
            "mission": "operations"
        },
        "casey": {
            "id": "casey", "name": "Casey", "role": "Accountant",
            "department": "Operations", "status": "active",
            "desk_x": 190, "desk_y": 500,
            "current_task": "Setting up expense categories",
            "mission": "operations"
        },
        "riley": {
            "id": "riley", "name": "Riley", "role": "Project Manager",
            "department": "Management", "status": "active",
            "desk_x": 630, "desk_y": 300,
            "current_task": "Coordinating Stock To Me build",
            "mission": "management"
        },
        "broker": {
            "id": "broker", "name": "Broker", "role": "Stock Broker",
            "department": "Trading", "status": "active",
            "desk_x": 420, "desk_y": 500,
            "current_task": "Analyzing small-cap setups",
            "mission": "trading"
        },
    },
    "tasks": {},
    "meetings": {},
}

tasks_counter = 0
meetings_counter = 0
websockets: list[WebSocket] = []


# ─── WebSocket broadcast ───────────────────────────────────────────────────────

async def broadcast(data: dict):
    msg = json.dumps(data)
    for ws in websockets[:]:
        try:
            await ws.send_text(msg)
        except Exception:
            websockets.remove(ws)


# ─── REST endpoints ────────────────────────────────────────────────────────────


@app.get("/api/state")
def get_state():
    return state


@app.post("/api/tasks")
def create_task(title: str = "", priority: int = 1, assigned_to: str = ""):
    global tasks_counter
    tasks_counter += 1
    tid = f"task{tasks_counter}"
    state["tasks"][tid] = {
        "id": tid,
        "title": title,
        "priority": priority,
        "assigned_to": assigned_to or None,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    asyncio.create_task(broadcast({"type": "state_update", "data": state}))
    return state["tasks"][tid]


@app.post("/api/meetings")
def create_meeting(
    meeting_type: str = "pair",
    participants: str = "",
    location: str = "conference",
    topic: str = "",
):
    global meetings_counter
    meetings_counter += 1
    mid = f"meet{meetings_counter}"
    parts = [p.strip() for p in participants.split(",") if p.strip()]
    state["meetings"][mid] = {
        "id": mid,
        "type": meeting_type,
        "topic": topic,
        "location": location,
        "participants": parts,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }
    asyncio.create_task(broadcast({"type": "state_update", "data": state}))
    return state["meetings"][mid]


@app.delete("/api/meetings/{meeting_id}")
def end_meeting(meeting_id: str):
    if meeting_id in state["meetings"]:
        del state["meetings"][meeting_id]
        asyncio.create_task(broadcast({"type": "state_update", "data": state}))
    return {"ok": True}


@app.patch("/api/agents/{agent_id}")
def update_agent(agent_id: str, status: str = None, current_task: str = None):
    if agent_id in state["agents"]:
        if status:
            state["agents"][agent_id]["status"] = status
        if current_task is not None:
            state["agents"][agent_id]["current_task"] = current_task
        asyncio.create_task(broadcast({"type": "state_update", "data": state}))
    return state["agents"].get(agent_id)


# ─── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    websockets.append(ws)
    try:
        await ws.send_json({"type": "state_update", "data": state})
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("action") == "update_agent":
                    aid = msg.get("agent_id")
                    if aid in state["agents"]:
                        if "status" in msg:
                            state["agents"][aid]["status"] = msg["status"]
                        if "current_task" in msg:
                            state["agents"][aid]["current_task"] = msg["current_task"]
                        await broadcast({"type": "state_update", "data": state})
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        websockets.remove(ws)


# ─── Static serving ─────────────────────────────────────────────────────────────

app.mount("/", StaticFiles(directory=".", html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
