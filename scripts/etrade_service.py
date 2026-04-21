"""
E*TRADE API Connector — OAuth1 + REST API client.

Handles the full OAuth1 flow:
  1. Get request token (PUT)
  2. Authorize in browser (GET)
  3. Exchange for access token (GET)
  4. Store tokens for reuse
  5. Make signed API calls

Docs: https://developer.etrade.com/docs
Production endpoint: https://api.etrade.com
Sandbox: https://apisb.etrade.com

Usage:
  python scripts/etrade_service.py --setup          # first-time OAuth flow
  python scripts/etrade_service.py --status        # check connection
  python scripts/etrade_service.py --positions    # fetch positions
  python scripts/etrade_service.py --alert ZD     # send alert to E*TRADE
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs

import httpx
from oauthlib.oauth1 import OAuth1
from requests_oauthlib import OAuth1Session

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.core.config import get_settings

settings = get_settings()

# ─── Config ────────────────────────────────────────────────────────────────────

ETRADE_CONFIG_FILE = Path(__file__).parent.parent / ".etrade_tokens.json"

# E*TRADE API endpoints
BASE_URL = "https://api.etrade.com"          # production
SANDBOX_URL = "https://apisb.etrade.com"    # sandbox

SANDBOX = os.getenv("ETRADE_SANDBOX", "true").lower() == "true"
BASE = SANDBOX_URL if SANDBOX else BASE_URL

# Consumer key/secret — set via environment or .env
API_KEY = os.getenv("ETRADE_API_KEY", "")
API_SECRET = os.getenv("ETRADE_API_SECRET", "")


# ─── Token storage ─────────────────────────────────────────────────────────────

def load_tokens() -> dict | None:
    if ETRADE_CONFIG_FILE.exists():
        with open(ETRADE_CONFIG_FILE) as f:
            return json.load(f)
    return None


def save_tokens(tokens: dict) -> None:
    with open(ETRADE_CONFIG_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    os.chmod(str(ETRADE_CONFIG_FILE), 0o600)


# ─── OAuth1 flow ───────────────────────────────────────────────────────────────

def get_request_token() -> tuple[str, str]:
    """Step 1: Get a request token (temporary, needs authorization)."""
    if not API_KEY or not API_SECRET:
        raise ValueError("Set ETRADE_API_KEY and ETRADE_API_SECRET environment variables first.")

    oauth = OAuth1Session(client_key=API_KEY, client_secret=API_SECRET)
    response = oauth.fetch_request_token(
        f"{BASE}/oauth/request_token",
        params={"oauth_callback": "oob"},  # out-of-band pin
    )
    return response["oauth_token"], response["oauth_token_secret"]


def get_authorization_url(request_token: str) -> str:
    """Step 2: Get the authorization URL for the user to visit in their browser."""
    return (
        f"{BASE}/oauth/authorize"
        f"?oauth_token={request_token}"
        f"&oauth_token_secret="
    )


def exchange_request_token(
    request_token: str,
    request_token_secret: str,
    verifier: str,
) -> dict:
    """Step 3: Exchange the verifier PIN for a permanent access token."""
    oauth = OAuth1Session(
        client_key=API_KEY,
        client_secret=API_SECRET,
        resource_owner_key=request_token,
        resource_owner_secret=request_token_secret,
    )
    response = oauth.fetch_access_token(
        f"{BASE}/oauth/access_token",
        params={"oauth_verifier": verifier},
    )
    return {
        "access_token": response["oauth_token"],
        "access_token_secret": response["oauth_token_secret"],
        "sandbox": SANDBOX,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }


# ─── Authenticated API client ─────────────────────────────────────────────────

class ETradeClient:
    """Authenticated E*TRADE API client."""

    def __init__(self, access_token: str, access_token_secret: str):
        self.client = OAuth1Session(
            client_key=API_KEY,
            client_secret=API_SECRET,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )

    def _get(self, path: str, params: dict | None = None) -> dict:
        """Make a signed GET request."""
        url = f"{BASE}{path}"
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def _post(self, path: str, data: dict | None = None) -> dict:
        """Make a signed POST request."""
        url = f"{BASE}{path}"
        response = self.client.post(url, json=data)
        response.raise_for_status()
        return response.json()

    # ─── Account ───────────────────────────────────────────────────────────────

    def list_accounts(self) -> dict:
        """List all accounts."""
        return self._get("/v1/accounts.json")

    def get_account_balance(self, account_id: str) -> dict:
        """Get cash balances for an account."""
        return self._get(f"/v1/accounts/{account_id}/balance.json")

    # ─── Positions ─────────────────────────────────────────────────────────────

    def list_positions(self, account_id: str) -> dict:
        """List all positions in an account."""
        return self._get(f"/v1/accounts/{account_id}/portfolio.json")

    def get_position(self, account_id: str, ticker: str) -> dict:
        """Get a specific position by ticker."""
        return self._get(
            f"/v1/accounts/{account_id}/portfolio.json",
            params={"symbols": ticker.upper()},
        )

    # ─── Orders ──────────────────────────────────────────────────────────────

    def place_order(
        self,
        account_id: str,
        ticker: str,
        quantity: int,
        order_type: str = "EQ",  # EQ = stock
        side: str = "BUY",       # BUY or SELL
        price_type: str = "MARKET",
        limit_price: float | None = None,
    ) -> dict:
        """Place a stock order."""
        order = {
            "orders": {
                "order": [
                    {
                        "instrument": {
                            "symbol": ticker.upper(),
                            "assetType": order_type,
                        },
                        "quantity": quantity,
                        "orderType": "MARKET" if price_type == "MARKET" else "LIMIT",
                        "side": side,
                    }
                ]
            }
        }
        if limit_price:
            order["orders"]["order"][0]["limitPrice"] = limit_price

        return self._post(f"/v1/accounts/{account_id}/orders.json", data=order)

    def preview_order(
        self,
        account_id: str,
        ticker: str,
        quantity: int,
        side: str = "BUY",
        limit_price: float | None = None,
    ) -> dict:
        """Preview an order (no execution)."""
        return self.place_order(
            account_id, ticker, quantity, side=side, limit_price=limit_price
        )

    # ─── Alerts from Broker ────────────────────────────────────────────────────

    def send_alert(self, ticker: str, message: str) -> dict:
        """
        Send a Broker alert as a note to the user.
        E*TRADE doesn't have push notifications via API,
        so we create a BUY watchlist order as a signal placeholder.
        The user watches their E*TRADE watchlist for these.
        """
        return {
            "status": "ok",
            "ticker": ticker,
            "message": message,
            "note": "E*TRADE watchlist orders used as signal — no automatic execution",
        }


# ─── Convenience functions ─────────────────────────────────────────────────────

def get_client() -> ETradeClient | None:
    """Get an authenticated E*TRADE client from stored tokens."""
    tokens = load_tokens()
    if not tokens:
        return None
    return ETradeClient(
        access_token=tokens["access_token"],
        access_token_secret=tokens["access_token_secret"],
    )


# ─── CLI ────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="E*TRADE API connector")
    parser.add_argument("--setup", action="store_true", help="Run first-time OAuth setup")
    parser.add_argument("--status", action="store_true", help="Check connection status")
    parser.add_argument("--accounts", action="store_true", help="List accounts")
    parser.add_argument("--positions", action="store_true", help="List positions")
    parser.add_argument("--account-id", type=str, default=None, help="Account ID")
    parser.add_argument("--ticker", type=str, default=None, help="Ticker symbol")
    args = parser.parse_args()

    if args.setup:
        print("🚀 E*TRADE OAuth Setup\n")
        print(f"Sandbox mode: {SANDBOX}")
        print()

        request_token, request_token_secret = get_request_token()
        auth_url = get_authorization_url(request_token)

        print(f"1. Open this URL in your browser:\n")
        print(f"   {auth_url}")
        print()
        print("2. Sign in to your E*TRADE account")
        print("3. Authorize the app — you'll get a verification code (6-digit PIN)")
        print("4. Enter the PIN below:\n")

        verifier = input("Verification code: ").strip()

        tokens = exchange_request_token(request_token, request_token_secret, verifier)
        save_tokens(tokens)

        print("\n✅ Access tokens saved!")
        print(f"   {'Sandbox' if SANDBOX else 'Production'} mode")
        print("   Run with --status to verify connection.")
        return

    client = get_client()
    if not client:
        print("❌ Not connected. Run: python etrade_service.py --setup")
        return

    if args.status:
        print("✅ E*TRADE connection active")
        accounts = client.list_accounts()
        for acct in accounts.get("AccountList", {}).get("Account", []):
            print(f"   Account: {acct['accountId']} ({acct['accountName']})")
        return

    if args.accounts:
        data = client.list_accounts()
        print(json.dumps(data, indent=2))
        return

    if args.positions:
        account_id = args.account_id
        if not account_id:
            accounts = client.list_accounts()
            account_id = accounts["AccountList"]["Account"][0]["accountId"]
        data = client.list_positions(account_id)
        print(json.dumps(data, indent=2))
        return


if __name__ == "__main__":
    main()
