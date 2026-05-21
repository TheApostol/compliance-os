"""
Crawler unit tests — BCRACrawler, UIFCrawler, BaseCrawler._get retry logic,
and _already_processed DB lookup.

All external I/O (HTTP, DB) is mocked.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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


# ── BCRA parser tests ─────────────────────────────────────────────────────────


class TestBCRAParseIndexHtml:
    """Test _parse_index_html with synthetic HTML — no network calls."""

    def _crawler(self):
        from app.modules.crawler.bcra_crawler import BCRACrawler
        return BCRACrawler()

    def test_strategy1_pdf_links(self):
        """Strategy 1: anchors with .pdf hrefs are found."""
        html = """
        <html><body>
          <a href="/Pdfs/comytexord/A7890.pdf">Com. A 7890</a>
          <a href="/Pdfs/comytexord/A7891.pdf">Com. A 7891</a>
          <a href="/Pdfs/comytexord/A7892.pdf">Com. A 7892</a>
          <a href="/Pdfs/comytexord/A7893.pdf">Com. A 7893</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) >= 3
        urls = [e.url for e in entries]
        assert any("A7890.pdf" in u for u in urls)
        assert any("A7891.pdf" in u for u in urls)

    def test_strategy2_table_rows(self):
        """Strategy 2: table rows with Pdfs links are parsed."""
        html = """
        <html><body><table>
          <tr>
            <td>A</td><td>7890</td><td>01/01/2025</td><td>Normas de liquidez</td>
            <td><a href="/Pdfs/comytexord/A7890.pdf">PDF</a></td>
          </tr>
          <tr>
            <td>A</td><td>7891</td><td>02/01/2025</td><td>Créditos</td>
            <td><a href="/Pdfs/comytexord/A7891.pdf">PDF</a></td>
          </tr>
          <tr>
            <td>A</td><td>7892</td><td>03/01/2025</td><td>Tasas</td>
            <td><a href="/Pdfs/comytexord/A7892.pdf">PDF</a></td>
          </tr>
        </table></body></html>
        """
        crawler = self._crawler()
        # Call strategy 2 directly — _parse_index_html would route via strategy 1 first
        entries = crawler._strategy_table_rows(html)
        assert len(entries) >= 3
        titles = [e.title for e in entries]
        assert any("7890" in t or "7891" in t for t in titles)

    def test_strategy3_anchor_text(self):
        """Strategy 3: anchors whose text matches Com. [ABC] <number>."""
        html = """
        <html><body>
          <a href="/page/A7890">Com. A 7890</a>
          <a href="/page/A7891">Com. A 7891</a>
          <a href="/page/A7892">Com. A 7892</a>
          <a href="/irrelevant">Otra cosa</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) >= 3
        titles = [e.title for e in entries]
        assert all(any(t.startswith("Com.") for t in titles) for _ in [1])

    def test_empty_html_returns_empty_list(self):
        """Empty HTML should produce no entries (no fallback in pure parse)."""
        crawler = self._crawler()
        entries = crawler._parse_index_html("")
        assert entries == []

    def test_deduplication(self):
        """Duplicate PDF hrefs should be deduplicated."""
        html = """
        <html><body>
          <a href="/Pdfs/comytexord/A7890.pdf">Com. A 7890</a>
          <a href="/Pdfs/comytexord/A7890.pdf">Com. A 7890 (copy)</a>
          <a href="/Pdfs/comytexord/A7891.pdf">Com. A 7891</a>
          <a href="/Pdfs/comytexord/A7892.pdf">Com. A 7892</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        urls = [e.url for e in entries]
        assert len(urls) == len(set(urls)), "Duplicate URLs found"

    def test_date_parsing(self):
        """Dates in dd/mm/yyyy format should be parsed into published_at."""
        html = """
        <html><body><table>
          <tr>
            <td>A</td><td>7890</td><td>15/03/2025</td><td>Test</td>
            <td><a href="/Pdfs/comytexord/A7890.pdf">PDF</a></td>
          </tr>
          <tr>
            <td>A</td><td>7891</td><td>16/03/2025</td><td>Test2</td>
            <td><a href="/Pdfs/comytexord/A7891.pdf">PDF</a></td>
          </tr>
          <tr>
            <td>A</td><td>7892</td><td>17/03/2025</td><td>Test3</td>
            <td><a href="/Pdfs/comytexord/A7892.pdf">PDF</a></td>
          </tr>
        </table></body></html>
        """
        crawler = self._crawler()
        # Call strategy 2 directly to test table-row date parsing
        entries = crawler._strategy_table_rows(html)
        dated = [e for e in entries if e.published_at is not None]
        assert len(dated) > 0
        assert dated[0].published_at.year == 2025  # type: ignore[union-attr]

    def test_result_capped_at_50(self):
        """Output should never exceed 50 entries."""
        rows = "".join(
            f'<a href="/Pdfs/comytexord/A{n}.pdf">Com. A {n}</a>'
            for n in range(7800, 7870)
        )
        html = f"<html><body>{rows}</body></html>"
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) <= 50


# ── BCRA fallback tests ───────────────────────────────────────────────────────


class TestBCRAFallback:
    def _crawler(self):
        from app.modules.crawler.bcra_crawler import BCRACrawler
        return BCRACrawler()

    @pytest.mark.asyncio
    async def test_fallback_on_network_error(self):
        """fetch_index() returns fallback entries on ConnectError."""
        from app.modules.crawler.bcra_crawler import BCRA_FALLBACK_URLS

        crawler = self._crawler()
        with patch.object(
            type(crawler), "_get",
            new=AsyncMock(side_effect=httpx.ConnectError("connection refused")),
        ):
            entries = await crawler.fetch_index()

        assert len(entries) == len(BCRA_FALLBACK_URLS)
        assert all("fallback" in e.title for e in entries)

    @pytest.mark.asyncio
    async def test_fallback_on_non_200(self):
        """fetch_index() returns fallback entries on 503."""
        from app.modules.crawler.bcra_crawler import BCRA_FALLBACK_URLS

        crawler = self._crawler()
        with patch.object(
            type(crawler), "_get",
            new=AsyncMock(return_value=_make_response(503)),
        ):
            entries = await crawler.fetch_index()

        assert len(entries) == len(BCRA_FALLBACK_URLS)


# ── UIF parser tests ──────────────────────────────────────────────────────────


class TestUIFParseIndexHtml:
    def _crawler(self):
        from app.modules.crawler.uif_crawler import UIFCrawler
        return UIFCrawler()

    def test_pdf_links_detected(self):
        """Any .pdf href should be picked up."""
        html = """
        <html><body>
          <a href="/uif/images/stories/res_30_2017.pdf">Resolución UIF N° 30/2017</a>
          <a href="/uif/attachments/circular_1_2023.pdf">Circular 1/2023</a>
          <a href="/uif/images/stories/res_15_2022.pdf">Resolución 15/2022</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) == 3
        assert all(e.url.endswith(".pdf") for e in entries)

    def test_keyword_links_detected(self):
        """Links with 'Resolución', 'Circular', or year pattern in text are found."""
        html = """
        <html><body>
          <a href="/normativa/res30">Resolución UIF N° 30/2017</a>
          <a href="/normativa/circ1">Circular 1/2023</a>
          <a href="/normativa/res15">Resoluciones vigentes 2022</a>
          <a href="/other">Nosotros</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        urls = [e.url for e in entries]
        assert any("res30" in u for u in urls)
        assert any("circ1" in u for u in urls)
        assert not any("other" in u for u in urls)

    def test_deduplication_by_url(self):
        """Duplicate URLs should appear only once."""
        html = """
        <html><body>
          <a href="/uif/res30.pdf">Resolución 30/2017</a>
          <a href="/uif/res30.pdf">Resolución 30/2017 (bis)</a>
          <a href="/uif/res31.pdf">Resolución 31/2017</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        urls = [e.url for e in entries]
        assert len(urls) == len(set(urls))

    def test_empty_html_returns_empty_list(self):
        crawler = self._crawler()
        entries = crawler._parse_index_html("")
        assert entries == []

    def test_year_extracted_from_link_text(self):
        """Year pattern in link text should populate published_at."""
        html = """
        <html><body>
          <a href="/uif/res30.pdf">Resolución 30/2019</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) == 1
        assert entries[0].published_at is not None
        assert entries[0].published_at.year == 2019

    def test_capped_at_50(self):
        """Output never exceeds 50 entries."""
        links = "".join(
            f'<a href="/uif/res_{n}.pdf">Resolución {n}/2022</a>'
            for n in range(1, 80)
        )
        html = f"<html><body>{links}</body></html>"
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) <= 50

    @pytest.mark.asyncio
    async def test_fetch_index_returns_empty_on_non_200(self):
        """fetch_index() should return [] and log warning (not raise) on non-200."""
        crawler = self._crawler()
        with patch.object(
            type(crawler), "_get",
            new=AsyncMock(return_value=_make_response(404)),
        ):
            entries = await crawler.fetch_index()
        assert entries == []

    @pytest.mark.asyncio
    async def test_fetch_index_returns_empty_on_network_error(self):
        """fetch_index() should return [] on network failure."""
        crawler = self._crawler()
        with patch.object(
            type(crawler), "_get",
            new=AsyncMock(side_effect=httpx.ConnectError("no route to host")),
        ):
            entries = await crawler.fetch_index()
        assert entries == []


# ── BaseCrawler._get retry logic ──────────────────────────────────────────────


class TestBaseGetRetry:
    """Test that _get retries on network errors and returns after eventual success."""

    @pytest.mark.asyncio
    async def test_succeeds_on_third_attempt(self):
        """Mock fails twice (ConnectError) then succeeds; _get should return response."""
        from app.modules.crawler.base_crawler import BaseCrawler

        success_response = _make_response(200, text="ok")
        call_count = 0

        async def mock_get_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("simulated failure")
            return success_response

        # Patch asyncio.sleep so tests don't actually wait
        with patch("asyncio.sleep", new=AsyncMock()):
            # We need to call the static method indirectly via a mock client
            # Patch httpx.AsyncClient.get to simulate failures then success
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.get.side_effect = [
                    httpx.ConnectError("fail 1"),
                    httpx.ConnectError("fail 2"),
                    success_response,
                ]
                resp = await BaseCrawler._get("https://example.com", retries=3)

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_raises_after_all_retries_exhausted(self):
        """_get should raise ConnectError after all retries fail."""
        from app.modules.crawler.base_crawler import BaseCrawler

        with patch("asyncio.sleep", new=AsyncMock()):
            with patch("httpx.AsyncClient") as mock_client_cls:
                mock_client = AsyncMock()
                mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
                mock_client.get.side_effect = httpx.ConnectError("always fails")

                with pytest.raises(httpx.ConnectError):
                    await BaseCrawler._get("https://example.com", retries=3)

    @pytest.mark.asyncio
    async def test_no_retry_on_4xx(self):
        """4xx responses are returned immediately without retry."""
        from app.modules.crawler.base_crawler import BaseCrawler

        not_found = _make_response(404)

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get.return_value = not_found

            resp = await BaseCrawler._get("https://example.com", retries=3)

        assert resp.status_code == 404
        # Should only be called once (no retry on 4xx)
        assert mock_client.get.call_count == 1


# ── BaseCrawler._already_processed ───────────────────────────────────────────


class TestAlreadyProcessed:
    """Test _already_processed with mocked DB session."""

    @pytest.mark.asyncio
    async def test_returns_true_when_hash_found(self):
        """Should return True if DB query returns True (hash exists)."""
        from app.modules.crawler.base_crawler import BaseCrawler

        # Mock the DB session so it returns True for the exists() scalar
        mock_result = MagicMock()
        mock_result.scalar.return_value = True

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_session_local = MagicMock(return_value=mock_session)

        with patch("app.db.base.AsyncSessionLocal", return_value=mock_session):
            # Instantiate a concrete subclass (BCRACrawler)
            from app.modules.crawler.bcra_crawler import BCRACrawler
            crawler = BCRACrawler()
            result = await crawler._already_processed("abc123")

        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_hash_not_found(self):
        """Should return False if DB query returns False."""
        from app.modules.crawler.bcra_crawler import BCRACrawler

        mock_result = MagicMock()
        mock_result.scalar.return_value = False

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.db.base.AsyncSessionLocal", return_value=mock_session):
            crawler = BCRACrawler()
            result = await crawler._already_processed("deadbeef")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_db_exception(self):
        """Should return False (not raise) on DB error."""
        from app.modules.crawler.bcra_crawler import BCRACrawler

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=Exception("DB down"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        with patch("app.db.base.AsyncSessionLocal", return_value=mock_session):
            crawler = BCRACrawler()
            result = await crawler._already_processed("badhash")

        assert result is False


# ── CrawlerResult dataclass ───────────────────────────────────────────────────


# ── BACEN crawler tests ───────────────────────────────────────────────────────


class TestBACENCrawler:
    """Test BACENCrawler — all external I/O mocked."""

    def _crawler(self):
        from app.modules.crawler.bacen_crawler import BACENCrawler
        return BACENCrawler()

    def test_bacen_fallback_entries(self):
        """Fallback returns exactly 5 entries, all with country BR."""
        from app.modules.crawler.bacen_crawler import BACENCrawler, BACEN_FALLBACK_URLS

        crawler = BACENCrawler()
        entries = crawler._fallback_entries()

        assert len(entries) == 5
        assert len(entries) == len(BACEN_FALLBACK_URLS)
        assert crawler.country == "BR"
        assert all("fallback" in e.title for e in entries)
        assert all(e.url.startswith("https://www.bcb.gov.br") for e in entries)

    def test_bacen_strategy1_pdf_links(self):
        """Strategy 1: anchors with .pdf hrefs are found."""
        html = """
        <html><body>
          <a href="/pre/normativos/circ/2023/03950.pdf">Circular 3950</a>
          <a href="/pre/normativos/circ/2023/03951.pdf">Circular 3951</a>
          <a href="/pre/normativos/circ/2023/03952.pdf">Circular 3952</a>
          <a href="/pre/normativos/circ/2023/03953.pdf">Circular 3953</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) >= 3
        urls = [e.url for e in entries]
        assert any("03950.pdf" in u for u in urls)
        assert any("03951.pdf" in u for u in urls)

    def test_bacen_strategy2_table_rows(self):
        """Strategy 2: table rows containing Circular keyword are parsed.

        The HTML uses non-PDF hrefs so strategy 1 doesn't fire; strategy 2
        must find the rows by Circular keyword and extract their links.
        """
        html = """
        <html><body><table>
          <tr>
            <td>Circular</td><td>3950</td>
            <td><a href="/normativos/circ/2023/view/3950">Ver</a></td>
          </tr>
          <tr>
            <td>Circular</td><td>3951</td>
            <td><a href="/normativos/circ/2023/view/3951">Ver</a></td>
          </tr>
          <tr>
            <td>Circular</td><td>3952</td>
            <td><a href="/normativos/circ/2023/view/3952">Ver</a></td>
          </tr>
        </table></body></html>
        """
        crawler = self._crawler()
        entries = crawler._strategy_table_rows(html)
        assert len(entries) >= 3
        urls = [e.url for e in entries]
        assert any("3950" in u for u in urls)
        assert any("3951" in u for u in urls)

    def test_bacen_strategy3_anchor_text(self):
        """Strategy 3: anchors whose text matches 'Circular 3950' pattern."""
        html = """
        <html><body>
          <a href="/page/3950">Circular 3950</a>
          <a href="/page/3951">Circular 3951</a>
          <a href="/page/3952">Circular 3952</a>
          <a href="/irrelevant">Página inicial</a>
        </body></html>
        """
        crawler = self._crawler()
        entries = crawler._parse_index_html(html)
        assert len(entries) >= 3
        titles = [e.title for e in entries]
        assert all(any("Circular" in t for t in titles) for _ in [1])
        assert not any("Página inicial" in t for t in titles)

    @pytest.mark.asyncio
    async def test_bacen_nonblocking_on_404(self):
        """Non-200 response returns fallback entries without raising."""
        from app.modules.crawler.bacen_crawler import BACEN_FALLBACK_URLS

        crawler = self._crawler()
        with patch.object(
            type(crawler), "_get",
            new=AsyncMock(return_value=_make_response(404)),
        ):
            entries = await crawler.fetch_index()

        assert len(entries) == len(BACEN_FALLBACK_URLS)
        assert all("fallback" in e.title for e in entries)

    def test_bacen_iso_date_extraction(self):
        """ISO yyyy-mm-dd date in text should be parsed into published_at."""
        from app.modules.crawler.bacen_crawler import BACENCrawler

        crawler = BACENCrawler()
        result = crawler._extract_date("Publicado em 2023-05-15 pelo BACEN")
        assert result is not None
        assert result.year == 2023
        assert result.month == 5
        assert result.day == 15


# ── CrawlerResult dataclass ───────────────────────────────────────────────────


class TestCrawlerResult:
    def test_to_dict_has_all_fields(self):
        from app.modules.crawler.base_crawler import CrawlerResult

        cr = CrawlerResult(
            regulator="BCRA",
            country="AR",
            crawled=3,
            skipped_duplicate=1,
            errors=0,
            documents=[{"title": "Test", "url": "https://x.com", "obligations_parsed": 2}],
            run_duration_seconds=12.5,
            timestamp="2025-01-15T00:00:00+00:00",
        )
        d = cr.to_dict()
        assert d["regulator"] == "BCRA"
        assert d["country"] == "AR"
        assert d["crawled"] == 3
        assert d["skipped_duplicate"] == 1
        assert d["errors"] == 0
        assert d["run_duration_seconds"] == 12.5
        assert isinstance(d["documents"], list)
        assert d["timestamp"] == "2025-01-15T00:00:00+00:00"
