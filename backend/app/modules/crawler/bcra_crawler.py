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


class BCRACrawler(BaseCrawler):
    def __init__(self):
        super().__init__(regulator="BCRA", country="AR")

    async def fetch_index(self) -> list[IndexEntry]:
        """Scrape BCRA communications index and return up to 50 recent entries."""
        resp = await self._get(BCRA_INDEX_URL)
        resp.raise_for_status()
        return self._parse_index_html(resp.text)

    def _parse_index_html(self, html: str) -> list[IndexEntry]:
        entries: list[IndexEntry] = []
        # BCRA table rows contain: Serie | Número | Fecha | Asunto | PDF link
        # Pattern: <a href="...pdf">  or table cells with communication data
        rows = re.findall(
            r'<tr[^>]*>.*?</tr>',
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
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL | re.IGNORECASE)
            cell_texts = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            cell_texts = [t for t in cell_texts if t]

            if len(cell_texts) >= 2:
                serie_num = " ".join(cell_texts[:2])
                subject = cell_texts[3] if len(cell_texts) > 3 else ""
                title = f"Com. {serie_num} — {subject}" if subject else f"Com. {serie_num}"
            else:
                title = url.split("/")[-1].replace(".pdf", "")

            # Try to parse date
            date_match = re.search(r'(\d{2}/\d{2}/\d{4})', row)
            pub_date = None
            if date_match:
                try:
                    pub_date = datetime.strptime(date_match.group(1), "%d/%m/%Y")
                except ValueError:
                    pass

            entries.append(IndexEntry(url=url, title=title, published_at=pub_date))

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
        return resp.content, "pdf"
