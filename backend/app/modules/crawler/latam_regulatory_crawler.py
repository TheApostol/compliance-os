"""
LATAM Regulatory Crawler - Unified Module for ComplianceOS

Purpose:
Fetch public and credentialed LATAM regulator data, route it through M1
(Regulatory Intelligence), persist tenant-scoped Regulation records, and
optionally trigger downstream Evidence, Graph and Qdrant RAG indexing.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel, Field

from app.db.base import AsyncSessionLocal
from app.db.models import Regulation
from app.services.ai_orchestrator import ai_orchestrator


class CrawlResult(BaseModel):
    source: str
    country: str
    regulator: str
    code: str
    title: str
    raw_data: Dict[str, Any] | List[Any]
    extracted_obligations: List[Dict[str, Any]] = Field(default_factory=list)
    evidence_hash: str
    tenant_id: str
    source_url: Optional[str] = None


class LatamRegulatoryCrawler:
    """Unified async crawler for LATAM regulators."""

    def __init__(self, timeout_seconds: float = 30.0):
        self.client = httpx.AsyncClient(
            timeout=timeout_seconds,
            limits=httpx.Limits(max_connections=20),
            follow_redirects=True,
        )

    async def close(self) -> None:
        await self.client.aclose()

    async def __aenter__(self) -> "LatamRegulatoryCrawler":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    def _get_credential(self, key: str, tenant_id: str | None = None) -> str:
        return os.getenv(key, "")

    async def _get_json(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        retries: int = 2,
    ) -> Any:
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                resp = await self.client.get(url, headers=headers, params=params)
                resp.raise_for_status()
                return resp.json()
            except Exception as exc:
                last_error = exc
                if attempt < retries:
                    await asyncio.sleep(0.75 * (attempt + 1))
        raise RuntimeError(f"GET JSON failed for {url}: {last_error}")

    def _hash_payload(self, payload: Any) -> str:
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def _extract_obligations(self, ai_result: Any) -> List[Dict[str, Any]]:
        if ai_result is None:
            return []
        if isinstance(ai_result, dict):
            if isinstance(ai_result.get("obligations"), list):
                return ai_result["obligations"]
            parsed = ai_result.get("parsed_json")
            if isinstance(parsed, dict) and isinstance(parsed.get("obligations"), list):
                return parsed["obligations"]
            answer = ai_result.get("response_text") or ai_result.get("answer")
            if isinstance(answer, str):
                return self._extract_obligations_from_text(answer)
        parsed_json = getattr(ai_result, "parsed_json", None)
        if isinstance(parsed_json, dict) and isinstance(parsed_json.get("obligations"), list):
            return parsed_json["obligations"]
        response_text = getattr(ai_result, "response_text", None)
        if isinstance(response_text, str):
            return self._extract_obligations_from_text(response_text)
        return []

    def _extract_obligations_from_text(self, text: str) -> List[Dict[str, Any]]:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and isinstance(parsed.get("obligations"), list):
                return parsed["obligations"]
        except Exception:
            return []
        return []

    async def _parse_with_ai(
        self,
        *,
        regulator: str,
        title: str,
        data: Any,
        model_preference: str = "meta/llama-3.3-70b-instruct",
    ) -> List[Dict[str, Any]]:
        prompt = (
            f"Extract structured regulatory obligations, risks, deadlines, metrics, "
            f"entities, and compliance implications from this {regulator} {title} data. "
            f"Return strict JSON with an 'obligations' list.\n\n"
            f"{json.dumps(data, ensure_ascii=False, default=str)[:14000]}"
        )
        result = await ai_orchestrator.infer(
            task_type="regulatory_parsing",
            prompt=prompt,
            model_preference=model_preference,
        )
        return self._extract_obligations(result)

    async def crawl_regulator(self, regulator: str, tenant_id: str, *, store: bool = True, **kwargs) -> List[CrawlResult]:
        adapters = {
            "BCRA": self._crawl_bcra,
            "BACEN": self._crawl_bacen,
            "BCCh": self._crawl_bcch,
            "BCRP": self._crawl_bcrp,
            "Banxico": self._crawl_banxico,
            "SFC": self._crawl_sfc,
        }
        if regulator not in adapters:
            raise ValueError(f"Unsupported regulator: {regulator}. Supported: {', '.join(adapters.keys())}")
        results = await adapters[regulator](tenant_id, **kwargs)
        if store and results:
            await self.store_results(results)
        return results

    async def _crawl_bcra(self, tenant_id: str, **kwargs) -> List[CrawlResult]:
        base = "https://api.bcra.gob.ar"
        endpoints = [
            ("/principalesvariables/v1", "Principales Variables", "BCRA_PRINCIPALES_VARIABLES"),
            ("/estadisticasmonetarias/v4", "Monetary Statistics v4", "BCRA_ESTADISTICAS_MONETARIAS_V4"),
        ]
        results: List[CrawlResult] = []
        for path, title, code in endpoints:
            url = f"{base}{path}"
            try:
                data = await self._get_json(url)
                obligations = await self._parse_with_ai(regulator="BCRA", title=title, data=data)
                results.append(CrawlResult(source=f"BCRA - {title}", country="AR", regulator="BCRA", code=code, title=title, raw_data=data, extracted_obligations=obligations, evidence_hash=self._hash_payload(data), tenant_id=tenant_id, source_url=url))
            except Exception as exc:
                print(f"[BCRA {title}] Error: {exc}")
        return results

    async def _crawl_bacen(self, tenant_id: str, series_codes: Optional[List[str]] = None, **kwargs) -> List[CrawlResult]:
        base = "https://api.bcb.gov.br/dados/serie/bcdata.sgs"
        series_codes = series_codes or ["1", "433", "4390"]
        results: List[CrawlResult] = []
        for code in series_codes:
            url = f"{base}/{code}/dados?formato=json"
            try:
                data = await self._get_json(url)
                sample = data[:100] if isinstance(data, list) else data
                obligations = await self._parse_with_ai(regulator="BACEN", title=f"Series {code}", data=sample)
                results.append(CrawlResult(source=f"BACEN Series {code}", country="BR", regulator="BACEN", code=f"BACEN_SGS_{code}", title=f"BACEN SGS Series {code}", raw_data=data, extracted_obligations=obligations, evidence_hash=self._hash_payload(data), tenant_id=tenant_id, source_url=url))
            except Exception as exc:
                print(f"[BACEN {code}] Error: {exc}")
        return results

    async def _crawl_bcch(self, tenant_id: str, timeseries: Optional[List[str]] = None, **kwargs) -> List[CrawlResult]:
        base = "https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx"
        user = self._get_credential("BCCH_USER", tenant_id)
        password = self._get_credential("BCCH_PASS", tenant_id)
        if not user or not password:
            print("[BCCh] Credentials missing. Set BCCH_USER and BCCH_PASS.")
            return []
        timeseries = timeseries or ["F022.TPM.TIN.D001.NO.Z.D"]
        results: List[CrawlResult] = []
        for ts in timeseries:
            params = {"user": user, "pass": password, "function": "GetSeries", "timeseries": ts, "firstdate": (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d"), "lastdate": datetime.now().strftime("%Y-%m-%d")}
            try:
                data = await self._get_json(base, params=params)
                obligations = await self._parse_with_ai(regulator="BCCh", title=f"Series {ts}", data=data)
                results.append(CrawlResult(source=f"BCCh Series {ts}", country="CL", regulator="BCCh", code=f"BCCH_{ts}", title=f"BCCh Series {ts}", raw_data=data, extracted_obligations=obligations, evidence_hash=self._hash_payload(data), tenant_id=tenant_id, source_url=base))
            except Exception as exc:
                print(f"[BCCh {ts}] Error: {exc}")
        return results

    async def _crawl_bcrp(self, tenant_id: str, series_codes: Optional[List[str]] = None, **kwargs) -> List[CrawlResult]:
        base = "https://estadisticas.bcrp.gob.pe/estadisticas/series/api"
        series_codes = series_codes or ["PN01288PM"]
        results: List[CrawlResult] = []
        for code in series_codes:
            url = f"{base}/{code}/json"
            try:
                data = await self._get_json(url)
                obligations = await self._parse_with_ai(regulator="BCRP", title=f"Series {code}", data=data)
                results.append(CrawlResult(source=f"BCRP Series {code}", country="PE", regulator="BCRP", code=f"BCRP_{code}", title=f"BCRP Series {code}", raw_data=data, extracted_obligations=obligations, evidence_hash=self._hash_payload(data), tenant_id=tenant_id, source_url=url))
            except Exception as exc:
                print(f"[BCRP {code}] Error: {exc}")
        return results

    async def _crawl_banxico(self, tenant_id: str, series: Optional[List[str]] = None, **kwargs) -> List[CrawlResult]:
        token = self._get_credential("BANXICO_TOKEN", tenant_id)
        if not token:
            print("[Banxico] Token missing. Set BANXICO_TOKEN.")
            return []
        base = "https://www.banxico.org.mx/SieAPIRest/service/v1/series"
        series = series or ["SF43783"]
        results: List[CrawlResult] = []
        for s in series:
            url = f"{base}/{s}/datos"
            try:
                data = await self._get_json(url, headers={"Bmx-Token": token})
                obligations = await self._parse_with_ai(regulator="Banxico", title=f"Series {s}", data=data)
                results.append(CrawlResult(source=f"Banxico Series {s}", country="MX", regulator="Banxico", code=f"BANXICO_{s}", title=f"Banxico Series {s}", raw_data=data, extracted_obligations=obligations, evidence_hash=self._hash_payload(data), tenant_id=tenant_id, source_url=url))
            except Exception as exc:
                print(f"[Banxico {s}] Error: {exc}")
        return results

    async def _crawl_sfc(self, tenant_id: str, **kwargs) -> List[CrawlResult]:
        url = kwargs.get("url", "https://www.datos.gov.co/resource/x7wx-67fu.json")
        try:
            data = await self._get_json(url, params={"$limit": 100})
            sample = data[:50] if isinstance(data, list) else data
            obligations = await self._parse_with_ai(regulator="SFC", title="Open Data", data=sample)
            return [CrawlResult(source="SFC Open Data", country="CO", regulator="SFC", code="SFC_OPEN_DATA", title="SFC Open Data", raw_data=data, extracted_obligations=obligations, evidence_hash=self._hash_payload(data), tenant_id=tenant_id, source_url=url)]
        except Exception as exc:
            print(f"[SFC] Error: {exc}")
            return []

    async def store_results(self, results: List[CrawlResult]) -> None:
        async with AsyncSessionLocal() as session:
            for res in results:
                regulation = Regulation(
                    tenant_id=res.tenant_id,
                    country=res.country,
                    regulator=res.regulator,
                    code=res.code,
                    title=f"Auto-crawled {res.source} - {datetime.now(timezone.utc).date()}",
                    source_url=res.source_url,
                    source_hash=res.evidence_hash,
                    full_text=json.dumps(res.raw_data, ensure_ascii=False, default=str),
                    metadata_json={"source": res.source, "raw_data": res.raw_data, "extracted_obligations": res.extracted_obligations, "crawler": "LatamRegulatoryCrawler"},
                )
                session.add(regulation)
                await session.commit()
                await session.refresh(regulation)
                await self._safe_downstream_hooks(regulation, res)

    async def _safe_downstream_hooks(self, regulation: Regulation, result: CrawlResult) -> None:
        try:
            from app.services.rag import get_rag
            rag = get_rag()
            await rag.index_regulation(regulation_id=str(regulation.id), country=result.country, regulator=result.regulator, code=result.code, title=regulation.title, text=regulation.full_text or "", tenant_id=result.tenant_id)
        except Exception as exc:
            print(f"[RAG hook] Failed for {result.source}: {exc}")
        try:
            from app.services.graph_service import get_graph
            graph = get_graph()
            await graph.add_regulation(regulation_id=str(regulation.id), country=result.country, regulator=result.regulator, code=result.code, title=regulation.title, obligations=result.extracted_obligations)
        except Exception as exc:
            print(f"[Graph hook] Failed for {result.source}: {exc}")


async def crawl_latam_regulator(regulator: str, tenant_id: str, *, store: bool = True, **kwargs) -> List[CrawlResult]:
    async with LatamRegulatoryCrawler() as crawler:
        return await crawler.crawl_regulator(regulator=regulator, tenant_id=tenant_id, store=store, **kwargs)


if __name__ == "__main__":
    async def main():
        results = await crawl_latam_regulator("BCRA", "tenant_default", store=False)
        print(f"Crawled {len(results)} results")
    asyncio.run(main())
