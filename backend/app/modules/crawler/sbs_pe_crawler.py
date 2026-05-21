"""
SBS Crawler — Superintendencia de Banca, Seguros y AFP (Peru)
==============================================================
Fetches Circulares and Resoluciones from SBS's regulatory index.
Index URL: https://www.sbs.gob.pe/regulacion/tipo/circulares
PDFs served at: https://www.sbs.gob.pe
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from app.modules.crawler.base_crawler import BaseCrawler, IndexEntry

logger = logging.getLogger(__name__)

SBS_PE_INDEX_URL = "https://www.sbs.gob.pe/regulacion/tipo/circulares"
SBS_PE_PDF_BASE  = "https://www.sbs.gob.pe"

# Known-good fallback: 5 SBS Peru circulars
# Used when the index page is unavailable or returns a non-200 status.
SBS_PE_FALLBACK_URLS: list[str] = [
    f"https://www.sbs.gob.pe/portals/0/jer/REGULA_BANCARIA_PDF/Circular-B-{num}.pdf"
    for num in ["2227-2020", "2228-2020", "2229-2021", "2230-2021", "2231-2022"]
]


class SBSPECrawler(BaseCrawler):
    def __init__(self):
        super().__init__(regulator="SBS", country="PE")

    async def fetch_index(self) -> list[IndexEntry]:
        """Scrape SBS Peru normatives index and return up to 50 recent entries.

        Falls back to a hardcoded list of recent known-good URLs if the index
        page is unavailable or returns a non-200 status.
        """
        try:
            resp = await self._get(SBS_PE_INDEX_URL)
        except Exception as e:
            logger.warning("SBS-PE index network error — using fallback URLs: %s", e)
            return self._fallback_entries()

        if resp.status_code != 200:
            logger.warning(
                "SBS-PE index returned HTTP %s — using fallback URLs", resp.status_code
            )
            return self._fallback_entries()

        entries = self._parse_index_html(resp.text)
        if not entries:
            logger.warning("SBS-PE index parsed 0 entries — using fallback URLs")
            return self._fallback_entries()

        return entries

    @staticmethod
    def _fallback_entries() -> list[IndexEntry]:
        """Return IndexEntry objects for the hardcoded fallback PDF URLs."""
        return [
            IndexEntry(
                url=url,
                title=f"SBS {url.split('Circular-')[-1].replace('.pdf', '')} (fallback)",
            )
            for url in SBS_PE_FALLBACK_URLS
        ]

    def _parse_index_html(self, html: str) -> list[IndexEntry]:
        # Strategy 1: look for PDF links anywhere in the page
        entries = self._strategy_pdf_links(html)
        if len(entries) >= 3:
            return entries[:50]
        # Strategy 2: table row parsing — rows containing Circular/Resolución keywords
        entries = self._strategy_table_rows(html)
        if len(entries) >= 3:
            return entries[:50]
        # Strategy 3: anchors matching Circular/Resolución number pattern
        entries = self._strategy_anchor_text(html)
        return entries[:50]

    def _strategy_pdf_links(self, html: str) -> list[IndexEntry]:
        """Strategy 1: find all href ending in .pdf and extract surrounding text."""
        entries: list[IndexEntry] = []
        pattern = re.compile(
            r'<a\s[^>]*href="([^"]*\.pdf)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(html):
            href = match.group(1).strip()
            anchor_text = re.sub(r"<[^>]+>", "", match.group(2)).strip()

            url = href if href.startswith("http") else f"{SBS_PE_PDF_BASE}{href}"
            title = anchor_text if anchor_text else url.split("/")[-1].replace(".pdf", "")

            pub_date = self._extract_date(match.group(0))
            entries.append(IndexEntry(url=url, title=title, published_at=pub_date))

        return self._deduplicate(entries)

    def _strategy_table_rows(self, html: str) -> list[IndexEntry]:
        """Strategy 2: find table rows containing Circular/Resolución keywords."""
        entries: list[IndexEntry] = []
        rows = re.findall(
            r"<tr[^>]*>.*?</tr>",
            html,
            re.DOTALL | re.IGNORECASE,
        )
        keyword_pattern = re.compile(
            r"Circular|Resoluci[oó]n|Resolucio|Oficio",
            re.IGNORECASE,
        )
        for row in rows:
            if not keyword_pattern.search(row):
                continue

            # Extract any link in the row
            link_match = re.search(r'href="([^"]+)"', row, re.IGNORECASE)
            if not link_match:
                continue

            href = link_match.group(1)
            url = href if href.startswith("http") else f"{SBS_PE_PDF_BASE}{href}"

            # Extract title from cell text
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
            cell_texts = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
            cell_texts = [t for t in cell_texts if t]

            if cell_texts:
                title = " — ".join(cell_texts[:2]) if len(cell_texts) >= 2 else cell_texts[0]
            else:
                title = url.split("/")[-1].replace(".pdf", "")

            pub_date = self._extract_date(row)
            entries.append(IndexEntry(url=url, title=title, published_at=pub_date))

        return self._deduplicate(entries)

    def _strategy_anchor_text(self, html: str) -> list[IndexEntry]:
        """Strategy 3: find anchors whose text matches Circular/Resolución SBS pattern."""
        entries: list[IndexEntry] = []
        norm_pattern = re.compile(
            r"Circular\s*[A-Z]-\d+|Resoluci[oó]n\s*SBS|Circular|Resoluci[oó]n|Resolucio|Oficio",
            re.IGNORECASE,
        )
        anchor_pattern = re.compile(
            r'<a\s[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        for match in anchor_pattern.finditer(html):
            anchor_text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if not norm_pattern.search(anchor_text):
                continue
            href = match.group(1).strip()
            url = href if href.startswith("http") else f"{SBS_PE_PDF_BASE}{href}"
            pub_date = self._extract_date(match.group(0))
            entries.append(IndexEntry(url=url, title=anchor_text, published_at=pub_date))

        return self._deduplicate(entries)

    @staticmethod
    def _extract_date(text: str) -> datetime | None:
        # Try dd/mm/yyyy first
        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        if date_match:
            try:
                return datetime.strptime(date_match.group(1), "%d/%m/%Y")
            except ValueError:
                pass
        # Also try ISO yyyy-mm-dd format
        iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
        if iso_match:
            try:
                return datetime.strptime(iso_match.group(1), "%Y-%m-%d")
            except ValueError:
                pass
        return None

    @staticmethod
    def _deduplicate(entries: list[IndexEntry]) -> list[IndexEntry]:
        seen: set[str] = set()
        unique: list[IndexEntry] = []
        for e in entries:
            if e.url not in seen:
                seen.add(e.url)
                unique.append(e)
        return unique

    async def fetch_document(self, url: str) -> tuple[bytes, str]:
        resp = await self._get(url)
        resp.raise_for_status()
        return resp.content, "pdf"
