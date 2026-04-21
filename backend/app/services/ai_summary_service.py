"""AI Summary Generator — plain-English risk summaries from structured inputs."""

from datetime import datetime, timezone

from app.models.models import ScoreSnapshot, Filing, PressRelease, CompanyEvent
from app.services.scoring_service import trap_label


RISK_PHRASES = {
    "Severe": "This name shows multiple high-risk signals. A financing event could be imminent.",
    "High Risk": "Elevated dilution and capital-need pressures are present. Watch closely.",
    "Elevated": "Some concern signals detected. The setup warrants attention.",
    "Watch": "Early signs of potential financing activity. No immediate action needed.",
    "Low": "No major risk signals detected at this time.",
}

FINANCING_VERBS = {
    "S-1": "filed a new registration statement",
    "S-1/A": "amended its registration statement",
    "424B3": "filed a prospectus supplement",
    "424B4": "filed a pricing supplement",
    "424B5": "filed a final prospectus supplement",
    "8-K": "disclosed a material financing arrangement",
    "10-Q": "reported quarterly financials",
    "10-K": "reported annual financials",
}


def build_stock_summary(
    ticker: str,
    company_name: str,
    scores: ScoreSnapshot,
    recent_filings: list[Filing],
    latest_pr: PressRelease | None,
    days_to_runway: float | None,
) -> str:
    """Build a one-paragraph plain-English stock summary."""

    label = trap_label(scores.trap_score)
    risk_note = RISK_PHRASES.get(label, "")

    # Financing filings summary
    financing_types = {"S-1", "S-1/A", "424B3", "424B4", "424B5", "8-K"}
    financing_filings = [f for f in recent_filings if f.filing_type in financing_types]
    filing_detail = ""
    if financing_filings:
        latest = financing_filings[0]
        verb = FINANCING_VERBS.get(latest.filing_type, "filed")
        days_ago = (datetime.now(timezone.utc) - latest.filed_at).days
        filing_detail = (
            f" {company_name} {verb} ({latest.filing_type}) "
            f"{days_ago} day{'s' if days_ago != 1 else ''} ago."
        )
        if scores.dilution_pressure_score >= 50:
            filing_detail += " The filing suggests active capital-raising setup."

    # Cash runway
    runway_detail = ""
    if days_to_runway is not None:
        if days_to_runway <= 3:
            runway_detail = f" Cash runway is critical — approximately {days_to_runway:.0f} months of cash remaining."
        elif days_to_runway <= 9:
            runway_detail = f" Cash runway is limited — roughly {days_to_runway:.0f} months remaining."

    # PR narrative
    pr_detail = ""
    if latest_pr:
        pr_detail = f" Recent press release: '{latest_pr.title}'."

    # Pump setup
    pump_detail = ""
    if scores.pump_setup_score >= 50:
        pump_detail = " Unusual volume and price action detected — a pump setup cannot be ruled out."

    # Historical repeat
    hist_detail = ""
    if scores.historical_repeat_score >= 50:
        hist_detail = " The company's recent behavior mirrors its prior capital-raise patterns."

    summary = f"{ticker} — {label} Risk. {risk_note}{runway_detail}{filing_detail}{pr_detail}{pump_detail}{hist_detail}"

    # Enforce cautionary language
    summary = summary.replace(" will ", " may ").replace(" will ", " could ")
    summary = summary.replace(" is manipulating", " may be setting up")
    summary = summary.replace(" guaranteed", " possible")

    if len(summary) > 500:
        summary = summary[:497] + "..."

    return summary


def build_event_explanation(
    ticker: str,
    event_type: str,
    event_timestamp: datetime,
    metadata: dict | None,
) -> str:
    """Build a plain-English explanation of a specific event."""
    ts_str = event_timestamp.strftime("%b %d, %Y")

    explanations = {
        "financing_filing": f"{ticker} filed a financing-related SEC filing on {ts_str}.",
        "shelf_filing": f"{ticker} registered a new securities shelf on {ts_str}, which may indicate plans to raise capital.",
        "prospectus_filing": f"{ticker} filed a prospectus on {ts_str}, moving closer to an actual offering.",
        "bullish_pr": f"{ticker} issued a positive press release on {ts_str}.",
        "volume_spike": f"Unusual volume detected for {ticker} around {ts_str}.",
        "price_spike": f"{ticker} experienced a significant price move on {ts_str}.",
        "selloff": f"{ticker} experienced selling pressure on {ts_str}.",
        "reverse_split": f"{ticker} executed a reverse split on {ts_str}.",
        "compliance_notice": f"Compliance or delisting notice filed by {ticker} on {ts_str}.",
    }

    base = explanations.get(event_type, f"Event recorded for {ticker} on {ts_str}.")

    if event_type == "financing_filing" and metadata:
        ft = metadata.get("filing_type", "")
        if ft in FINANCING_VERBS:
            return f"{ticker} {FINANCING_VERBS[ft][:-1]} on {ts_str}."

    return base


def build_what_changed(
    ticker: str,
    prev_scores: ScoreSnapshot | None,
    curr_scores: ScoreSnapshot,
) -> str:
    """Build 'what changed today' section."""
    if prev_scores is None:
        return f"First score recorded for {ticker}. Initial Trap Score: {curr_scores.trap_score:.0f} ({trap_label(curr_scores.trap_score)})."

    changes = []
    if abs(curr_scores.trap_score - prev_scores.trap_score) >= 5:
        direction = "increased" if curr_scores.trap_score > prev_scores.trap_score else "decreased"
        changes.append(f"Trap Score {direction} from {prev_scores.trap_score:.0f} to {curr_scores.trap_score:.0f}")

    if abs(curr_scores.dilution_pressure_score - prev_scores.dilution_pressure_score) >= 10:
        direction = "increased" if curr_scores.dilution_pressure_score > prev_scores.dilution_pressure_score else "decreased"
        changes.append(f"Dilution Pressure {direction}")

    if abs(curr_scores.cash_need_score - prev_scores.cash_need_score) >= 10:
        direction = "increased" if curr_scores.cash_need_score > prev_scores.cash_need_score else "decreased"
        changes.append(f"Cash Need Score {direction}")

    if not changes:
        return f"No significant score changes for {ticker} today."

    return f"{ticker}: {'; '.join(changes)}."


