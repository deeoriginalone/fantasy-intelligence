"""Read-only, low-frequency reader for ESPN's public NFL news JSON feed."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from time import monotonic
from typing import Any, Callable

import requests

NEWS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/news"
REQUEST_TIMEOUT_SECONDS = 4
CACHE_TTL_SECONDS = 300
_CACHE: dict[str, Any] = {"expires_at": 0.0, "result": None}
_CACHE_LOCK = Lock()


def read_espn_nfl_news(*, fetch_json: Callable[[], Any] | None = None, force_refresh: bool = False) -> dict[str, Any]:
    """Fetch one public feed snapshot per five minutes; do not scrape article HTML."""
    now_monotonic = monotonic()
    with _CACHE_LOCK:
        if not force_refresh and _CACHE["result"] is not None and now_monotonic < _CACHE["expires_at"]:
            return deepcopy(_CACHE["result"])

    retrieved_at = datetime.now(timezone.utc).isoformat()
    try:
        if fetch_json:
            payload = fetch_json()
        else:
            response = requests.get(NEWS_URL, params={"limit": 50}, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
        source_articles = payload.get("articles") if isinstance(payload, dict) else None
        if not isinstance(source_articles, list):
            result = {"state": "BLOCKED", "source": "ESPN public NFL news JSON", "retrieved_at": retrieved_at, "articles": [], "blockers": ["ESPN_NEWS_FEED_SCHEMA_UNAVAILABLE"]}
        else:
            articles = []
            for article in source_articles:
                if not isinstance(article, dict):
                    continue
                athlete_ids = sorted({
                    str(category.get("athleteId"))
                    for category in article.get("categories") or []
                    if isinstance(category, dict) and category.get("type") == "athlete" and category.get("athleteId") is not None
                })
                if not athlete_ids:
                    continue
                web_link = ((article.get("links") or {}).get("web") or {}).get("href")
                articles.append({
                    "article_id": str(article.get("id") or "") or None,
                    "headline": article.get("headline"),
                    "description": article.get("description"),
                    "published_at": article.get("published"),
                    "last_modified_at": article.get("lastModified"),
                    "url": web_link,
                    "espn_athlete_ids": athlete_ids,
                    "source": "ESPN",
                    "freshness_state": "UNVERIFIED",
                    "decision_effect": "INFORMATIONAL_ONLY",
                })
            result = {
                "state": "AVAILABLE",
                "source": "ESPN public NFL news JSON",
                "source_url": NEWS_URL,
                "retrieved_at": retrieved_at,
                "freshness_state": "UNVERIFIED",
                "decision_effect": "INFORMATIONAL_ONLY",
                "articles": articles,
                "blockers": [],
            }
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        result = {"state": "UNAVAILABLE", "source": "ESPN public NFL news JSON", "retrieved_at": retrieved_at, "freshness_state": "UNAVAILABLE", "decision_effect": "INFORMATIONAL_ONLY", "articles": [], "blockers": ["ESPN_NEWS_FEED_REQUEST_FAILED"]}

    with _CACHE_LOCK:
        _CACHE["result"] = deepcopy(result)
        _CACHE["expires_at"] = monotonic() + CACHE_TTL_SECONDS
    return result


def news_for_espn_player(feed: dict[str, Any] | None, espn_id: Any, *, limit: int = 3) -> dict[str, Any]:
    """Return only exact ESPN athlete-ID matches; never resolve news by name."""
    if not espn_id:
        return {"state": "UNAVAILABLE", "source": "ESPN", "articles": [], "freshness_state": "UNAVAILABLE", "decision_effect": "INFORMATIONAL_ONLY", "blockers": ["ESPN_PLAYER_ID_UNAVAILABLE"]}
    feed = dict(feed or {})
    if feed.get("state") != "AVAILABLE":
        return {"state": feed.get("state") or "UNAVAILABLE", "source": feed.get("source") or "ESPN", "articles": [], "freshness_state": feed.get("freshness_state") or "UNAVAILABLE", "decision_effect": "INFORMATIONAL_ONLY", "blockers": list(feed.get("blockers") or ["ESPN_NEWS_FEED_UNAVAILABLE"])}
    matches = [article for article in feed.get("articles") or [] if str(espn_id) in (article.get("espn_athlete_ids") or [])]
    matches.sort(key=lambda article: str(article.get("published_at") or ""), reverse=True)
    return {
        "state": "AVAILABLE" if matches else "UNAVAILABLE",
        "source": "ESPN public NFL news JSON",
        "espn_id": str(espn_id),
        "feed_retrieved_at": feed.get("retrieved_at"),
        "freshness_state": "UNVERIFIED" if matches else "UNAVAILABLE",
        "decision_effect": "INFORMATIONAL_ONLY",
        "articles": matches[:limit],
        "blockers": [] if matches else ["ESPN_PLAYER_NEWS_NOT_IN_FEED"],
    }


def reset_espn_news_cache() -> None:
    """Clear the process-local cache for deterministic tests."""
    with _CACHE_LOCK:
        _CACHE["result"] = None
        _CACHE["expires_at"] = 0.0