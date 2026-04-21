"""
Broker Notification Service — routes Broker alerts to connected channels.

Supports multiple delivery channels (can be enabled simultaneously):
  - E*TRADE watchlist signals (placeholder — no auto-trading)
  - Telegram (via OpenClaw — user already has it configured)
  - Email (via SMTP / Gmail integration)
  - Webhook (TradingView, Zapier, etc.)
  - Mission Control log (always enabled)

Usage:
  from scripts.broker_notifications import BrokerAlert, send_broker_alert
  send_broker_alert(BrokerAlert(ticker="ZD", severity="high", message="..."))
"""

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pathlib import Path
import json

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import get_settings

settings = get_settings()


# ─── Alert types ───────────────────────────────────────────────────────────────

class AlertSeverity(str, Enum):
    INFO = "info"
    CAUTION = "caution"
    HIGH = "high"
    SEVERE = "severe"


class AlertPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BrokerAlert:
    ticker: str
    severity: AlertSeverity
    message: str
    trap_score: Optional[float] = None
    dilution_pct: Optional[float] = None
    offering_price: Optional[float] = None
    shares_offered: Optional[int] = None
    source: str = "Stock To Me"
    priority: AlertPriority = AlertPriority.NORMAL

    def formatted_message(self) -> str:
        parts = [
            f"📈 {self.ticker}",
            f"Severity: {self.severity.value.upper()}",
            self.message,
        ]
        if self.trap_score is not None:
            parts.append(f"Trap Score: {self.trap_score:.0f}/100")
        if self.dilution_pct is not None:
            parts.append(f"Immediate Dilution: {self.dilution_pct:.1f}%")
        return " | ".join(parts)


# ─── Mission Control logger (always runs) ────────────────────────────────────

def log_to_mission_control(alert: BrokerAlert) -> None:
    """Log to the Mission Control state file for the live floor."""
    state_file = Path(__file__).parent.parent / "broker_status.json"
    state = {"last_alert": None, "alerts_today": 0, "last_updated": None}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except Exception:
            pass

    state["last_alert"] = {
        "ticker": alert.ticker,
        "severity": alert.severity.value,
        "message": alert.message,
        "trap_score": alert.trap_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    state["alerts_today"] = state.get("alerts_today", 0) + 1
    state["last_updated"] = datetime.now(timezone.utc).isoformat()

    state_file.write_text(json.dumps(state, indent=2))
    print(f"[Broker] 🚨 {alert.formatted_message()}")


# ─── E*TRADE ──────────────────────────────────────────────────────────────────────

def send_to_etrade(alert: BrokerAlert) -> bool:
    """Send alert to E*TRADE as a watchlist signal."""
    try:
        from scripts.etrade_service import get_client
        client = get_client()
        if not client:
            return False
        client.send_alert(alert.ticker, alert.formatted_message())
        return True
    except Exception as e:
        print(f"[Broker] E*TRADE error: {e}")
        return False


# ─── Telegram (via OpenClaw) ──────────────────────────────────────────────────

async def send_to_telegram(alert: BrokerAlert) -> bool:
    """
    Send alert to Telegram via OpenClaw messaging.
    Requires openclaw channels configured and a Telegram bot token.
    """
    try:
        from app.core.security import get_current_user
        # This requires the bot to be configured — handled by OpenClaw natively
        # We use the message tool through the sessions system
        return False  # placeholder — use sessions_send or message tool directly
    except Exception:
        return False


# ─── Webhook ────────────────────────────────────────────────────────────────────

async def send_to_webhook(alert: BrokerAlert, webhook_url: str) -> bool:
    """POST alert JSON to any webhook URL (TradingView, Zapier, etc.)."""
    try:
        payload = {
            "ticker": alert.ticker,
            "severity": alert.severity.value,
            "message": alert.message,
            "trap_score": alert.trap_score,
            "dilution_pct": alert.dilution_pct,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "Stock To Me Broker",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            return response.status_code in (200, 201, 202)
    except Exception as e:
        print(f"[Broker] Webhook error: {e}")
        return False


# ─── Unified sender ────────────────────────────────────────────────────────────

async def send_broker_alert(alert: BrokerAlert) -> dict:
    """
    Route a Broker alert to all enabled channels.
    Returns a summary dict of what was sent.
    """
    results = {}

    # Always log to Mission Control
    log_to_mission_control(alert)

    # E*TRADE
    if os.getenv("ETRADE_ENABLED", "false").lower() == "true":
        results["etrade"] = send_to_etrade(alert)

    # Webhook (TradingView etc.)
    webhook_url = os.getenv("BROKER_WEBHOOK_URL")
    if webhook_url:
        results["webhook"] = await send_to_webhook(alert, webhook_url)

    # Telegram — use the message tool from here
    # (handled separately via sessions_send to Telegram session)
    tg_session = os.getenv("BROKER_TELEGRAM_SESSION")
    if tg_session:
        from app.sessions import sessions_send
        try:
            await sessions_send(
                sessionKey=tg_session,
                message=f"🚨 *Broker Alert — {alert.ticker}*\n{alert.formatted_message()}",
            )
            results["telegram"] = True
        except Exception as e:
            results["telegram"] = False
            print(f"[Broker] Telegram error: {e}")

    return results


# ─── High-priority alert check ────────────────────────────────────────────────

def should_escalate(alert: BrokerAlert) -> bool:
    """Decide if this alert is important enough to interrupt."""
    if alert.severity in (AlertSeverity.SEVERE, AlertSeverity.HIGH):
        return True
    if alert.trap_score is not None and alert.trap_score >= 80:
        return True
    if alert.dilution_pct is not None and alert.dilution_pct >= 25:
        return True
    return False


# ─── CLI test ──────────────────────────────────────────────────────────────────

def main():
    alert = BrokerAlert(
        ticker="ZD",
        severity=AlertSeverity.HIGH,
        message="Possible pump-before-offering setup detected. 3 bullish PRs in 8 days. Rel volume 4.2x.",
        trap_score=78.0,
        dilution_pct=18.5,
    )
    log_to_mission_control(alert)

if __name__ == "__main__":
    main()
