"""Mission Control server — serves the live office floor at port 8765."""

import json
import asyncio
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

app = FastAPI(title="Mission Control", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            "desk_x": 1110, "desk_y": 500,
            "current_task": "Scanning for high-trap setups",
            "mission": "trading"
        },
    },
    "tasks": {},
    "meetings": {},
}

tasks_counter = 0
meetings_counter = 0
websockets: list[WebSocket] = []


# ─── Resolve the correct static directory ────────────────────────────────────────

def _static_dir() -> Path:
    """Find frontend/public relative to this script."""
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent  # scripts/ → stock-to-me/
    static_dir = project_root / "frontend" / "public"
    if static_dir.exists():
        return static_dir
    # Fallback: serve from project root
    return project_root


# ─── Redirect / to office-floor-live.html ───────────────────────────────────────

@app.get("/")
def root():
    static_dir = _static_dir()
    index_path = static_dir / "office-floor-live.html"
    if index_path.exists():
        return RedirectResponse(url="/office-floor-live.html")
    return {
        "app": "Mission Control",
        "version": "1.0.0",
        "note": "office-floor-live.html not found. Run this script from the stock-to-me directory.",
        "static_dir": str(static_dir),
    }


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

async def broadcast(data: dict):
    msg = json.dumps(data)
    for ws in websockets[:]:
        try:
            await ws.send_text(msg)
        except Exception:
            websockets.remove(ws)


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

static_dir = _static_dir()
print(f"Serving static files from: {static_dir}")
app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print("🚀 Mission Control running at http://localhost:8765")
    print(f"   Static files: {static_dir}")
    uvicorn.run(app, host="0.0.0.0", port=8765)
