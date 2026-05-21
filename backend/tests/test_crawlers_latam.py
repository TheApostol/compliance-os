"""
LATAM Crawler unit tests — CMFCrawler (Chile), SFCCrawler (Colombia), CNBVCrawler (Mexico).

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
# CMF (Chile)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCMFCrawler:
    """Test CMFCrawler — all external I/O mocked."""

    def _crawler(self):
        from app.modules.crawler.cmf_crawler import CMFCrawler
        return CMFCrawler()

    def test_cmf_fallback_entries(self):
        """Fallback returns exactly 5 entries with correct country code CL."""
        from app.modules.crawler.cmf_crawler import CMFCrawler, CMF_FALLBACK_URLS

        crawler = CMFCrawler()
        entries = crawler._fallback_entries()

        assert len(entries) == 5
        assert len(entries) == len(CMF_FALLBACK_URLS)
        assert crawler.country == "CL"
        assert all("fallback" in e.title for e in entries)
        assert all(e.url.startswith("https://www.cmfchile.cl") for e in entries)

    def test_cmf_strategy1_pdf_links(self):
        """Strategy 1: anchors with .pdf hrefs are found."""
        html = """
        <html><body>
          <a href="/portal/principal/613/articles-53621_doc.pdf">Circular 3621</a>
          <a href="/portal/principal/613/articles-53622_doc.pdf">Circular 3622</a>
          <a href="/portal/principal/613/articles-53623_doc.pdf">Circular 3623</a>
          <a href="/portal/principal/613/articles-53624_doc.pdf">Circular 3624</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) >= 3
        urls = [e.url for e in entries]
        assert any("53621" in u for u in urls)
        assert any("53622" in u for u in urls)

    @pytest.mark.asyncio
    async def test_cmf_nonblocking_on_404(self):
        """Non-200 response returns fallback entries without raising."""
        from app.modules.crawler.cmf_crawler import CMF_FALLBACK_URLS

        crawler = self._crawler()
        with patch.object(
            type(crawler), "_get",
            new=AsyncMock(return_value=_make_response(404)),
        ):
            entries = await crawler.fetch_index()

        assert len(entries) == len(CMF_FALLBACK_URLS)
        assert all("fallback" in e.title for e in entries)

    def test_cmf_keyword_detection(self):
        """Anchor with CMF-specific keyword (NCG) in text is detected."""
        html = """
        <html><body>
          <a href="/normativa/ncg-123">NCG 123 sobre valores</a>
          <a href="/normativa/ncg-124">NCG 124 sobre seguros</a>
          <a href="/normativa/ncg-125">NCG 125 sobre fondos</a>
          <a href="/other">Inicio</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        urls = [e.url for e in entries]
        assert any("ncg-123" in u for u in urls)
        assert any("ncg-124" in u for u in urls)
        assert not any("other" in u for u in urls)


# ═══════════════════════════════════════════════════════════════════════════════
# SFC (Colombia)
# ═══════════════════════════════════════════════════════════════════════════════


class TestSFCCrawler:
    """Test SFCCrawler — all external I/O mocked."""

    def _crawler(self):
        from app.modules.crawler.sfc_crawler import SFCCrawler
        return SFCCrawler()

    def test_sfc_fallback_entries(self):
        """Fallback returns exactly 5 entries with correct country code CO."""
        from app.modules.crawler.sfc_crawler import SFCCrawler, SFC_FALLBACK_URLS

        crawler = SFCCrawler()
        entries = crawler._fallback_entries()

        assert len(entries) == 5
        assert len(entries) == len(SFC_FALLBACK_URLS)
        assert crawler.country == "CO"
        assert all("fallback" in e.title for e in entries)
        assert all(e.url.startswith("https://www.superfinanciera.gov.co") for e in entries)

    def test_sfc_strategy1_pdf_links(self):
        """Strategy 1: anchors with .pdf hrefs are found."""
        html = """
        <html><body>
          <a href="/descargas?com=institucional&name=pubFile10097650&downloadname=10097650.pdf">CE 001</a>
          <a href="/descargas?com=institucional&name=pubFile10097651&downloadname=10097651.pdf">CE 002</a>
          <a href="/descargas?com=institucional&name=pubFile10097652&downloadname=10097652.pdf">CE 003</a>
          <a href="/descargas?com=institucional&name=pubFile10097653&downloadname=10097653.pdf">CE 004</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) >= 3
        urls = [e.url for e in entries]
        assert any("10097650" in u for u in urls)
        assert any("10097651" in u for u in urls)

    @pytest.mark.asyncio
    async def test_sfc_nonblocking_on_404(self):
        """Non-200 response returns fallback entries without raising."""
        from app.modules.crawler.sfc_crawler import SFC_FALLBACK_URLS

        crawler = self._crawler()
        with patch.object(
            type(crawler), "_get",
            new=AsyncMock(return_value=_make_response(404)),
        ):
            entries = await crawler.fetch_index()

        assert len(entries) == len(SFC_FALLBACK_URLS)
        assert all("fallback" in e.title for e in entries)

    def test_sfc_keyword_detection(self):
        """Anchor with SFC-specific keyword (Circular) in text is detected."""
        html = """
        <html><body>
          <a href="/normativa/ce-001">Circular Externa 001 de 2024</a>
          <a href="/normativa/ce-002">Circular Externa 002 de 2024</a>
          <a href="/normativa/ce-003">Circular Externa 003 de 2024</a>
          <a href="/other">Inicio</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        urls = [e.url for e in entries]
        assert any("ce-001" in u for u in urls)
        assert any("ce-002" in u for u in urls)
        assert not any("other" in u for u in urls)


# ═══════════════════════════════════════════════════════════════════════════════
# CNBV (Mexico)
# ═══════════════════════════════════════════════════════════════════════════════


class TestCNBVCrawler:
    """Test CNBVCrawler — all external I/O mocked."""

    def _crawler(self):
        from app.modules.crawler.cnbv_crawler import CNBVCrawler
        return CNBVCrawler()

    def test_cnbv_fallback_entries(self):
        """Fallback returns exactly 5 entries with correct country code MX."""
        from app.modules.crawler.cnbv_crawler import CNBVCrawler, CNBV_FALLBACK_URLS

        crawler = CNBVCrawler()
        entries = crawler._fallback_entries()

        assert len(entries) == 5
        assert len(entries) == len(CNBV_FALLBACK_URLS)
        assert crawler.country == "MX"
        assert all("fallback" in e.title for e in entries)
        assert all(e.url.startswith("https://www.cnbv.gob.mx") for e in entries)

    def test_cnbv_strategy1_pdf_links(self):
        """Strategy 1: anchors with .pdf hrefs are found."""
        html = """
        <html><body>
          <a href="/SECTORES-SUPERVISADOS/BANCA-MULTIPLE/Disposiciones/Documents/Circular1.pdf">Circular 1</a>
          <a href="/SECTORES-SUPERVISADOS/BANCA-MULTIPLE/Disposiciones/Documents/Circular2.pdf">Circular 2</a>
          <a href="/SECTORES-SUPERVISADOS/BANCA-MULTIPLE/Disposiciones/Documents/Circular3.pdf">Circular 3</a>
          <a href="/SECTORES-SUPERVISADOS/BANCA-MULTIPLE/Disposiciones/Documents/Circular4.pdf">Circular 4</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) >= 3
        urls = [e.url for e in entries]
        assert any("Circular1.pdf" in u for u in urls)
        assert any("Circular2.pdf" in u for u in urls)

    @pytest.mark.asyncio
    async def test_cnbv_nonblocking_on_404(self):
        """Non-200 response returns fallback entries without raising."""
        from app.modules.crawler.cnbv_crawler import CNBV_FALLBACK_URLS

        crawler = self._crawler()
        with patch.object(
            type(crawler), "_get",
            new=AsyncMock(return_value=_make_response(404)),
        ):
            entries = await crawler.fetch_index()

        assert len(entries) == len(CNBV_FALLBACK_URLS)
        assert all("fallback" in e.title for e in entries)

    def test_cnbv_keyword_detection(self):
        """Anchor with CNBV-specific keyword (CUB) in text is detected."""
        html = """
        <html><body>
          <a href="/disposiciones/cub-2024">CUB Circular Única de Bancos 2024</a>
          <a href="/disposiciones/cub-2023">CUB Circular Única de Bancos 2023</a>
          <a href="/disposiciones/cub-2022">CUB Circular Única de Bancos 2022</a>
          <a href="/other">Inicio</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        urls = [e.url for e in entries]
        assert any("cub-2024" in u for u in urls)
        assert any("cub-2023" in u for u in urls)
        assert not any("other" in u for u in urls)
