export interface Company {
  id: number;
  ticker: string;
  name: string;
  exchange: string;
  sector: string | null;
  industry: string | null;
  market_cap: number | null;
  float_shares: number | null;
  shares_outstanding: number | null;
  avg_volume_20d: number | null;
  current_price: number | null;
  is_active: boolean;
  created_at: string;
}

export interface ScoreSnapshot {
  id: number;
  company_id: number;
  as_of_timestamp: string;
  cash_need_score: number;
  dilution_pressure_score: number;
  pump_setup_score: number;
  trap_score: number;
  timing_urgency_score: number;
  historical_repeat_score: number;
  pattern_similarity_score: number;
  dilution_impact_score: number;
  ai_summary: string | null;
  version: string;
}

export interface FilingTag {
  id: number;
  tag_name: string;
  tag_value_text: string | null;
  tag_value_num: number | null;
  confidence: number | null;
}

export interface Filing {
  id: number;
  company_id: number;
  accession_number: string;
  filing_type: string;
  filed_at: string;
  source_url: string | null;
  parsed_json: Record<string, unknown> | null;
  created_at: string;
  tags: FilingTag[];
}

export interface PressRelease {
  id: number;
  company_id: number;
  published_at: string;
  title: string;
  body_text: string | null;
  category: string | null;
  source_url: string | null;
}

export interface Alert {
  id: number;
  company_id: number | null;
  alert_type: string;
  severity: string;
  triggered_at: string;
  title: string;
  body: string;
  payload_json: Record<string, unknown> | null;
  is_read: boolean;
}

export interface TimelineEvent {
  timestamp: string;
  event_type: string;
  label: string;
  detail: string | null;
  source: string | null;
  metadata: Record<string, unknown> | null;
}

export interface DilutionImpact {
  company_id: number;
  ticker: string;
  current_price: number | null;
  current_shares: number | null;
  current_market_cap: number | null;
  immediate_dilution_pct: number | null;
  potential_total_dilution_pct: number | null;
  new_shares_outstanding: number | null;
  theoretical_price: number | null;
  theoretical_price_mild: number | null;
  theoretical_price_moderate: number | null;
  theoretical_price_severe: number | null;
  warrant_overhang_notes: string | null;
}

export interface TopTrapItem {
  ticker: string;
  name: string;
  trap_score: number;
  trap_label: string;
  dilution_pressure_score: number;
  cash_need_score: number;
  pump_setup_score: number;
  latest_pr: string | null;
}

export interface DashboardOverview {
  total_companies: number;
  high_trap_count: number;
  new_filings_today: number;
  active_alerts: number;
  trap_score_breakdown: Record<string, number>;
}

export const TRAP_LABELS: Record<string, string> = {
  Low: "bg-green-100 text-green-800",
  Watch: "bg-yellow-100 text-yellow-800",
  Elevated: "bg-orange-100 text-orange-800",
  "High Risk": "bg-red-100 text-red-800",
  Severe: "bg-red-200 text-red-900 font-bold",
};

export function trapLabel(score: number): string {
  if (score >= 85) return "Severe";
  if (score >= 70) return "High Risk";
  if (score >= 50) return "Elevated";
  if (score >= 25) return "Watch";
  return "Low";
}

export function formatMarketCap(value: number | null): string {
  if (value === null) return "—";
  if (value >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(1)}B`;
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  return `$${value.toLocaleString()}`;
}

export function formatShares(value: number | null): string {
  if (value === null) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  return value.toLocaleString();
}
