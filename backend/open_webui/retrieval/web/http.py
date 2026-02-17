import logging
from typing import Any, Optional

import requests

from open_webui.config import RAG_WEB_SEARCH_REQUEST_TIMEOUT
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


def get_json_with_timeout(
    url: str,
    *,
    provider_name: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    timeout_seconds: Optional[int] = None,
) -> dict[str, Any]:
    """Perform a provider API GET call with shared timeout/error handling and return parsed JSON."""
    timeout = timeout_seconds or RAG_WEB_SEARCH_REQUEST_TIMEOUT.value
    try:
        response = requests.get(url, headers=headers, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        log.error("%s timeout after %ss", provider_name, timeout)
        raise
    except requests.exceptions.RequestException as e:
        log.error("%s request failed: %s", provider_name, e)
        try:
            if e.response is not None:
                log.error("%s error details: %s", provider_name, e.response.json())
        except Exception:
            pass
        raise
    except ValueError as e:
        status_code = response.status_code if "response" in locals() else "unknown"
        log.error(
            "%s returned invalid JSON (status=%s): %s",
            provider_name,
            status_code,
            e,
        )
        raise requests.exceptions.RequestException(
            f"{provider_name} returned invalid JSON"
        ) from e
