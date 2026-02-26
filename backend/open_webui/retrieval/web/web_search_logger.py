"""
Web Search Audit Logger

Structured audit logging for every web search query dispatched to upstream providers.
Designed for:
  - Data leakage analysis (what queries are leaving the system)
  - Performance monitoring (latency, result counts)
  - Security auditing (who searched what, when)

Each log record is emitted as a single JSON payload in the application logger,
so it is captured by the container runtime (stdout/stderr) without external
file writes.
"""

import hashlib
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from open_webui.env import SRC_LOG_LEVELS

# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_query(query: str) -> str:
    """SHA-256 hash of the normalised query for correlation without storing PII at INFO level."""
    normalised = query.lower().strip()
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:16]


def _safe_user_attrs(user) -> dict:
    """Extract safe, non-secret user attributes for audit logging."""
    if not user:
        return {
            "user_id": None,
            "user_role": None,
            "user_email": None,
            "user_name": None,
        }
    return {
        "user_id": (
            str(getattr(user, "id", None))
            if getattr(user, "id", None) is not None
            else None
        ),
        "user_role": getattr(user, "role", None),
        "user_email": getattr(user, "email", None),
        "user_name": getattr(user, "name", None),
    }


def _emit_audit_record(record: dict) -> None:
    """Emit a structured audit record into container logs without raising."""
    try:
        payload = json.dumps(
            record, default=str, ensure_ascii=False, separators=(",", ":")
        )
        log.info("[web_search_audit] %s", payload)
    except Exception:
        log.exception("[web_search_audit] failed to serialize audit record")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def log_web_search_dispatch(
    *,
    engine: str,
    query: str,
    result_count_requested: int,
    domain_filter_list: Optional[list] = None,
    user=None,
    event_id: Optional[str] = None,
) -> dict:
    """
    Log a web search dispatch event BEFORE calling the upstream provider.

    Returns a context dict to be passed to ``log_web_search_result()`` later.
    """
    event_id = event_id or f"wsd_{uuid.uuid4().hex[:12]}"
    ts = datetime.now(timezone.utc).isoformat()

    try:
        record = {
            "event_id": event_id,
            "event_type": "web_search_dispatch",
            "timestamp": ts,
            "engine": engine,
            "query": query,
            "query_hash": _hash_query(query),
            "query_length": len(query),
            "result_count_requested": result_count_requested,
            "domain_filter_active": bool(domain_filter_list),
            "domain_filter_count": len(domain_filter_list) if domain_filter_list else 0,
            **_safe_user_attrs(user),
        }
        _emit_audit_record(record)
    except Exception:
        log.exception("[web_search_dispatch] audit logging failure")

    return {
        "event_id": event_id,
        "start_time": time.monotonic(),
        "engine": engine,
    }


def log_web_search_result(
    *,
    dispatch_ctx: dict,
    results: list,
    error: Optional[Exception] = None,
) -> None:
    """
    Log the outcome of a web search call AFTER the upstream provider returns.

    Args:
        dispatch_ctx: The dict returned by ``log_web_search_dispatch()``.
        results: The list of SearchResult objects returned (empty on failure).
        error: The exception if the call failed, else None.
    """
    elapsed_ms = round((time.monotonic() - dispatch_ctx["start_time"]) * 1000)
    event_id = dispatch_ctx["event_id"]
    engine = dispatch_ctx["engine"]

    try:
        result_urls = []
        result_domains: list[str] = []
        _seen_domains: set[str] = set()
        for result in results or []:
            link = getattr(result, "link", None)
            if link:
                result_urls.append(link)
                try:
                    domain = urlparse(link).netloc
                    if domain and domain not in _seen_domains:
                        result_domains.append(domain)
                        _seen_domains.add(domain)
                except Exception:
                    continue

        record = {
            "event_id": event_id,
            "event_type": "web_search_result",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "engine": engine,
            "latency_ms": elapsed_ms,
            "result_count": len(results) if results else 0,
            "result_urls": result_urls,
            "result_domains": result_domains,
            "result_domain_count": len(result_domains),
            "has_snippets": sum(
                1 for result in (results or []) if getattr(result, "snippet", None)
            ),
            "success": error is None,
            "error_type": type(error).__name__ if error else None,
            "error_message": str(error)[:500] if error else None,
        }
        _emit_audit_record(record)
    except Exception:
        log.exception("[web_search_result] audit logging failure")


def log_web_search_content_load(
    *,
    event_id: str,
    urls: list,
    docs_loaded: int,
    latency_ms: int,
    bypass_embedding: bool = False,
    collection_name: Optional[str] = None,
    error: Optional[Exception] = None,
) -> None:
    """
    Log the URL content-loading phase that follows search result retrieval.

    This captures what external URLs are actually being fetched/scraped,
    which is critical for data-leakage analysis.
    """
    try:
        record = {
            "event_id": event_id,
            "event_type": "web_search_content_load",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "urls_requested": urls,
            "urls_requested_count": len(urls) if urls else 0,
            "docs_loaded": docs_loaded,
            "latency_ms": latency_ms,
            "bypass_embedding": bypass_embedding,
            "collection_name": collection_name,
            "success": error is None,
            "error_type": type(error).__name__ if error else None,
            "error_message": str(error)[:500] if error else None,
        }
        _emit_audit_record(record)
    except Exception:
        log.exception("[web_search_content_load] audit logging failure")
