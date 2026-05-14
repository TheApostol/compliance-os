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
        resp = await self._get(UIF_INDEX_URL)
        resp.raise_for_status()
        return self._parse_index_html(resp.text)

    def _parse_index_html(self, html: str) -> list[IndexEntry]:
        entries: list[IndexEntry] = []

        # UIF index lists links like: <a href="/uif/...">Resolución UIF N° 30/2017</a>
        pattern = re.compile(
            r'<a\s+href="([^"]*(?:normativa|resolucion|res_uif)[^"]*)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        for match in pattern.finditer(html):
            href = match.group(1).strip()
            link_text = re.sub(r'<[^>]+>', '', match.group(2)).strip()

            if not link_text or len(link_text) < 5:
                continue

            url = href if href.startswith("http") else f"{UIF_BASE_URL}{href}"

            # Try to extract date from link text (e.g. "Res. 30/2017" → year only)
            year_match = re.search(r'/(\d{4})', link_text)
            pub_date = None
            if year_match:
                try:
                    pub_date = datetime(int(year_match.group(1)), 1, 1)
                except ValueError:
                    pass

            entries.append(IndexEntry(url=url, title=link_text, published_at=pub_date))

        # Deduplicate by URL
        seen: set[str] = set()
        unique: list[IndexEntry] = []
        for e in entries:
            if e.url not in seen:
                seen.add(e.url)
                unique.append(e)

        return unique[:50]

    async def fetch_document(self, url: str) -> tuple[bytes, str]:
        resp = await self._get(url)
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        doc_type = "pdf" if "pdf" in content_type else "html"
        return resp.content, doc_type
