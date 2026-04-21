"""SQLAlchemy models for Stock To Me."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, Float, ForeignKey, Index, Integer,
    JSON, Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def now_utc():
    return datetime.now(timezone.utc)


# ─── Enum helpers ────────────────────────────────────────────────────────────


class FilingType(str):
    S1 = "S-1"
    S1A = "S-1/A"
    F424B3 = "424B3"
    F424B4 = "424B4"
    F424B5 = "424B5"
    EIGHT_K = "8-K"
    TEN_Q = "10-Q"
    TEN_K = "10-K"
    DEF14A = "DEF 14A"
    RW = "RW"
    EFFECT = "EFFECT"


class AlertSeverity(str):
    INFO = "info"
    CAUTION = "caution"
    HIGH = "high"
    SEVERE = "severe"


class AlertType(str):
    NEW_FILING = "new_filing"
    FINANCING_TERMS = "financing_terms"
    CASH_RUNWAY = "cash_runway"
    PATTERN_REPEAT = "pattern_repeat"
    PUMP_SETUP = "pump_setup"
    WARRANT_OVERHANG = "warrant_overhang"
    TRAP_SCORE = "trap_score"


class EventType(str):
    FINANCING_FILING = "financing_filing"
    SHELF_FILING = "shelf_filing"
    AMENDMENT_FILING = "amendment_filing"
    PROSPECTUS_FILING = "prospectus_filing"
    FINANCING_8K = "financing_8k"
    BULLISH_PR = "bullish_pr"
    COMPLIANCE_NOTICE = "compliance_notice"
    REVERSE_SPLIT = "reverse_split"
    VOLUME_SPIKE = "volume_spike"
    PRICE_SPIKE = "price_spike"
    SELLOFF = "selloff"
    OFFERING_PRESSURE = "offering_pressure"


# ─── Company ──────────────────────────────────────────────────────────────────


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticker: Mapped[str] = mapped_column(String(10), unique=True, nullable=False, index=True)
    cik: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    exchange: Mapped[str] = mapped_column(String(20), nullable=False)
    sector: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    market_cap: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    float_shares: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    shares_outstanding: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    avg_volume_20d: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    current_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )

    # Relationships
    market_data: Mapped[List["MarketDataDaily"]] = relationship(back_populates="company")
    filings: Mapped[List["Filing"]] = relationship(back_populates="company")
    financial_snapshots: Mapped[List["FinancialSnapshot"]] = relationship(back_populates="company")
    press_releases: Mapped[List["PressRelease"]] = relationship(back_populates="company")
    company_events: Mapped[List["CompanyEvent"]] = relationship(back_populates="company")
    offerings: Mapped[List["Offering"]] = relationship(back_populates="company")
    score_snapshots: Mapped[List["ScoreSnapshot"]] = relationship(back_populates="company")
    pattern_matches: Mapped[List["PatternMatch"]] = relationship(back_populates="company")
    alerts: Mapped[List["Alert"]] = relationship(back_populates="company")
    watchlist_items: Mapped[List["WatchlistItem"]] = relationship(back_populates="company")


# ─── Market Data ───────────────────────────────────────────────────────────────


class MarketDataDaily(Base):
    __tablename__ = "market_data_daily"
    __table_args__ = (
        Index("ix_market_data_company_date", "company_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    open: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    close: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    premarket_volume: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    premarket_gap_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rel_volume_5d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rel_volume_20d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    return_1d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    return_3d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    return_5d: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    company: Mapped["Company"] = relationship(back_populates="market_data")


# ─── Filings ────────────────────────────────────────────────────────────────────


class Filing(Base):
    __tablename__ = "filings"
    __table_args__ = (
        Index("ix_filings_company_filed_at", "company_id", "filed_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    accession_number: Mapped[str] = mapped_column(String(50), nullable=False)
    filing_type: Mapped[str] = mapped_column(String(20), nullable=False)
    filed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="filings")
    tags: Mapped[List["FilingTag"]] = relationship(back_populates="filing")
    offerings: Mapped[List["Offering"]] = relationship(back_populates="filing")


class FilingTag(Base):
    __tablename__ = "filing_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filing_id: Mapped[int] = mapped_column(ForeignKey("filings.id"), nullable=False)
    tag_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tag_value_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tag_value_num: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    filing: Mapped["Filing"] = relationship(back_populates="tags")


# ─── Financial Snapshots ────────────────────────────────────────────────────────


class FinancialSnapshot(Base):
    __tablename__ = "financial_snapshots"
    __table_args__ = (
        Index("ix_financial_snapshots_company_period", "company_id", "period_end"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    period_end: Mapped[datetime] = mapped_column(Date, nullable=False)
    report_type: Mapped[str] = mapped_column(String(10), nullable=False)  # 10-Q, 10-K
    cash_and_equivalents: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    total_debt: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    revenue: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    op_cash_flow: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    net_loss: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    going_concern_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    company: Mapped["Company"] = relationship(back_populates="financial_snapshots")


# ─── Press Releases ─────────────────────────────────────────────────────────────


class PressRelease(Base):
    __tablename__ = "press_releases"
    __table_args__ = (
        Index("ix_press_releases_company_published", "company_id", "published_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    body_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    company: Mapped["Company"] = relationship(back_populates="press_releases")


# ─── Company Events ───────────────────────────────────────────────────────────


class CompanyEvent(Base):
    __tablename__ = "company_events"
    __table_args__ = (
        Index("ix_company_events_company_ts", "company_id", "event_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    company: Mapped["Company"] = relationship(back_populates="company_events")


# ─── Offerings ──────────────────────────────────────────────────────────────────


class Offering(Base):
    __tablename__ = "offerings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    filing_id: Mapped[Optional[int]] = mapped_column(ForeignKey("filings.id"), nullable=True)
    offering_type: Mapped[str] = mapped_column(String(50), nullable=False)
    announced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    offering_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    shares_offered: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    gross_proceeds: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    warrant_shares: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    warrant_exercise_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    atm_capacity_remaining: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    convertible_principal: Mapped[Optional[int]] = mapped_column(Numeric(20), nullable=True)
    convertible_conversion_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    company: Mapped["Company"] = relationship(back_populates="offerings")
    filing: Mapped[Optional["Filing"]] = relationship(back_populates="offerings")


# ─── Scores ────────────────────────────────────────────────────────────────────


class ScoreSnapshot(Base):
    __tablename__ = "score_snapshots"
    __table_args__ = (
        Index("ix_score_snapshots_company_timestamp", "company_id", "as_of_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    as_of_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    cash_need_score: Mapped[float] = mapped_column(Float, default=0)
    dilution_pressure_score: Mapped[float] = mapped_column(Float, default=0)
    pump_setup_score: Mapped[float] = mapped_column(Float, default=0)
    trap_score: Mapped[float] = mapped_column(Float, default=0)
    timing_urgency_score: Mapped[float] = mapped_column(Float, default=0)
    historical_repeat_score: Mapped[float] = mapped_column(Float, default=0)
    pattern_similarity_score: Mapped[float] = mapped_column(Float, default=0)
    dilution_impact_score: Mapped[float] = mapped_column(Float, default=0)
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(10), default="1.0")

    company: Mapped["Company"] = relationship(back_populates="score_snapshots")


# ─── Pattern Engine ─────────────────────────────────────────────────────────────


class PatternTemplate(Base):
    __tablename__ = "pattern_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    rule_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class PatternMatch(Base):
    __tablename__ = "pattern_matches"
    __table_args__ = (
        Index("ix_pattern_matches_company_matched", "company_id", "matched_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    matched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    template_id: Mapped[int] = mapped_column(ForeignKey("pattern_templates.id"), nullable=False)
    match_score: Mapped[float] = mapped_column(Float, default=0)
    matched_sequence_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    historical_reference_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    company: Mapped["Company"] = relationship(back_populates="pattern_matches")
    template: Mapped["PatternTemplate"] = relationship()


# ─── Alerts ─────────────────────────────────────────────────────────────────────


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_company_triggered", "company_id", "triggered_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id"), nullable=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    payload_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)

    company: Mapped[Optional["Company"]] = relationship(back_populates="alerts")


# ─── Users ────────────────────────────────────────────────────────────────────────


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[str] = mapped_column(String(50), default="email")
    provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    plan_type: Mapped[str] = mapped_column(String(20), default="free")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    watchlists: Mapped[List["Watchlist"]] = relationship(back_populates="user")


# ─── Watchlists ────────────────────────────────────────────────────────────────


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped["User"] = relationship(back_populates="watchlists")
    items: Mapped[List["WatchlistItem"]] = relationship(back_populates="watchlist")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    watchlist_id: Mapped[int] = mapped_column(ForeignKey("watchlists.id"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    watchlist: Mapped["Watchlist"] = relationship(back_populates="items")
    company: Mapped["Company"] = relationship(back_populates="watchlist_items")
