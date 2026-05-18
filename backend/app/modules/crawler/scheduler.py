"""
Crawler Scheduler — APScheduler AsyncIOScheduler integrated with FastAPI lifespan.

Schedule:
  BCRA  — every 6 hours
  UIF   — every 12 hours
  BACEN — every 8 hours
"""

from __future__ import annotations

import logging
from typing import Any

from app.modules.crawler.base_crawler import CrawlerResult

logger = logging.getLogger(__name__)


async def run_bcra(tenant_id: str = "polkorp") -> dict[str, Any]:
    from app.modules.crawler.bcra_crawler import BCRACrawler
    crawler = BCRACrawler()
    result: CrawlerResult = await crawler.run(tenant_id=tenant_id)
    logger.info("BCRA crawl complete: %s", result)
    return result.to_dict()


async def run_uif(tenant_id: str = "polkorp") -> dict[str, Any]:
    from app.modules.crawler.uif_crawler import UIFCrawler
    crawler = UIFCrawler()
    result: CrawlerResult = await crawler.run(tenant_id=tenant_id)
    logger.info("UIF crawl complete: %s", result)
    return result.to_dict()


async def run_bacen(tenant_id: str = "polkorp") -> dict[str, Any]:
    from app.modules.crawler.bacen_crawler import BACENCrawler
    crawler = BACENCrawler()
    result: CrawlerResult = await crawler.run(tenant_id=tenant_id)
    logger.info("BACEN crawl complete: %s", result)
    return result.to_dict()


async def run_all(tenant_id: str = "polkorp") -> list[dict[str, Any]]:
    """Run all crawlers sequentially (respects NVIDIA 40 RPM limit)."""
    results = []
    for run_fn in [run_bcra, run_uif, run_bacen]:
        try:
            results.append(await run_fn(tenant_id=tenant_id))
        except Exception as e:
            logger.error("Crawler failed: %s", e)
            results.append({"error": str(e)})
    return results


def start_scheduler(app=None):
    """Start APScheduler. Call from FastAPI lifespan."""
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger

        scheduler = AsyncIOScheduler()
        scheduler.add_job(run_bcra,  IntervalTrigger(hours=6),  id="bcra_crawl",  replace_existing=True)
        scheduler.add_job(run_uif,   IntervalTrigger(hours=12), id="uif_crawl",   replace_existing=True)
        scheduler.add_job(run_bacen, IntervalTrigger(hours=8),  id="bacen_crawl", replace_existing=True)
        scheduler.start()
        logger.info("Crawler scheduler started (BCRA: 6h, UIF: 12h, BACEN: 8h)")
        return scheduler
    except ImportError:
        logger.warning("apscheduler not installed — crawler scheduling disabled")
        return None
    except Exception as e:
        logger.warning("Crawler scheduler failed to start: %s", e)
        return None
