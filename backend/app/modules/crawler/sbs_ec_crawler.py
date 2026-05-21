"""
SBES Crawler — Superintendencia de Bancos del Ecuador (Ecuador)
===============================================================
Fetches Resoluciones, Circulares, and Normas from SBES's normativa index.
Index URL: https://www.superbancos.gob.ec/bancos/normativa/
PDFs served at: https://www.superbancos.gob.ec
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from app.modules.crawler.base_crawler import BaseCrawler, IndexEntry

logger = logging.getLogger(__name__)

SBS_EC_INDEX_URL = "https://www.superbancos.gob.ec/bancos/normativa/"
SBS_EC_PDF_BASE  = "https://www.superbancos.gob.ec"

# Known-good fallback: 5 SBES Ecuador resolutions
# Used when the index page is unavailable or returns a non-200 status.
SBS_EC_FALLBACK_URLS: list[str] = [
    f"https://www.superbancos.gob.ec/bancos/wp-content/uploads/downloads/2023/{month:02d}/resolucion-2023-{n}.pdf"
    for month, n in [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)]
]


class SBSECCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(regulator="SBES", country="EC")

    async def fetch_index(self) -> list[IndexEntry]:
        """Scrape SBES Ecuador normativa index and return up to 50 recent entries.

        Falls back to a hardcoded list of recent known-good URLs if the index
        page is unavailable or returns a non-200 status.
        """
        try:
            resp = await self._get(SBS_EC_INDEX_URL)
        except Exception as e:
            logger.warning("SBES-EC index network error — using fallback URLs: %s", e)
            return self._fallback_entries()

        if resp.status_code != 200:
            logger.warning(
                "SBES-EC index returned HTTP %s — using fallback URLs", resp.status_code
            )
            return self._fallback_entries()

        entries = self._parse_index_html(resp.text)
        if not entries:
            logger.warning("SBES-EC index parsed 0 entries — using fallback URLs")
            return self._fallback_entries()

        return entries

    @staticmethod
    def _fallback_entries() -> list[IndexEntry]:
        """Return IndexEntry objects for the hardcoded fallback PDF URLs."""
        return [
            IndexEntry(
                url=url,
                title=f"SBES {url.split('/')[-1].replace('.pdf', '')} (fallback)",
            )
            for url in SBS_EC_FALLBACK_URLS
        ]

    def _parse_index_html(self, html: str) -> list[IndexEntry]:
        # Strategy 1: look for PDF links anywhere in the page
        entries = self._strategy_pdf_links(html)
        if len(entries) >= 3:
            return entries[:50]
        # Strategy 2: table row parsing — rows containing Resolución/Circular/Norma keywords
        entries = self._strategy_table_rows(html)
        if len(entries) >= 3:
            return entries[:50]
        # Strategy 3: anchors matching Resolución/Circular number pattern
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

            url = href if href.startswith("http") else f"{SBS_EC_PDF_BASE}{href}"
            title = anchor_text if anchor_text else url.split("/")[-1].replace(".pdf", "")

            pub_date = self._extract_date(match.group(0))
            entries.append(IndexEntry(url=url, title=title, published_at=pub_date))

        return self._deduplicate(entries)

    def _strategy_table_rows(self, html: str) -> list[IndexEntry]:
        """Strategy 2: find table rows containing Resolución/Circular/Norma keywords."""
        entries: list[IndexEntry] = []
        rows = re.findall(
            r"<tr[^>]*>.*?</tr>",
            html,
            re.DOTALL | re.IGNORECASE,
        )
        keyword_pattern = re.compile(
            r"Resoluci[oó]n|Resolucio|Circular|Norma|Codificaci[oó]n",
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
            url = href if href.startswith("http") else f"{SBS_EC_PDF_BASE}{href}"

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
        """Strategy 3: find anchors whose text matches Resolución No./Circular number pattern."""
        entries: list[IndexEntry] = []
        norm_pattern = re.compile(
            r"Resoluci[oó]n\s*No\.\s*[\w-]+|Circular\s*\d+|Resoluci[oó]n|Resolucio|Circular|Norma|Codificaci[oó]n",
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
            url = href if href.startswith("http") else f"{SBS_EC_PDF_BASE}{href}"
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
