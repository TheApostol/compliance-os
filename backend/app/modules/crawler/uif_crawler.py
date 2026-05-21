"""
UIF Crawler — Unidad de Información Financiera (Argentina)
===========================================================
Fetches Resoluciones from UIF's normativa index.
Index URL: https://www.uif.gob.ar/uif/index.php/es/normativa
Documents are served as HTML pages or linked PDFs.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime

from app.modules.crawler.base_crawler import BaseCrawler, IndexEntry

logger = logging.getLogger(__name__)

UIF_INDEX_URL = "https://www.uif.gob.ar/uif/index.php/es/normativa"
UIF_BASE_URL  = "https://www.uif.gob.ar"


class UIFCrawler(BaseCrawler):
    def __init__(self):
        super().__init__(regulator="UIF", country="AR")

    async def fetch_index(self) -> list[IndexEntry]:
        """Scrape UIF normativa index. Returns empty list on non-200 (logs warning)."""
        try:
            resp = await self._get(UIF_INDEX_URL)
        except Exception as e:
            logger.warning("UIF index network error: %s", e)
            return []

        if resp.status_code != 200:
            logger.warning("UIF index returned HTTP %s — skipping run", resp.status_code)
            return []

        return self._parse_index_html(resp.text)

    def _parse_index_html(self, html: str) -> list[IndexEntry]:
        entries: list[IndexEntry] = []

        # Collect all <a href="...">...</a> matches
        anchor_pattern = re.compile(
            r'<a\s[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )

        # Anchor text keywords that signal a regulatory document
        text_keywords = re.compile(
            r"Resoluci[oó]n|Resoluciones|Circular|\d{4}",
            re.IGNORECASE,
        )

        for match in anchor_pattern.finditer(html):
            href = match.group(1).strip()
            link_text = re.sub(r"<[^>]+>", "", match.group(2)).strip()

            # Accept the link if EITHER:
            #   (a) href ends with .pdf  OR
            #   (b) anchor text contains regulatory keywords
            is_pdf_link = bool(re.search(r"\.pdf$", href, re.IGNORECASE))
            is_keyword_match = bool(text_keywords.search(link_text))

            if not (is_pdf_link or is_keyword_match):
                continue

            if not link_text or len(link_text) < 3:
                link_text = href.rstrip("/").split("/")[-1]

            url = href if href.startswith("http") else f"{UIF_BASE_URL}{href}"

            # Try to extract date — year from link text (e.g. "Res. 30/2017" → 2017)
            pub_date = self._extract_year(link_text)

            entries.append(IndexEntry(url=url, title=link_text, published_at=pub_date))

        return self._deduplicate(entries)[:50]

    @staticmethod
    def _extract_year(text: str) -> datetime | None:
        year_match = re.search(r"/(\d{4})", text)
        if year_match:
            try:
                return datetime(int(year_match.group(1)), 1, 1)
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
        content_type = resp.headers.get("content-type", "")
        doc_type = "pdf" if "pdf" in content_type else "html"
        return resp.content, doc_type
