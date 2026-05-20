"""
Crawler Scheduler — APScheduler AsyncIOScheduler integrated with FastAPI lifespan.

Schedule:
  BCRA  — every 6 hours
  UIF   — every 12 hours
  BACEN — every 8 hours
  CMF   — every 12 hours
  SFC   — every 12 hours
  CNBV  — every 12 hours
"""

from __future__ import annotations

import logging
from typing import Any

from app.modules.crawler.base_crawler import CrawlerResult

logger = logging.getLogger(__name__)


async def run_bcra(tenant_id: str = "polkorp") -> dict[str, Any]:
    from app.modules.crawler.bcra_crawler import BCRACrawler
    from app.services.event_bus import publish
    crawler = BCRACrawler()
    result: CrawlerResult = await crawler.run(tenant_id=tenant_id)
    logger.info("BCRA crawl complete: %s", result)
    d = result.to_dict()
    await publish(f"crawler:{tenant_id}", {"regulator": "BCRA", **d})
    return d


async def run_uif(tenant_id: str = "polkorp") -> dict[str, Any]:
    from app.modules.crawler.uif_crawler import UIFCrawler
    from app.services.event_bus import publish
    crawler = UIFCrawler()
    result: CrawlerResult = await crawler.run(tenant_id=tenant_id)
    logger.info("UIF crawl complete: %s", result)
    d = result.to_dict()
    await publish(f"crawler:{tenant_id}", {"regulator": "UIF", **d})
    return d


async def run_bacen(tenant_id: str = "polkorp") -> dict[str, Any]:
    from app.modules.crawler.bacen_crawler import BACENCrawler
    from app.services.event_bus import publish
    crawler = BACENCrawler()
    result: CrawlerResult = await crawler.run(tenant_id=tenant_id)
    logger.info("BACEN crawl complete: %s", result)
    d = result.to_dict()
    await publish(f"crawler:{tenant_id}", {"regulator": "BACEN", **d})
    return d


async def run_cmf(tenant_id: str = "polkorp") -> dict[str, Any]:
    from app.modules.crawler.cmf_crawler import CMFCrawler
    from app.services.event_bus import publish
    crawler = CMFCrawler()
    result: CrawlerResult = await crawler.run(tenant_id=tenant_id)
    logger.info("CMF crawl complete: %s", result)
    d = result.to_dict()
    await publish(f"crawler:{tenant_id}", {"regulator": "CMF", **d})
    return d


async def run_sfc(tenant_id: str = "polkorp") -> dict[str, Any]:
    from app.modules.crawler.sfc_crawler import SFCCrawler
    from app.services.event_bus import publish
    crawler = SFCCrawler()
    result: CrawlerResult = await crawler.run(tenant_id=tenant_id)
    logger.info("SFC crawl complete: %s", result)
    d = result.to_dict()
    await publish(f"crawler:{tenant_id}", {"regulator": "SFC", **d})
    return d


async def run_cnbv(tenant_id: str = "polkorp") -> dict[str, Any]:
    from app.modules.crawler.cnbv_crawler import CNBVCrawler
    from app.services.event_bus import publish
    crawler = CNBVCrawler()
    result: CrawlerResult = await crawler.run(tenant_id=tenant_id)
    logger.info("CNBV crawl complete: %s", result)
    d = result.to_dict()
    await publish(f"crawler:{tenant_id}", {"regulator": "CNBV", **d})
    return d


async def run_deadline_check(tenant_id: str = "polkorp") -> dict:
    from app.modules.monitoring.deadline_checker import check_deadlines
    result = await check_deadlines(tenant_id=tenant_id)
    logger.info("Deadline check complete: %s", result)
    return result


async def run_all(tenant_id: str = "polkorp") -> list[dict[str, Any]]:
    """Run all crawlers sequentially (respects NVIDIA 40 RPM limit)."""
    from app.services.event_bus import publish
    results = []
    for run_fn in [run_bcra, run_uif, run_bacen, run_cmf, run_sfc, run_cnbv]:
        try:
            results.append(await run_fn(tenant_id=tenant_id))
        except Exception as e:
            logger.error("Crawler failed: %s", e)
            results.append({"error": str(e)})

    # Publish a summary event for run_all
    total_crawled = sum(r.get("crawled", 0) for r in results if isinstance(r, dict) and "crawled" in r)
    total_skipped = sum(r.get("skipped_duplicate", 0) for r in results if isinstance(r, dict))
    total_errors = sum(r.get("errors", 0) for r in results if isinstance(r, dict))
    await publish(f"crawler:{tenant_id}", {
        "regulator": "ALL",
        "crawled": total_crawled,
        "skipped_duplicate": total_skipped,
        "errors": total_errors,
        "results": results,
    })
    return results


def start_scheduler(app=None):
    """Start APScheduler. Call from FastAPI lifespan."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = AsyncIOScheduler()
        scheduler.add_job(run_bcra,           IntervalTrigger(hours=6),  id="bcra_crawl",     replace_existing=True)
        scheduler.add_job(run_uif,            IntervalTrigger(hours=12), id="uif_crawl",      replace_existing=True)
        scheduler.add_job(run_bacen,          IntervalTrigger(hours=8),  id="bacen_crawl",    replace_existing=True)
        scheduler.add_job(run_cmf,            IntervalTrigger(hours=12), id="cmf_crawl",      replace_existing=True)
        scheduler.add_job(run_sfc,            IntervalTrigger(hours=12), id="sfc_crawl",      replace_existing=True)
        scheduler.add_job(run_cnbv,           IntervalTrigger(hours=12), id="cnbv_crawl",     replace_existing=True)
        scheduler.add_job(run_deadline_check, IntervalTrigger(hours=24), id="deadline_check", replace_existing=True)
        scheduler.start()
        logger.info(
            "Crawler scheduler started "
            "(BCRA: 6h, UIF: 12h, BACEN: 8h, CMF: 12h, SFC: 12h, CNBV: 12h, deadline: 24h)"
        )
        return scheduler
    except ImportError:
        logger.warning("apscheduler not installed — crawler scheduling disabled")
        return None
    except Exception as e:
        logger.warning("Crawler scheduler failed to start: %s", e)
        return None
