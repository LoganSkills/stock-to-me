"""SEC Filing Ingestion Service — EDGAR bulk FTP + API."""

import re
import json
import gzip
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List
from urllib.parse import urljoin

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Company, Filing, FilingTag, CompanyEvent, EventType
from app.core.config import get_settings

settings = get_settings()

EDGAR_BASE = "https://data.sec.gov"
SUBMISSIONS_PATH = "/submissions/"
FILING_TYPES_PRIORITY = {"S-1", "S-1/A", "424B3", "424B4", "424B5", "8-K", "10-Q", "10-K"}


defcik = re.compile(r"^\d{10}$")


def safe_get_text(doc: httpx.Response, max_len: int = 50_000) -> Optional[str]:
    """Extract text content, fall back to .txt link."""
    content_type = doc.headers.get("Content-Type", "")
    if "text/html" in content_type or "text/plain" in content_type:
        text = doc.text[:max_len]
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text if text else None
    return None


async def fetch_company_submissions(cik: str) -> Optional[dict]:
    """Fetch company submission index from EDGAR."""
    path = f"{SUBMISSIONS_PATH}CIK{cik.zfill(10)}.json"
    url = urljoin(EDGAR_BASE, path)
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            doc = await client.get(url)
            if doc.status_code == 200:
                return doc.json()
        except Exception:
            pass
    return None


async def fetch_filing_text(company: Company, accession: str) -> Optional[str]:
    """Fetch raw filing text from EDGAR Archives."""
    accession_normalized = accession.replace("/", "").replace("\\", "")
    path = f"/Archives/edgar/data/{company.cik}/{accession_normalized}/{accession_normalized}.txt"
    url = urljoin("https://www.sec.gov", path)
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            doc = await client.get(url)
            if doc.status_code == 200:
                return doc.text[:100_000]
        except Exception:
            pass
    return None


def parse_filing_date(filing_date_str: str) -> datetime:
    """Parse EDGAR filing date string."""
    try:
        return datetime.strptime(filing_date_str[:10], "%Y-%m-%d")
    except Exception:
        return datetime.now(timezone.utc)


def extract_accession_number(doc: httpx.Response) -> Optional[str]:
    """Extract accession number from filing HTML."""
    match = re.search(r"ACCESSION NUMBER:\s*(\d+-\d+-\d+)", doc.text)
    return match.group(1) if match else None


def extract_filing_tags(filing_type: str, raw_text: str) -> List[dict]:
    """Extract structured tags from filing raw text using regex rules."""
    tags = []

    if filing_type in ("S-1", "S-1/A", "424B3", "424B4", "424B5"):
        # Share offering amounts
        share_match = re.search(r"(\d[\d,]*)\s*(?:shares?|shares of)", raw_text[:50_000], re.I)
        if share_match:
            shares_str = re.sub(r"[^\d]", "", share_match.group(1))
            if shares_str:
                tags.append({"tag_name": "shares_offered", "tag_value_num": float(shares_str), "confidence": 0.7})

        # Offering price
        price_match = re.search(r"\$?([\d.]+)\s*(?:per share)?", raw_text[:50_000], re.I)
        if price_match:
            try:
                price = float(price_match.group(1))
                if 0.01 < price < 100_000:
                    tags.append({"tag_name": "offering_price", "tag_value_num": price, "confidence": 0.6})
            except ValueError:
                pass

        # Gross proceeds
        proceeds_match = re.search(r"\$([\d,]+)\s*(?:gross proceeds|million)", raw_text[:50_000], re.I)
        if proceeds_match:
            proceeds_str = re.sub(r"[^\d]", "", proceeds_match.group(1))
            tags.append({"tag_name": "gross_proceeds", "tag_value_num": float(proceeds_str), "confidence": 0.6})

        # Detect offering type language
        text_lower = raw_text[:50_000].lower()
        if "direct offering" in text_lower or "registered direct" in text_lower:
            tags.append({"tag_name": "offering_type", "tag_value_text": "direct_offering", "confidence": 0.8})
        if "at-the-market" in text_lower or "atm" in text_lower:
            tags.append({"tag_name": "offering_type", "tag_value_text": "atm", "confidence": 0.8})
        if "private placement" in text_lower:
            tags.append({"tag_name": "offering_type", "tag_value_text": "private_placement", "confidence": 0.8})
        if "warrant" in text_lower:
            tags.append({"tag_name": "warrants_issued", "tag_value_text": "suspected", "confidence": 0.6})
        if "resale registration" in text_lower or "registration rights" in text_lower:
            tags.append({"tag_name": "resale_registration", "tag_value_text": "yes", "confidence": 0.7})
        if "convertible" in text_lower and "note" in text_lower:
            tags.append({"tag_name": "convertible_notes", "tag_value_text": "suspected", "confidence": 0.6})
        if "shelf" in text_lower:
            tags.append({"tag_name": "active_shelf", "tag_value_text": "yes", "confidence": 0.7})

    elif filing_type in ("10-Q", "10-K"):
        text_lower = raw_text[:50_000].lower()

        # Going concern
        if "going concern" in text_lower or "substantial doubt" in text_lower:
            tags.append({"tag_name": "going_concern", "tag_value_text": "yes", "confidence": 0.9})
        if "cash and cash equivalents" in text_lower:
            cash_match = re.search(r"cash and cash equivalents[\r\n\s]*([\d,]+)", raw_text[:100_000], re.I)
            if cash_match:
                cash_str = re.sub(r"[^\d]", "", cash_match.group(1))
                tags.append({"tag_name": "cash", "tag_value_num": float(cash_str), "confidence": 0.8})
        if "revenue" in text_lower:
            rev_match = re.search(r"revenue[\r\n\s]*([\d,]+)", raw_text[:100_000], re.I)
            if rev_match:
                rev_str = re.sub(r"[^\d]", "", rev_match.group(1))
                tags.append({"tag_name": "revenue", "tag_value_num": float(rev_str), "confidence": 0.8})

    elif filing_type == "8-K":
        text_lower = raw_text[:30_000].lower()
        if "financing" in text_lower or "purchase agreement" in text_lower:
            tags.append({"tag_name": "financing_language", "tag_value_text": "yes", "confidence": 0.7})
        if "warrant" in text_lower:
            tags.append({"tag_name": "warrants_issued", "tag_value_text": "yes", "confidence": 0.7})
        if "convertible" in text_lower:
            tags.append({"tag_name": "convertible_notes", "tag_value_text": "yes", "confidence": 0.7})
        if "delisting" in text_lower or "nasdaq compliance" in text_lower:
            tags.append({"tag_name": "compliance_notice", "tag_value_text": "yes", "confidence": 0.8})

    return tags


async def ingest_company_filings(
    company: Company,
    session: AsyncSession,
    days_back: int = 30,
) -> List[Filing]:
    """Fetch and store recent filings for a company."""
    submissions = await fetch_company_submissions(company.cik)
    if not submissions:
        return []

    recent_filings = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    for filing in submissions.get("recentFilings", []):
        filing_date_str = filing.get("filingDate", "")
        filed_at = parse_filing_date(filing_date_str)

        if filed_at < cutoff:
            continue

        filing_type = filing.get("form", "")
        if filing_type not in FILING_TYPES_PRIORITY:
            continue

        accession = filing.get("accessionNumber", "")
        if not accession:
            continue

        # Check if already ingested
        result = await session.execute(
            select(Filing).where(
                Filing.company_id == company.id,
                Filing.accession_number == accession,
            )
        )
        if result.scalar_one_or_none():
            continue

        # Fetch raw text
        raw_text = await fetch_filing_text(company, accession)

        # Create filing record
        new_filing = Filing(
            company_id=company.id,
            accession_number=accession,
            filing_type=filing_type,
            filed_at=filed_at,
            source_url=filing.get("documentUrl"),
            raw_text=raw_text,
        )
        session.add(new_filing)
        await session.flush()

        # Extract and store tags
        if raw_text:
            extracted_tags = extract_filing_tags(filing_type, raw_text)
            for tag_data in extracted_tags:
                tag = FilingTag(
                    filing_id=new_filing.id,
                    tag_name=tag_data["tag_name"],
                    tag_value_text=tag_data.get("tag_value_text"),
                    tag_value_num=tag_data.get("tag_value_num"),
                    confidence=tag_data.get("confidence", 0.5),
                )
                session.add(tag)

        # Create company event
        event_type = _map_filing_to_event_type(filing_type)
        if event_type:
            event = CompanyEvent(
                company_id=company.id,
                event_type=event_type,
                event_timestamp=filed_at,
                source_type="edgar_filing",
                source_id=str(new_filing.id),
                metadata_json={
                    "filing_type": filing_type,
                    "accession_number": accession,
                },
            )
            session.add(event)

        recent_filings.append(new_filing)

    await session.commit()
    return recent_filings


def _map_filing_to_event_type(filing_type: str) -> str:
    """Map filing type to company event type."""
    mapping = {
        "S-1": EventType.SHELF_FILING,
        "S-1/A": EventType.AMENDMENT_FILING,
        "424B3": EventType.PROSPECTUS_FILING,
        "424B4": EventType.PROSPECTUS_FILING,
        "424B5": EventType.PROSPECTUS_FILING,
        "8-K": EventType.FINANCING_8K,
        "10-Q": EventType.FINANCING_FILING,
        "10-K": EventType.FINANCING_FILING,
    }
    return mapping.get(filing_type, EventType.FINANCING_FILING)
