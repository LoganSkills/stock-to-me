# E*TRADE Setup Guide for Stock To Me

## Prerequisites

1. **E*TRADE Brokerage Account** — you already have one
2. **E*TRADE Developer Account** — needed to get API keys

## Step 1: Register as a Developer

1. Go to [developer.etrade.com](https://developer.etrade.com)
2. Click **"Get API Keys"** or sign in with your E*TRADE credentials
3. Create a new app:
   - App Name: `Stock To Me`
   - Purpose: Personal trading automation
   - Select **Sandbox** (test mode) first — use this while tuning
   - Select the APIs you need:
     - ✅ Accounts & Balances
     - ✅ Portfolio & Positions
     - ✅ Market Orders (place orders)
     - ✅ Order Preview

4. You'll receive:
   - **Consumer Key** (API Key)
   - **Consumer Secret** (API Secret)

## Step 2: Enable Production Access (when ready)

Production access requires E*TRADE review. For now, **Sandbox mode works perfectly** for building and testing. The scripts default to sandbox.

To go live:
- Submit production access request from the developer portal
- E*TRADE may require additional verification

## Step 3: Set Environment Variables

```bash
export ETRADE_API_KEY="your_consumer_key_here"
export ETRADE_API_SECRET="your_consumer_secret_here"
export ETRADE_SANDBOX="true"   # sandbox mode (safe to test)
# When ready for production:
export ETRADE_SANDBOX="false"
```

Add these to your `~/.bashrc` or `.env` file so they're always available.

## Step 4: Run OAuth Setup

```bash
cd /home/ubuntu/stock-to-me
python scripts/etrade_service.py --setup
```

This will:
1. Print an authorization URL
2. Open it in your browser
3. You sign into E*TRADE, authorize the app
4. You'll get a 6-digit PIN
5. Enter the PIN at the prompt
6. Tokens are saved to `.etrade_tokens.json`

## Step 5: Verify Connection

```bash
python scripts/etrade_service.py --status
python scripts/etrade_service.py --accounts
python scripts/etrade_service.py --positions
```

## API Capabilities

| Feature | Status |
|---------|--------|
| List accounts | ✅ |
| Get account balance | ✅ |
| List positions | ✅ |
| Place market order | ✅ |
| Place limit order | ✅ |
| Preview order | ✅ |
| Cancel order | ❌ (not yet) |
| Real-time quotes | ⚠️ requires market data add-on |

## Important Notes

**No automatic trading** — Stock To Me's Broker does NOT auto-execute trades. It:
- Monitors your positions alongside trap scores
- Sends alerts when high-risk setups are detected
- Can place watchlist signals to your E*TRADE account
- You confirm all orders manually

This keeps you in control and avoids any compliance issues with pattern day trading rules.

## Sandbox vs Production

- **Sandbox**: Uses fake market data. Orders don't execute. Safe for all testing.
- **Production**: Real money. Real orders execute. Requires production API key approval.

Always test in sandbox first.
