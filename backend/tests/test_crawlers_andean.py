"""
Andean Crawler unit tests — SBSPECrawler (Peru), SBSECCrawler (Ecuador), BCUCrawler (Uruguay).

All external I/O (HTTP, DB) is mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest


# ── test helpers ──────────────────────────────────────────────────────────────


def _make_response(status_code: int = 200, text: str = "", content: bytes = b"") -> httpx.Response:
    """Build a minimal httpx.Response without making a real request."""
    return httpx.Response(
        status_code=status_code,
        content=content or text.encode(),
        headers={"content-type": "text/html; charset=utf-8"},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SBS Peru (PE)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSBSPECrawler:
    """Test SBSPECrawler — all external I/O mocked."""

    def _crawler(self):
        from app.modules.crawler.sbs_pe_crawler import SBSPECrawler
        return SBSPECrawler()

    def test_sbs_pe_fallback_entries(self):
        """Fallback returns exactly 5 entries with correct country code PE."""
        from app.modules.crawler.sbs_pe_crawler import SBSPECrawler, SBS_PE_FALLBACK_URLS

        crawler = SBSPECrawler()
        entries = crawler._fallback_entries()

        assert len(entries) == 5
        assert len(entries) == len(SBS_PE_FALLBACK_URLS)
        assert crawler.country == "PE"
        assert all("fallback" in e.title for e in entries)
        assert all(e.url.startswith("https://www.sbs.gob.pe") for e in entries)

    def test_sbs_pe_strategy1_pdf_links(self):
        """Strategy 1: anchors with .pdf hrefs are found."""
        html = """
        <html><body>
          <a href="/portals/0/jer/REGULA_BANCARIA_PDF/Circular-B-2227-2020.pdf">Circular B-2227-2020</a>
          <a href="/portals/0/jer/REGULA_BANCARIA_PDF/Circular-B-2228-2020.pdf">Circular B-2228-2020</a>
          <a href="/portals/0/jer/REGULA_BANCARIA_PDF/Circular-B-2229-2021.pdf">Circular B-2229-2021</a>
          <a href="/portals/0/jer/REGULA_BANCARIA_PDF/Circular-B-2230-2021.pdf">Circular B-2230-2021</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) >= 3
        urls = [e.url for e in entries]
        assert any("2227-2020" in u for u in urls)
        assert any("2228-2020" in u for u in urls)

    @pytest.mark.asyncio
    async def test_sbs_pe_nonblocking_on_404(self):
        """Non-200 response returns fallback entries without raising."""
        from app.modules.crawler.sbs_pe_crawler import SBS_PE_FALLBACK_URLS

        crawler = self._crawler()
        with patch.object(
            type(crawler), "_get",
            new=AsyncMock(return_value=_make_response(404)),
        ):
            entries = await crawler.fetch_index()

        assert len(entries) == len(SBS_PE_FALLBACK_URLS)
        assert all("fallback" in e.title for e in entries)

    def test_sbs_pe_keyword_detection(self):
        """Anchor with SBS-PE-specific keyword (Circular, Resolución) in text is detected."""
        html = """
        <html><body>
          <a href="/normativa/circular-001">Circular B-2227 sobre encaje</a>
          <a href="/normativa/resolucion-001">Resolución SBS N° 001-2024</a>
          <a href="/normativa/circular-002">Circular B-2228 sobre riesgo</a>
          <a href="/other">Inicio</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        urls = [e.url for e in entries]
        assert any("circular-001" in u for u in urls)
        assert any("resolucion-001" in u for u in urls)
        assert not any("/other" in u for u in urls)


# ═══════════════════════════════════════════════════════════════════════════════
# SBES Ecuador (EC)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSBSECCrawler:
    """Test SBSECCrawler — all external I/O mocked."""

    def _crawler(self):
        from app.modules.crawler.sbs_ec_crawler import SBSECCrawler
        return SBSECCrawler()

    def test_sbs_ec_fallback_entries(self):
        """Fallback returns exactly 5 entries with correct country code EC."""
        from app.modules.crawler.sbs_ec_crawler import SBSECCrawler, SBS_EC_FALLBACK_URLS

        crawler = SBSECCrawler()
        entries = crawler._fallback_entries()

        assert len(entries) == 5
        assert len(entries) == len(SBS_EC_FALLBACK_URLS)
        assert crawler.country == "EC"
        assert all("fallback" in e.title for e in entries)
        assert all(e.url.startswith("https://www.superbancos.gob.ec") for e in entries)

    def test_sbs_ec_strategy1_pdf_links(self):
        """Strategy 1: anchors with .pdf hrefs are found."""
        html = """
        <html><body>
          <a href="/bancos/wp-content/uploads/downloads/2023/01/resolucion-2023-001.pdf">Resolución 001-2023</a>
          <a href="/bancos/wp-content/uploads/downloads/2023/02/resolucion-2023-002.pdf">Resolución 002-2023</a>
          <a href="/bancos/wp-content/uploads/downloads/2023/03/resolucion-2023-003.pdf">Resolución 003-2023</a>
          <a href="/bancos/wp-content/uploads/downloads/2023/04/resolucion-2023-004.pdf">Resolución 004-2023</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) >= 3
        urls = [e.url for e in entries]
        assert any("001.pdf" in u for u in urls)
        assert any("002.pdf" in u for u in urls)

    @pytest.mark.asyncio
    async def test_sbs_ec_nonblocking_on_404(self):
        """Non-200 response returns fallback entries without raising."""
        from app.modules.crawler.sbs_ec_crawler import SBS_EC_FALLBACK_URLS

        crawler = self._crawler()
        with patch.object(
            type(crawler), "_get",
            new=AsyncMock(return_value=_make_response(404)),
        ):
            entries = await crawler.fetch_index()

        assert len(entries) == len(SBS_EC_FALLBACK_URLS)
        assert all("fallback" in e.title for e in entries)

    def test_sbs_ec_keyword_detection(self):
        """Anchor with SBES-specific keyword (Resolución, Circular, Norma) in text is detected."""
        html = """
        <html><body>
          <a href="/normativa/res-001">Resolución No. SB-2024-001</a>
          <a href="/normativa/circ-001">Circular 001 de 2024</a>
          <a href="/normativa/norma-001">Norma de solvencia 2024</a>
          <a href="/other">Inicio</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        urls = [e.url for e in entries]
        assert any("res-001" in u for u in urls)
        assert any("circ-001" in u for u in urls)
        assert not any("/other" in u for u in urls)


# ═══════════════════════════════════════════════════════════════════════════════
# BCU Uruguay (UY)
# ═══════════════════════════════════════════════════════════════════════════════


class TestBCUCrawler:
    """Test BCUCrawler — all external I/O mocked."""

    def _crawler(self):
        from app.modules.crawler.bcu_crawler import BCUCrawler
        return BCUCrawler()

    def test_bcu_fallback_entries(self):
        """Fallback returns exactly 5 entries with correct country code UY."""
        from app.modules.crawler.bcu_crawler import BCUCrawler, BCU_FALLBACK_URLS

        crawler = BCUCrawler()
        entries = crawler._fallback_entries()

        assert len(entries) == 5
        assert len(entries) == len(BCU_FALLBACK_URLS)
        assert crawler.country == "UY"
        assert all("fallback" in e.title for e in entries)
        assert all(e.url.startswith("https://www.bcu.gub.uy") for e in entries)

    def test_bcu_strategy1_pdf_links(self):
        """Strategy 1: anchors with .pdf hrefs are found."""
        html = """
        <html><body>
          <a href="/Servicios-Financieros-SSF/Circulares/Circular2380.pdf">Circular 2380</a>
          <a href="/Servicios-Financieros-SSF/Circulares/Circular2381.pdf">Circular 2381</a>
          <a href="/Servicios-Financieros-SSF/Circulares/Circular2382.pdf">Circular 2382</a>
          <a href="/Servicios-Financieros-SSF/Circulares/Circular2383.pdf">Circular 2383</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) >= 3
        urls = [e.url for e in entries]
        assert any("Circular2380" in u for u in urls)
        assert any("Circular2381" in u for u in urls)

    @pytest.mark.asyncio
    async def test_bcu_nonblocking_on_404(self):
        """Non-200 response returns fallback entries without raising."""
        from app.modules.crawler.bcu_crawler import BCU_FALLBACK_URLS

        crawler = self._crawler()
        with patch.object(
            type(crawler), "_get",
            new=AsyncMock(return_value=_make_response(404)),
        ):
            entries = await crawler.fetch_index()

        assert len(entries) == len(BCU_FALLBACK_URLS)
        assert all("fallback" in e.title for e in entries)

    def test_bcu_keyword_detection(self):
        """Anchor with BCU-specific keyword (Circular, Comunicación) in text is detected."""
        html = """
        <html><body>
          <a href="/circulares/circular-2380">Circular 2380 sobre liquidez</a>
          <a href="/circulares/circular-2381">Circular 2381 sobre capital</a>
          <a href="/comunicaciones/com-001">Comunicación 001 de 2024</a>
          <a href="/other">Inicio</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        urls = [e.url for e in entries]
        assert any("circular-2380" in u for u in urls)
        assert any("circular-2381" in u for u in urls)
        assert not any("/other" in u for u in urls)
