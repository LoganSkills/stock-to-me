# Stock To Me — Build Specification (MVP to V1)

> SEC filing intelligence platform for small-cap traders. Monitors dilution risk, financing setups, and pump-before-offering patterns.

## 1. Product Summary

Stock To Me is a web-based intelligence platform for small-cap traders. It monitors SEC filings, company financial stress, capital-raise structures, price/volume behavior, and repeat company behavior patterns to identify dilution risk, financing setups, pump-before-offering behavior, and possible retail-trap conditions.

The product does not make guaranteed price predictions or accuse issuers of manipulation. It presents structured risk signals, historical pattern matches, dilution-impact estimates, and plain-English AI explanations.

**Core User Promise:** "Know when a small-cap setup is likely becoming a financing event, a pump-before-dilution pattern, or a high-risk liquidity trap."

---

## 2. Users

- **Primary:** Retail small-cap traders focused on biotech, microcaps, and low-float names
- **Secondary:** Active traders monitoring dilution and offering risk
- **Social/content traders:** Need fast plain-English summaries of filings

---

## 3. MVP Scope

### Includes
- Daily scan of U.S. small caps in a configurable universe
- SEC filing ingestion and parsing
- Basic financial stress calculations
- Core scoring engine (5 scores + trap score)
- Company timeline/event history
- Dilution calculator for direct offerings and warrant overhang
- AI summary generator
- Dashboard, stock detail page, and alerts page

### Excludes
- Options flow
- Real-time social sentiment as core dependency
- Broker integrations
- Auto-trading
- Full ML sequence modeling
- Mobile app
- Community/chat features

---

## 4. Product Modules

### A. Market Universe Module
Define which tickers are monitored.

**Initial Universe Rules:**
- U.S.-listed common stocks only
- Market cap: $10M to $750M
- Exclude ETFs, ADRs (configurable)
- Prefer: low revenue, biotech, clinical-stage, prior offering history

**Required Fields:**
`ticker, company_name, exchange, sector, industry, market_cap, float_shares, shares_outstanding, avg_volume_20d, current_price`

### B. SEC Filings Module
Ingest and classify filings relevant to dilution and financing risk.

**Filing Types:** S-1, S-1/A, 424B3, 424B4, 424B5, 8-K, 10-Q, 10-K, DEF 14A (optional), RW (later), EFFECT (later)

**Extracted Tags:**
`active shelf, direct offering, ATM program, registered direct, private placement, warrants issued, convertible notes, registration rights, resale registration, reverse split mention, Nasdaq compliance mention, going concern language`

### C. Financial Stress Module
Estimate capital pressure.

**Core Derived Metrics:**
- estimated cash runway (months)
- burn-to-cash ratio
- revenue weakness flag
- leverage stress flag

### D. Price/Volume Behavior Module
Detect pump setup conditions.

**Derived Signals:**
`relative volume, unusual premarket activity, multi-day momentum run, abnormal gap up, spike after filing/news`

### E. News/PR Timeline Module
Align communications with filings and trading behavior.

### F. Company Memory / Pattern Engine
Identify whether the issuer is repeating prior behavior. Compares current event sequence to prior issuer sequences and cross-company pattern templates.

### G. Dilution Impact Engine
Estimate share increase and possible repricing impact.

**Coverage:** direct offerings, registered directs, warrants, simple convertibles, ATM overhang estimate (range)

### H. AI Explanation Layer
Translate all system output into plain English. Caution wording only — no guarantees, no accusations.

---

## 5. Core Screens

### 5.1 Dashboard
Sections: Top Trap Scores Today, Highest Dilution Risk, New Financing Filings, Most Urgent Cash Need, New Pattern Repeats Detected, Recent Alerts

**Filters:** market cap range, sector, exchange, filing type, score thresholds, timeframe

### 5.2 Stock Detail Page
Header (ticker, company, exchange, price, market cap, float), Score Cards, AI Summary Box, Company Timeline, Filing/PR/Event Table, Dilution Impact Panel, Historical Pattern Matches, Alerts History

### 5.3 Alerts Page
Types: new filing alert, financing language alert, cash runway deterioration, pattern repeat, pump setup, dilution impact update

### 5.4 Admin / Configuration
Universe settings, score weights, parser rule management, alert thresholds

---

## 6. Database Schema

See `backend/app/models/models.py` for full SQLAlchemy definitions.

### Core Tables
- `companies` — ticker, CIK, name, exchange, sector, market_cap, float, shares, volume
- `market_data_daily` — OHLCV, premarket, relative volume, returns
- `filings` — accession number, filing type, filed_at, raw text, parsed JSON
- `filing_tags` — tag name, value (text/num), confidence
- `financial_snapshots` — cash, debt, revenue, burn, going concern flag
- `press_releases` — published_at, title, body, category
- `company_events` — event_type, source, metadata
- `offerings` — offering type, terms, proceeds, warrant details
- `score_snapshots` — all 5 scores + trap score
- `pattern_templates` — pattern code, name, rule JSON, active
- `pattern_matches` — matched template, score, sequence, historical reference
- `alerts` — type, severity, triggered_at, body, payload
- `users` — auth provider, plan type
- `watchlists` + `watchlist_items`

---

## 7. Scoring System

Scores range 0–100.

| Score | Purpose | Key Inputs |
|---|---|---|
| Cash Need | Capital pressure | runway months, going concern, burn, revenue |
| Dilution Pressure | Near-term supply increase | active S-1, 424B, ATM, warrants, convertibles |
| Pump Setup | Spec. momentum before financing | rel volume, premarket gap, PR frequency, low float |
| Timing Urgency | Event proximity | runway urgency, filing recency, compliance deadlines |
| Historical Repeat | Playbook repetition | prior offerings, reverse splits, PR-after-filing patterns |
| Pattern Similarity | Match to known templates | event sequences vs rule-based templates |
| **Trap Score** | **Primary risk score** | weighted composite of above 5 |

**Trap Score Formula:**
```
Trap Score = 0.25×Dilution + 0.20×CashNeed + 0.20×PumpSetup + 0.20×HistRepeat + 0.15×Timing
```

**Labels:** 0–24 Low | 25–49 Watch | 50–69 Elevated | 70–84 High Risk | 85–100 Severe

---

## 8. Pattern Engine

Rules + event sequences, not ML (MVP).

**Example Templates:**
- **P1: Pump Before Offering** — financing filing → bullish PR within 5 days → rel volume >3x → price spike >20%
- **P2: Reverse Split Funding Loop** — compliance risk → reverse split → shelf/S-1 refresh → financing event
- **P3: Warrant Overhang Reprice** — warrants near current price → stock spikes above exercise → follow-on selling

---

## 9. Dilution Impact Engine

**Calculations:**
- `immediate_dilution_pct = offering_shares / current_shares_outstanding`
- `new_shares = current + offering_shares`
- `theoretical_price = current_market_cap / new_shares`
- `fully_diluted_shares = current + offering + warrant_shares`
- `fully_diluted_theoretical_price = current_market_cap / fully_diluted_shares`

**Scenario Multipliers:** mild (×0.95), moderate (×0.85), severe (×0.70)

---

## 10. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind, shadcn/ui, Recharts |
| Backend | Python FastAPI, Celery (bg jobs), PostgreSQL, Redis |
| Data | SEC EDGAR (bulk FTP/public), market data API, fundamentals API, PR/news feed |
| Infra | Vercel (frontend), Railway/Render/Fly.io (backend), managed Postgres |

---

## 11. API Endpoints

```
Auth:
  POST /auth/register
  POST /auth/login
  GET  /auth/me

Dashboard:
  GET /dashboard/overview
  GET /dashboard/top-traps
  GET /dashboard/new-filings
  GET /dashboard/alerts

Stocks:
  GET /stocks
  GET /stocks/{ticker}
  GET /stocks/{ticker}/scores
  GET /stocks/{ticker}/timeline
  GET /stocks/{ticker}/filings
  GET /stocks/{ticker}/patterns
  GET /stocks/{ticker}/dilution-impact

Alerts:
  GET  /alerts
  PATCH /alerts/{id}/read

Watchlists:
  GET    /watchlists
  POST   /watchlists
  POST   /watchlists/{id}/items
  DELETE /watchlists/{id}/items/{ticker}

Jobs:
  POST /jobs/run-daily-scan
  POST /jobs/reparse-filing/{filing_id}
  POST /admin/score-config
```

---

## 12. Build Phases

### Phase 0 — Foundation (Week 1)
Repo setup, auth scaffold, database schema, stock universe loader, basic frontend shell

### Phase 1 — Core Data (Week 2)
SEC ingestion, filings storage, market data integration, financial snapshots

### Phase 2 — Intelligence MVP (Week 3)
Filing tag extraction, cash need score, dilution pressure score, trap score formula, company timeline

### Phase 3 — Stock Page / Dashboard (Week 4)
Dashboard cards, stock detail page, score cards, AI summary box

### Phase 4 — Pattern + Dilution Engine (Week 5)
Rule-based pattern templates, historical repeat logic, dilution calculations, alert generation

### Phase 5 — Polish / Beta (Week 6)
Filters, watchlists, onboarding text, subscription stubs, QA

---

## 13. Acceptance Criteria (MVP)

1. Dashboard shows ranked high-risk names
2. Click stock → view current scores
3. View recent filings and extracted financing terms
4. View timeline of filings, PRs, price/volume events
5. Dilution impact estimate when offering terms available
6. Plain-English summary of current risk
7. Alerts generated when thresholds crossed

---

## 14. Legal / Compliance Language

**Approved:** "high dilution risk," "possible financing setup," "pattern consistent with prior financing behavior," "historically associated with selling pressure," "illustrative estimate"

**Avoid:** "guaranteed pump and dump," "hedge funds are manipulating," "this will go to X"
