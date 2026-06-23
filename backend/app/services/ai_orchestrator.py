"""
ComplianceOS — AI Orchestration Layer (v0.2 — calibrated on real benchmark data)
================================================================================

Single entry point for all AI inference across modules M1-M6.

Responsibilities:
  - Route requests to the right model based on task type
  - Manage fallback chains
  - Enforce rate limits (NVIDIA free tier: 40 RPM)
  - Track cost and latency per inference
  - Log every call to immutable audit trail
  - Detect and block prompt injection attempts (M5)

ROUTING CALIBRATED FROM REAL BENCHMARK (results.csv, 2026-05-11):
  ✓ kimi-k2: Q=100 in M2 Copilot + M5 Governance. Fastest tier-1 (15.8s).
  ✓ nemotron-super-49b: Q=100 in M1+M3+M5. Most thorough (757 tokens avg). Slow (33s).
  ✓ llama-3.3-70b: Q=91.3. Best speed/quality balance (21s avg).
  ✗ deepseek-v3.1: EOL 2026-04-15 → replaced by deepseek-v3.1-terminus
  ✗ mistral-large-2: 404 Not Found → replaced by mistral-large-3-675b
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from app.core.config import get_settings


# ═══════════════════════════════════════════════════════════════════
# TASK TYPES — drives model selection
# ═══════════════════════════════════════════════════════════════════

class TaskType(str, Enum):
    # M1 — Regulatory Intelligence
    REGULATORY_PARSING = "regulatory_parsing"
    REGULATORY_MAPPING = "regulatory_mapping"

    # M2 — Copilot
    COPILOT_QA = "copilot_qa"
    COPILOT_DEEP = "copilot_deep"

    # M3 — AML/KYC
    KYC_SCREENING = "kyc_screening"
    SANCTIONS_SCREENING = "sanctions_screening"

    # M4 — Monitoring
    ANOMALY_DETECTION = "anomaly_detection"
    POLICY_DRIFT = "policy_drift"

    # M5 — AI Governance
    SELF_AUDIT = "self_audit"
    INJECTION_DETECT = "injection_detect"
    CONTENT_SAFETY = "content_safety"

    # M6 — Evidence
    OCR_EXTRACTION = "ocr_extraction"
    RAG_RERANK = "rag_rerank"

    # M8 — Predictive Risk
    JURISDICTION_RISK = "jurisdiction_risk"
    MARKET_ENTRY_SIM = "market_entry_sim"

    # Embeddings (separate API call, not chat completions)
    EMBEDDING = "embedding"

    # Multilingual specialization
    MULTILINGUAL_ZH = "multilingual_zh"


# ═══════════════════════════════════════════════════════════════════
# MODEL REGISTRY — only VALIDATED models
# ═══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class ModelSpec:
    id: str
    provider: str = "nvidia"
    context_window: int = 128_000
    free_endpoint: bool = True
    supports_streaming: bool = True
    ref_cost_per_1m_in: float = 0.0
    ref_cost_per_1m_out: float = 0.0
    strengths: tuple[str, ...] = ()
    benchmark_quality: float = 0.0
    notes: str = ""


EMBED_MODEL = "nvidia/nv-embed-v2"
EMBED_DIMS = 1024


MODELS: dict[str, ModelSpec] = {
    # ── TIER 1: BENCHMARK-VALIDATED (real Q scores) ──────────────
    "nemotron-super-49b": ModelSpec(
        id="nvidia/llama-3.3-nemotron-super-49b-v1",
        ref_cost_per_1m_in=0.40, ref_cost_per_1m_out=0.40,
        strengths=("reasoning", "agentic", "kyc", "evidence_rich"),
        benchmark_quality=93.6,
        notes="WINNER overall. Q=100 in M1+M3+M5. Slow (33s avg) but thorough (757 tokens avg).",
    ),
    "llama-3.3-70b": ModelSpec(
        id="meta/llama-3.3-70b-instruct",
        ref_cost_per_1m_in=0.20, ref_cost_per_1m_out=0.60,
        strengths=("balanced", "fast", "regulatory_parsing"),
        benchmark_quality=91.3,
        notes="Best speed/quality balance. Q=100 in M1. Avg 21s.",
    ),
    "kimi-k2": ModelSpec(
        id="moonshotai/kimi-k2-instruct",
        ref_cost_per_1m_in=0.60, ref_cost_per_1m_out=2.50,
        strengths=("copilot", "governance", "multilingual", "fastest"),
        benchmark_quality=91.2,
        notes="FASTEST tier-1 (15.8s). Q=100 in M2+M5. Multilingual ES/EN/ZH native.",
    ),

    # ── TIER 2: catalog-verified, replacements for deprecated models ──
    "minimax-m2": ModelSpec(
        id="minimaxai/minimax-m2",
        context_window=200_000,
        ref_cost_per_1m_in=0.50, ref_cost_per_1m_out=2.00,
        strengths=("reasoning", "function_calling", "long_context"),
        notes="230B MoE, 10B active. Reasoning + tool-use.",
    ),
    "deepseek-v3.1-terminus": ModelSpec(
        id="deepseek-ai/deepseek-v3.1-terminus",
        ref_cost_per_1m_in=0.27, ref_cost_per_1m_out=1.10,
        strengths=("reasoning", "multilingual", "chinese"),
        notes="Replacement for deprecated deepseek-v3.1. Sparse attention.",
    ),
    "nemotron-nano-30b": ModelSpec(
        id="nvidia/nemotron-3-nano-30b-a3b",
        ref_cost_per_1m_in=0.10, ref_cost_per_1m_out=0.20,
        strengths=("fast", "instruction_following", "cost_efficient"),
        notes="Fast nano variant for high-volume low-criticality routes.",
    ),
    "mistral-large-3": ModelSpec(
        id="mistralai/mistral-large-3-675b-instruct-2512",
        ref_cost_per_1m_in=2.00, ref_cost_per_1m_out=6.00,
        strengths=("balanced", "multimodal", "agentic"),
        notes="Replacement for 404'd mistral-large-2. MoE VLM.",
    ),

    # ── TIER 3: cross-provider fallback (premortem F1/T1.1) ──────
    # Only reached when every NVIDIA model in the chain has already failed.
    "claude-sonnet-4-6": ModelSpec(
        id="claude-sonnet-4-6",
        provider="anthropic",
        context_window=1_000_000,
        ref_cost_per_1m_in=3.00, ref_cost_per_1m_out=15.00,
        strengths=("reasoning", "fallback"),
        notes="Anthropic fallback tier 2 — covers a total NVIDIA NIM outage.",
    ),
    "openrouter-llama-3.3-70b": ModelSpec(
        id="meta-llama/llama-3.3-70b-instruct",
        provider="openrouter",
        ref_cost_per_1m_in=0.12, ref_cost_per_1m_out=0.30,
        strengths=("fallback",),
        notes="OpenRouter fallback tier 3 — catch-all if NVIDIA and Anthropic are both down.",
    ),
}

# Appended to every routing chain below so an NVIDIA-wide outage degrades to
# Anthropic, then OpenRouter, instead of a total inference failure (F1).
CROSS_PROVIDER_FALLBACK_TAIL = ["claude-sonnet-4-6", "openrouter-llama-3.3-70b"]


# ═══════════════════════════════════════════════════════════════════
# DATA RESIDENCY (T1.3) — which providers a tenant's data may leave to
# ═══════════════════════════════════════════════════════════════════
#
# Tenant.data_residency_policy (global | latam | ar | br) gates which
# ModelSpec.provider values are eligible for that tenant. NVIDIA NIM is
# the baseline provider for every policy; the Anthropic/OpenRouter
# cross-provider fallback tier (a different vendor/jurisdiction) is only
# eligible for tenants on the unrestricted "global" policy. Unknown
# policy strings fall back to the most restrictive set (NVIDIA-only).
RESIDENCY_ALLOWED_PROVIDERS: dict[str, frozenset[str]] = {
    "global": frozenset({"nvidia", "anthropic", "openrouter"}),
    "latam": frozenset({"nvidia"}),
    "ar": frozenset({"nvidia"}),
    "br": frozenset({"nvidia"}),
}
DEFAULT_RESIDENCY_PROVIDERS = RESIDENCY_ALLOWED_PROVIDERS["latam"]  # most restrictive


# ═══════════════════════════════════════════════════════════════════
# CIRCUIT BREAKER (T1.6) — stop hammering a provider that's down
# ═══════════════════════════════════════════════════════════════════

class CircuitBreaker:
    """Per-provider consecutive-failure counter. Opens after `threshold`
    consecutive failures and skips that provider's models for `cooldown_s`
    seconds, so a dead provider doesn't add latency to every request in
    the chain — callers fall straight through to the next tier."""

    def __init__(self, threshold: int = 5, cooldown_s: float = 60.0):
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self._fail_counts: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}

    def is_open(self, provider: str) -> bool:
        opened_at = self._opened_at.get(provider)
        if opened_at is None:
            return False
        if time.time() - opened_at >= self.cooldown_s:
            # Cooldown elapsed — half-open: allow one probe through.
            del self._opened_at[provider]
            self._fail_counts[provider] = 0
            return False
        return True

    def record_success(self, provider: str) -> None:
        self._fail_counts[provider] = 0
        self._opened_at.pop(provider, None)

    def record_failure(self, provider: str) -> None:
        count = self._fail_counts.get(provider, 0) + 1
        self._fail_counts[provider] = count
        if count >= self.threshold:
            self._opened_at[provider] = time.time()


# ═══════════════════════════════════════════════════════════════════
# ROUTING TABLE — calibrated on benchmark results
# ═══════════════════════════════════════════════════════════════════

ROUTING: dict[TaskType, list[str]] = {
    # M1 — Regulatory: llama-3.3-70b & nemotron tied at Q=100
    TaskType.REGULATORY_PARSING:   ["llama-3.3-70b", "nemotron-super-49b", "kimi-k2"],
    TaskType.REGULATORY_MAPPING:   ["nemotron-super-49b", "llama-3.3-70b", "minimax-m2"],

    # M2 — Copilot: kimi won Q=100, llama-70b second
    TaskType.COPILOT_QA:           ["kimi-k2", "llama-3.3-70b", "nemotron-super-49b"],
    TaskType.COPILOT_DEEP:         ["nemotron-super-49b", "kimi-k2", "minimax-m2"],

    # M3 — KYC/AML: nemotron Q=100, llama-70b Q=92
    TaskType.KYC_SCREENING:        ["nemotron-super-49b", "llama-3.3-70b", "kimi-k2"],
    TaskType.SANCTIONS_SCREENING:  ["nemotron-super-49b", "llama-3.3-70b", "deepseek-v3.1-terminus"],

    # M4 — Monitoring: nemotron Q=92 best
    TaskType.ANOMALY_DETECTION:    ["nemotron-super-49b", "llama-3.3-70b", "minimax-m2"],
    TaskType.POLICY_DRIFT:         ["nemotron-super-49b", "minimax-m2", "llama-3.3-70b"],

    # M5 — Governance: kimi 2x faster than nemotron at same Q=100
    TaskType.SELF_AUDIT:           ["kimi-k2", "nemotron-super-49b", "minimax-m2"],
    TaskType.INJECTION_DETECT:     ["kimi-k2", "llama-3.3-70b"],
    TaskType.CONTENT_SAFETY:       ["kimi-k2", "nemotron-super-49b"],

    # M6 — Evidence
    TaskType.OCR_EXTRACTION:       ["nemotron-super-49b", "kimi-k2"],
    TaskType.RAG_RERANK:           ["nemotron-nano-30b", "llama-3.3-70b"],

    # M8 — Predictive Risk: reasoning-heavy, grounded with real regulation/obligation counts
    TaskType.JURISDICTION_RISK:    ["nemotron-super-49b", "llama-3.3-70b", "minimax-m2"],
    TaskType.MARKET_ENTRY_SIM:     ["nemotron-super-49b", "llama-3.3-70b", "minimax-m2"],

    # Multilingual ZH
    TaskType.MULTILINGUAL_ZH:      ["kimi-k2", "deepseek-v3.1-terminus", "minimax-m2"],
}

for _chain in ROUTING.values():
    _chain.extend(CROSS_PROVIDER_FALLBACK_TAIL)


# ═══════════════════════════════════════════════════════════════════
# INFERENCE REQUEST / RESULT
# ═══════════════════════════════════════════════════════════════════

@dataclass
class InferenceRequest:
    task: TaskType
    system: str
    user_prompt: str
    tenant_id: str
    user_id: str | None = None
    temperature: float = 0.2
    max_tokens: int = 1024
    json_mode: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InferenceResult:
    success: bool
    response_text: str
    parsed_json: dict | None
    model_used: str
    fallback_chain_used: list[str]
    latency_ttft_ms: float
    latency_total_ms: float
    tokens_in: int
    tokens_out: int
    estimated_cost_usd: float
    audit_id: str
    timestamp: str
    error: str | None = None


# ═══════════════════════════════════════════════════════════════════
# RATE LIMITER
# ═══════════════════════════════════════════════════════════════════

class RateLimiter:
    def __init__(self, rpm: int):
        self.rpm = rpm
        self.min_delay = 60.0 / rpm
        self._last_call: float = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            elapsed = time.time() - self._last_call
            if elapsed < self.min_delay:
                await asyncio.sleep(self.min_delay - elapsed)
            self._last_call = time.time()


# ═══════════════════════════════════════════════════════════════════
# PROMPT INJECTION DETECTOR
# ═══════════════════════════════════════════════════════════════════

INJECTION_PATTERNS = [
    "ignore previous instructions", "ignore all previous", "disregard your training",
    "you are now", "<system>", "</system>", "bypass aml", "approve all",
    "override:", "new instructions:", "act as if",
    "olvida las instrucciones", "ignora las instrucciones",
]


def detect_injection(text: str) -> tuple[bool, list[str]]:
    """Fast rule-based injection detection."""
    lower = text.lower()
    matches = [p for p in INJECTION_PATTERNS if p in lower]
    return len(matches) > 0, matches


# ═══════════════════════════════════════════════════════════════════
# THE ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════

class AIOrchestrator:
    """Single point of contact between modules and AI providers."""

    def __init__(self):
        s = get_settings()
        self.settings = s
        self.client = AsyncOpenAI(
            base_url=s.nvidia_base_url,
            api_key=s.nvidia_api_key or "missing-key",
            timeout=180.0,  # nemotron can take 70s+
        )
        self.rate_limiter = RateLimiter(rpm=s.nvidia_rate_limit_rpm)

        # Fallback tiers (premortem F1/T1.1) — only constructed when configured.
        self.anthropic_client = (
            AsyncAnthropic(api_key=s.anthropic_api_key, timeout=180.0)
            if s.has_anthropic else None
        )
        self.openrouter_client = (
            AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=s.openrouter_api_key,
                timeout=180.0,
            )
            if s.has_openrouter else None
        )

        self._audit_callback = None
        self._residency_cache: dict[str, str] = {}
        self.circuit_breaker = CircuitBreaker()

    def set_audit_callback(self, callback):
        """Inject the audit logger from outside (avoids circular imports)."""
        self._audit_callback = callback

    async def _get_residency_policy(self, tenant_id: str) -> str:
        """Look up Tenant.data_residency_policy, cached per-process. On any
        lookup failure (tenant missing, DB unreachable) fall back to "global"
        — the same default the column itself has for an unspecified tenant —
        rather than letting a transient DB error take down all inference."""
        cached = self._residency_cache.get(tenant_id)
        if cached is not None:
            return cached
        try:
            from sqlalchemy import select
            from app.db.base import AsyncSessionLocal
            from app.db.models import Tenant

            async with AsyncSessionLocal() as session:
                stmt = select(Tenant.data_residency_policy).where(Tenant.slug == tenant_id)
                policy = (await session.execute(stmt)).scalar_one_or_none()
        except Exception:
            policy = None

        policy = policy or "global"
        self._residency_cache[tenant_id] = policy
        return policy

    async def infer(self, req: InferenceRequest) -> InferenceResult:
        """Main entry. Try primary model, fall back if it fails."""
        if not (self.settings.has_nvidia or self.settings.has_anthropic or self.settings.has_openrouter):
            return self._fail(req, "No AI provider configured (NVIDIA/Anthropic/OpenRouter all missing)")

        # M5 — block prompt injection at the gateway
        injected, patterns = detect_injection(req.user_prompt)
        if injected:
            return self._fail(
                req,
                f"Prompt injection detected: {patterns}",
                audit_tag="INJECTION_BLOCKED",
            )

        # T1.3 — data residency: which providers may even be considered for this tenant
        residency_policy = await self._get_residency_policy(req.tenant_id)
        allowed_providers = RESIDENCY_ALLOWED_PROVIDERS.get(residency_policy, DEFAULT_RESIDENCY_PROVIDERS)

        chain = ROUTING.get(req.task, ["kimi-k2"])
        chain_used = []
        last_error = None

        for model_key in chain:
            spec = MODELS.get(model_key)
            if not spec:
                continue
            if spec.provider not in allowed_providers:
                continue
            if spec.provider == "nvidia" and not self.settings.has_nvidia:
                continue
            if spec.provider == "anthropic" and not self.settings.has_anthropic:
                continue
            if spec.provider == "openrouter" and not self.settings.has_openrouter:
                continue
            # T1.6 — circuit breaker: skip a provider that's been failing rather
            # than eating its timeout again on every single request.
            if self.circuit_breaker.is_open(spec.provider):
                continue
            chain_used.append(model_key)

            try:
                result = await self._call_model(spec, req, chain_used)
                self.circuit_breaker.record_success(spec.provider)
                await self._audit(req, result, status="OK")
                return result
            except Exception as e:
                self.circuit_breaker.record_failure(spec.provider)
                last_error = f"{type(e).__name__}: {str(e)[:200]}"
                continue

        if not chain_used:
            return self._fail(
                req,
                f"No eligible provider for residency policy '{residency_policy}' "
                f"(allowed: {sorted(allowed_providers)}) or all circuits open",
            )
        return self._fail(req, f"All fallbacks failed. Last: {last_error}",
                          chain_used=chain_used)

    async def _call_model(
        self,
        spec: ModelSpec,
        req: InferenceRequest,
        chain_used: list[str],
    ) -> InferenceResult:
        """Dispatch to the right provider SDK based on spec.provider."""
        if spec.provider == "anthropic":
            return await self._call_anthropic(spec, req, chain_used)
        if spec.provider == "openrouter":
            return await self._call_openai_compatible(
                self.openrouter_client, spec, req, chain_used, rate_limiter=None,
            )
        return await self._call_openai_compatible(
            self.client, spec, req, chain_used, rate_limiter=self.rate_limiter,
        )

    async def _call_openai_compatible(
        self,
        client: AsyncOpenAI,
        spec: ModelSpec,
        req: InferenceRequest,
        chain_used: list[str],
        rate_limiter: RateLimiter | None,
    ) -> InferenceResult:
        """Shared streaming call path for any OpenAI-compatible provider (NVIDIA, OpenRouter)."""
        if rate_limiter:
            await rate_limiter.acquire()

        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": req.system},
            {"role": "user", "content": req.user_prompt},
        ]

        t_start = time.time()
        ttft = 0.0
        chunks: list[str] = []

        stream = await client.chat.completions.create(
            model=spec.id,
            messages=messages,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if ttft == 0.0:
                ttft = (time.time() - t_start) * 1000
            if chunk.choices and chunk.choices[0].delta.content:
                chunks.append(chunk.choices[0].delta.content)

        total_ms = (time.time() - t_start) * 1000
        response_text = "".join(chunks)

        tokens_in = len(req.system + req.user_prompt) // 4
        tokens_out = len(response_text) // 4
        cost = (
            (tokens_in / 1_000_000) * spec.ref_cost_per_1m_in +
            (tokens_out / 1_000_000) * spec.ref_cost_per_1m_out
        )

        parsed = self._try_parse_json(response_text) if req.json_mode else None

        return InferenceResult(
            success=True,
            response_text=response_text,
            parsed_json=parsed,
            model_used=spec.id,
            fallback_chain_used=chain_used,
            latency_ttft_ms=round(ttft, 1),
            latency_total_ms=round(total_ms, 1),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated_cost_usd=round(cost, 6),
            audit_id=self._audit_id(req),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    async def _call_anthropic(
        self,
        spec: ModelSpec,
        req: InferenceRequest,
        chain_used: list[str],
    ) -> InferenceResult:
        """Fallback call path via the Anthropic Messages API (non-streaming)."""
        t_start = time.time()

        response = await self.anthropic_client.messages.create(
            model=spec.id,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            system=req.system,
            messages=[{"role": "user", "content": req.user_prompt}],
        )

        total_ms = (time.time() - t_start) * 1000
        response_text = "".join(
            block.text for block in response.content if block.type == "text"
        )

        tokens_in = response.usage.input_tokens
        tokens_out = response.usage.output_tokens
        cost = (
            (tokens_in / 1_000_000) * spec.ref_cost_per_1m_in +
            (tokens_out / 1_000_000) * spec.ref_cost_per_1m_out
        )

        parsed = self._try_parse_json(response_text) if req.json_mode else None

        return InferenceResult(
            success=True,
            response_text=response_text,
            parsed_json=parsed,
            model_used=spec.id,
            fallback_chain_used=chain_used,
            latency_ttft_ms=round(total_ms, 1),  # non-streaming — no separate TTFT
            latency_total_ms=round(total_ms, 1),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated_cost_usd=round(cost, 6),
            audit_id=self._audit_id(req),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _strip_js_comments(text: str) -> str:
        """Remove JS-style // line comments that some models inject into JSON.
        Negative lookbehind on `:` and `/` keeps https:// URLs intact."""
        import re
        return re.sub(r"(?<![:/])\s*//[^\n]*", "", text)

    @staticmethod
    def _try_parse_json(text: str) -> dict | None:
        """Robust JSON parsing — handles ```json wrapping and // comments from nemotron."""
        t = text.strip()
        if "```json" in t:
            t = t.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in t:
            parts = t.split("```")
            if len(parts) >= 3:
                t = parts[1]
        start, end = t.find("{"), t.rfind("}")
        if start == -1 or end == -1:
            return None
        candidate = t[start:end + 1]
        # First attempt: parse as-is
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
        # Second attempt: strip JS-style // comments then retry
        try:
            return json.loads(AIOrchestrator._strip_js_comments(candidate))
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _audit_id(req: InferenceRequest) -> str:
        payload = f"{req.tenant_id}:{req.task}:{datetime.now(timezone.utc).isoformat()}:{req.user_prompt[:80]}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    async def embed(self, texts: list[str], tenant_id: str = "system") -> list[list[float]] | None:
        """Generate embeddings via NVIDIA NIM nv-embed-v2. Returns list of vectors or None on failure."""
        if not self.settings.has_nvidia:
            return None
        try:
            await self.rate_limiter.acquire()
            response = await self.client.embeddings.create(
                model=EMBED_MODEL,
                input=[t[:8000] for t in texts],
                encoding_format="float",
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            return None

    def _fail(self, req, error_msg: str, chain_used=None, audit_tag: str = "ERROR") -> InferenceResult:
        return InferenceResult(
            success=False,
            response_text="",
            parsed_json=None,
            model_used="",
            fallback_chain_used=chain_used or [],
            latency_ttft_ms=0,
            latency_total_ms=0,
            tokens_in=0,
            tokens_out=0,
            estimated_cost_usd=0,
            audit_id=self._audit_id(req),
            timestamp=datetime.now(timezone.utc).isoformat(),
            error=error_msg,
        )

    async def _audit(self, req: InferenceRequest, result: InferenceResult, status: str):
        if self._audit_callback:
            try:
                await self._audit_callback({
                    "audit_id": result.audit_id,
                    "tenant_id": req.tenant_id,
                    "user_id": req.user_id,
                    "task": req.task.value,
                    "model_used": result.model_used,
                    "fallback_chain": result.fallback_chain_used,
                    "status": status,
                    "latency_ms": result.latency_total_ms,
                    "tokens_in": result.tokens_in,
                    "tokens_out": result.tokens_out,
                    "cost_usd": result.estimated_cost_usd,
                    "timestamp": result.timestamp,
                    "prompt_hash": hashlib.sha256(req.user_prompt.encode()).hexdigest(),
                })
            except Exception:
                pass  # never let audit failure block inference


# ═══════════════════════════════════════════════════════════════════
# Singleton accessor
# ═══════════════════════════════════════════════════════════════════

_orchestrator: AIOrchestrator | None = None


def get_orchestrator() -> AIOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AIOrchestrator()
    return _orchestrator
