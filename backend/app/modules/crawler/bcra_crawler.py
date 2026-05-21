"""
BCRA Crawler — Banco Central de la República Argentina
========================================================
Fetches Comunicaciones (A, B, C series) from BCRA's publication index.
Index URL: https://www.bcra.gob.ar/SistemasFinancieros/sf_comunicaciones.asp
PDFs served at: https://www.bcra.gob.ar/Pdfs/comytexord/<ID>.pdf
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from app.modules.crawler.base_crawler import BaseCrawler, IndexEntry

logger = logging.getLogger(__name__)

BCRA_INDEX_URL = "https://www.bcra.gob.ar/SistemasFinancieros/sf_comunicaciones.asp"
BCRA_PDF_BASE  = "https://www.bcra.gob.ar/Pdfs/comytexord/"

# Known-good fallback: last 5 Com. A series entries (A7890–A7894)
# Used when the index page is unavailable or returns a non-200 status.
BCRA_FALLBACK_URLS: list[str] = [
    f"https://www.bcra.gob.ar/Pdfs/comytexord/A{num}.pdf"
    for num in range(7890, 7895)
]


class BCRACrawler(BaseCrawler):
    def __init__(self):
        super().__init__(regulator="BCRA", country="AR")

    async def fetch_index(self) -> list[IndexEntry]:
        """Scrape BCRA communications index and return up to 50 recent entries.

        Falls back to a hardcoded list of recent known-good URLs if the index
        page is unavailable or returns a non-200 status.
        """
        try:
            resp = await self._get(BCRA_INDEX_URL)
        except Exception as e:
            logger.warning("BCRA index network error — using fallback URLs: %s", e)
            return self._fallback_entries()

        if resp.status_code != 200:
            logger.warning(
                "BCRA index returned HTTP %s — using fallback URLs", resp.status_code
            )
            return self._fallback_entries()

        entries = self._parse_index_html(resp.text)
        if not entries:
            logger.warning("BCRA index parsed 0 entries — using fallback URLs")
            return self._fallback_entries()

        return entries

    @staticmethod
    def _fallback_entries() -> list[IndexEntry]:
        """Return IndexEntry objects for the hardcoded fallback PDF URLs."""
        return [
            IndexEntry(
                url=url,
                title=f"Com. A {url.split('A')[-1].replace('.pdf', '')} (fallback)",
            )
            for url in BCRA_FALLBACK_URLS
        ]

    def _parse_index_html(self, html: str) -> list[IndexEntry]:
        # Strategy 1: look for PDF links anywhere in the page
        entries = self._strategy_pdf_links(html)
        if len(entries) >= 3:
            return entries[:50]
        # Strategy 2: table row parsing (original approach)
        entries = self._strategy_table_rows(html)
        if len(entries) >= 3:
            return entries[:50]
        # Strategy 3: any anchor with "comunicacion" or "com" in href
        entries = self._strategy_anchor_text(html)
        return entries[:50]

    def _strategy_pdf_links(self, html: str) -> list[IndexEntry]:
        """Strategy 1: find all href ending in .pdf or /pdf and extract surrounding text."""
        entries: list[IndexEntry] = []
        # Match anchors whose href ends in .pdf (case-insensitive)
        pattern = re.compile(
            r'<a\s[^>]*href="([^"]*\.pdf)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(html):
            href = match.group(1).strip()
            anchor_text = re.sub(r"<[^>]+>", "", match.group(2)).strip()

            # Also try to pick up surrounding text if anchor text is thin
            url = href if href.startswith("http") else f"https://www.bcra.gob.ar{href}"
            title = anchor_text if anchor_text else url.split("/")[-1].replace(".pdf", "")

            pub_date = self._extract_date(match.group(0))
            entries.append(IndexEntry(url=url, title=title, published_at=pub_date))

        return self._deduplicate(entries)

    def _strategy_table_rows(self, html: str) -> list[IndexEntry]:
        """Strategy 2: original table row parsing approach."""
        entries: list[IndexEntry] = []
        rows = re.findall(
            r"<tr[^>]*>.*?</tr>",
            html,
            re.DOTALL | re.IGNORECASE,
        )
        for row in rows:
            # Extract PDF link
            pdf_match = re.search(
                r'href="([^"]*(?:Pdfs|pdfs)[^"]*\.pdf)"',
                row,
                re.IGNORECASE,
            )
            if not pdf_match:
                continue
            pdf_path = pdf_match.group(1)
            url = pdf_path if pdf_path.startswith("http") else f"https://www.bcra.gob.ar{pdf_path}"

            # Extract communication number / title from cell text
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
            cell_texts = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
            cell_texts = [t for t in cell_texts if t]

            if len(cell_texts) >= 2:
                serie_num = " ".join(cell_texts[:2])
                subject = cell_texts[3] if len(cell_texts) > 3 else ""
                title = f"Com. {serie_num} — {subject}" if subject else f"Com. {serie_num}"
            else:
                title = url.split("/")[-1].replace(".pdf", "")

            pub_date = self._extract_date(row)
            entries.append(IndexEntry(url=url, title=title, published_at=pub_date))

        return self._deduplicate(entries)

    def _strategy_anchor_text(self, html: str) -> list[IndexEntry]:
        """Strategy 3: find anchors whose text matches Com. [ABC] <number> pattern."""
        entries: list[IndexEntry] = []
        com_pattern = re.compile(r"Com\.\s*[ABC]\s*\d+", re.IGNORECASE)
        anchor_pattern = re.compile(
            r'<a\s[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        for match in anchor_pattern.finditer(html):
            anchor_text = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if not com_pattern.search(anchor_text):
                continue
            href = match.group(1).strip()
            url = href if href.startswith("http") else f"https://www.bcra.gob.ar{href}"
            pub_date = self._extract_date(match.group(0))
            entries.append(IndexEntry(url=url, title=anchor_text, published_at=pub_date))

        return self._deduplicate(entries)

    @staticmethod
    def _extract_date(text: str) -> datetime | None:
        date_match = re.search(r"(\d{2}/\d{2}/\d{4})", text)
        if date_match:
            try:
                return datetime.strptime(date_match.group(1), "%d/%m/%Y")
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
