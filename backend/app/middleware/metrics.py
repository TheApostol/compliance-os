from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator

# ── Crawler metrics (used by M4 deadline checker + LATAM crawler) ──────────────
CRAWL_ATTEMPTS = Counter(
    "complianceos_crawl_attempts_total",
    "Total crawler attempts",
    ["regulator"],
)
CRAWL_SUCCESS = Counter(
    "complianceos_crawl_success_total",
    "Successful crawler runs",
    ["regulator"],
)

_instrumentator: Instrumentator | None = None


def setup_metrics(app) -> None:
    global _instrumentator
    _instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/docs", "/redoc", "/openapi.json"],
        inprogress_labels=True,
    ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
