"""Pydantic schemas for request/response validation."""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ─── Auth ──────────────────────────────────────────────────────────────────────


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: str
    plan_type: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─── Company ────────────────────────────────────────────────────────────────────────


class CompanyOut(BaseModel):
    id: int
    ticker: str
    name: str
    exchange: str
    sector: Optional[str]
    industry: Optional[str]
    market_cap: Optional[int]
    float_shares: Optional[int]
    shares_outstanding: Optional[int]
    avg_volume_20d: Optional[int]
    current_price: Optional[float]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CompanyDetailOut(CompanyOut):
    latest_scores: Optional["ScoreSnapshotOut"] = None
    latest_pr: Optional["PressReleaseOut"] = None
    days_to_runway: Optional[int] = None

    class Config:
        from_attributes = True


# ─── Market Data ────────────────────────────────────────────────────────────────


class MarketDataDailyOut(BaseModel):
    id: int
    company_id: int
    date: date
    open: Optional[float]
    high: Optional[float]
    low: Optional[float]
    close: Optional[float]
    volume: Optional[int]
    premarket_volume: Optional[int]
    premarket_gap_pct: Optional[float]
    rel_volume_5d: Optional[float]
    rel_volume_20d: Optional[float]
    return_1d: Optional[float]
    return_3d: Optional[float]
    return_5d: Optional[float]

    class Config:
        from_attributes = True


# ─── Filings ────────────────────────────────────────────────────────────────────


class FilingTagOut(BaseModel):
    id: int
    tag_name: str
    tag_value_text: Optional[str]
    tag_value_num: Optional[float]
    confidence: Optional[float]

    class Config:
        from_attributes = True


class FilingOut(BaseModel):
    id: int
    company_id: int
    accession_number: str
    filing_type: str
    filed_at: datetime
    source_url: Optional[str]
    parsed_json: Optional[dict]
    created_at: datetime
    tags: List[FilingTagOut] = []

    class Config:
        from_attributes = True


# ─── Financial Snapshots ────────────────────────────────────────────────────────


class FinancialSnapshotOut(BaseModel):
    id: int
    company_id: int
    period_end: date
    report_type: str
    cash_and_equivalents: Optional[int]
    total_debt: Optional[int]
    revenue: Optional[int]
    op_cash_flow: Optional[int]
    net_loss: Optional[int]
    going_concern_flag: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─── Press Releases ──────────────────────────────────────────────────────────────


class PressReleaseOut(BaseModel):
    id: int
    company_id: int
    published_at: datetime
    title: str
    body_text: Optional[str]
    category: Optional[str]
    source_url: Optional[str]

    class Config:
        from_attributes = True


# ─── Company Events ─────────────────────────────────────────────────────────────


class CompanyEventOut(BaseModel):
    id: int
    company_id: int
    event_type: str
    event_timestamp: datetime
    source_type: Optional[str]
    metadata_json: Optional[dict]

    class Config:
        from_attributes = True


# ─── Offerings ──────────────────────────────────────────────────────────────────


class OfferingOut(BaseModel):
    id: int
    company_id: int
    offering_type: str
    announced_at: Optional[datetime]
    offering_price: Optional[float]
    shares_offered: Optional[int]
    gross_proceeds: Optional[int]
    warrant_shares: Optional[int]
    warrant_exercise_price: Optional[float]
    atm_capacity_remaining: Optional[int]
    convertible_principal: Optional[int]
    convertible_conversion_price: Optional[float]

    class Config:
        from_attributes = True


# ─── Scores ─────────────────────────────────────────────────────────────────────


class ScoreSnapshotOut(BaseModel):
    id: int
    company_id: int
    as_of_timestamp: datetime
    cash_need_score: float
    dilution_pressure_score: float
    pump_setup_score: float
    trap_score: float
    timing_urgency_score: float
    historical_repeat_score: float
    pattern_similarity_score: float
    dilution_impact_score: float
    ai_summary: Optional[str]
    version: str

    class Config:
        from_attributes = True


# ─── Pattern Engine ────────────────────────────────────────────────────────────


class PatternTemplateOut(BaseModel):
    id: int
    pattern_code: str
    name: str
    description: Optional[str]
    rule_json: dict
    active: bool

    class Config:
        from_attributes = True


class PatternMatchOut(BaseModel):
    id: int
    company_id: int
    matched_at: datetime
    template_id: int
    match_score: float
    matched_sequence_json: Optional[dict]
    historical_reference_json: Optional[dict]
    template: Optional[PatternTemplateOut] = None

    class Config:
        from_attributes = True


# ─── Alerts ─────────────────────────────────────────────────────────────────────


class AlertOut(BaseModel):
    id: int
    company_id: Optional[int]
    alert_type: str
    severity: str
    triggered_at: datetime
    title: str
    body: str
    payload_json: Optional[dict]
    is_read: bool

    class Config:
        from_attributes = True


class AlertUpdate(BaseModel):
    is_read: bool


# ─── Dashboard ──────────────────────────────────────────────────────────────────


class DashboardOverview(BaseModel):
    total_companies: int
    high_trap_count: int
    new_filings_today: int
    active_alerts: int
    trap_score_breakdown: dict  # e.g. {"low": 10, "watch": 20, ...}


class TopTrapItem(BaseModel):
    ticker: str
    name: str
    trap_score: float
    trap_label: str
    dilution_pressure_score: float
    cash_need_score: float
    pump_setup_score: float
    latest_pr: Optional[str] = None


class NewFilingItem(BaseModel):
    ticker: str
    name: str
    filing_type: str
    filed_at: datetime
    tags: List[str]


class AlertSummaryItem(BaseModel):
    id: int
    company_id: Optional[int]
    ticker: Optional[str]
    alert_type: str
    severity: str
    triggered_at: datetime
    title: str
    body: str
    is_read: bool


# ─── Dilution Impact ────────────────────────────────────────────────────────────


class DilutionImpactOut(BaseModel):
    company_id: int
    ticker: str
    current_price: Optional[float]
    current_shares: Optional[int]
    current_market_cap: Optional[float]
    immediate_dilution_pct: Optional[float]
    potential_total_dilution_pct: Optional[float]
    new_shares_outstanding: Optional[int]
    theoretical_price: Optional[float]
    theoretical_price_mild: Optional[float]
    theoretical_price_moderate: Optional[float]
    theoretical_price_severe: Optional[float]
    warrant_overhang_notes: Optional[str]
    offering_terms: Optional[OfferingOut]


# ─── Watchlists ────────────────────────────────────────────────────────────────


class WatchlistOut(BaseModel):
    id: int
    name: str
    created_at: datetime
    item_count: int = 0

    class Config:
        from_attributes = True


class WatchlistCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class WatchlistItemCreate(BaseModel):
    ticker: str


# ─── Stock List / Filter ────────────────────────────────────────────────────────


class StockFilter(BaseModel):
    min_market_cap: Optional[int] = None
    max_market_cap: Optional[int] = None
    sector: Optional[str] = None
    exchange: Optional[str] = None
    filing_type: Optional[str] = None
    min_trap_score: Optional[int] = None
    max_trap_score: Optional[int] = None
    timeframe: Optional[str] = "all"  # "1d", "7d", "30d", "all"


class StockListItem(BaseModel):
    ticker: str
    name: str
    exchange: str
    sector: Optional[str]
    market_cap: Optional[int]
    current_price: Optional[float]
    trap_score: Optional[float]
    trap_label: Optional[str]
    cash_need_score: Optional[float]
    dilution_pressure_score: Optional[float]
    pump_setup_score: Optional[float]
    latest_filed_at: Optional[datetime] = None


class StockListResponse(BaseModel):
    stocks: List[StockListItem]
    total: int
    page: int
    per_page: int


# ─── Company Timeline ──────────────────────────────────────────────────────────


class TimelineEvent(BaseModel):
    timestamp: datetime
    event_type: str
    label: str
    detail: Optional[str]
    source: Optional[str]
    metadata: Optional[dict]


class CompanyTimeline(BaseModel):
    ticker: str
    events: List[TimelineEvent]


# Forward refs
CompanyDetailOut.model_rebuild()
