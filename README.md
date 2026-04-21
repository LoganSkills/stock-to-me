# Stock To Me

SEC filing intelligence platform for small-cap traders. Monitors dilution risk, financing setups, pump-before-offering patterns, and repeat company playbooks.

## Overview

Stock To Me ingests SEC filings, market data, and press releases for U.S. small-cap stocks ($10M–$750M market cap) and scores each issuer for dilution and trap risk. It presents structured risk signals, historical pattern matches, dilution-impact estimates, and plain-English AI explanations.

**Core promise:** Know when a small-cap setup is likely becoming a financing event, a pump-before-dilution pattern, or a high-risk liquidity trap.

## Project Structure

```
stock-to-me/
├── backend/              # FastAPI + PostgreSQL + Celery
│   ├── app/
│   │   ├── api/         # Route handlers
│   │   ├── core/        # Config, database, auth
│   │   ├── models/      # SQLAlchemy models
│   │   ├── schemas/     # Pydantic request/response
│   │   └── services/    # Business logic
│   └── migrations/       # Alembic DB migrations
├── frontend/            # Next.js app
│   ├── app/            # App router pages
│   ├── components/     # UI components
│   └── types/          # Shared TypeScript types
├── data/               # Seed data, reference files
└── scripts/            # DB init, one-off scripts
```

## Quick Start

### Backend

```bash
cd backend
cp .env.example .env   # fill in your values
docker compose up -d  # starts Postgres + Redis
alembic upgrade head  # apply migrations
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

## Tech Stack

- **Frontend:** Next.js, TypeScript, Tailwind, shadcn/ui, Recharts
- **Backend:** FastAPI, SQLAlchemy, Alembic, Celery, Redis
- **Database:** PostgreSQL
- **Data:** SEC EDGAR bulk FTP, market data API

## MVP Status

Phase 0 (Foundation) — in progress. See SPEC.md for full build roadmap.

## License

MIT
