"""Comprehensive read-only Sleeper API client with retry and JSON caching hooks."""
from __future__ import annotations
import json, os, time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = os.getenv("SLEEPER_API_BASE", "https://api.sleeper.app/v1").rstrip("/")
TIMEOUT = int(os.getenv("SLEEPER_API_TIMEOUT", "15"))
USER_AGENT = os.getenv("SLEEPER_USER_AGENT", "fantasy-intelligence/1.0")

class SleeperAPIError(RuntimeError): pass

def _get(path, params=None, retries=2):
    url=f"{BASE_URL}/{path.lstrip('/')}"
    if params:
        url += "?" + urlencode({k:v for k,v in params.items() if v is not None})
    request=Request(url,headers={"Accept":"application/json","User-Agent":USER_AGENT})
    last=None
    for attempt in range(retries+1):
        try:
            with urlopen(request,timeout=TIMEOUT) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            body=exc.read().decode("utf-8",errors="replace")
            if exc.code not in (429,500,502,503,504) or attempt==retries:
                raise SleeperAPIError(f"Sleeper HTTP {exc.code} for {url}: {body[:300]}") from exc
            last=exc
        except (URLError,TimeoutError) as exc:
            last=exc
            if attempt==retries: break
        time.sleep(0.5*(2**attempt))
    raise SleeperAPIError(f"Sleeper request failed for {url}: {last}")

# User and league APIs
def get_user(user): return _get(f"user/{user}")
def get_user_leagues(user_id, season, sport="nfl"): return _get(f"user/{user_id}/leagues/{sport}/{season}")
def get_league(league_id): return _get(f"league/{league_id}")
def get_league_users(league_id): return _get(f"league/{league_id}/users")
def get_league_rosters(league_id): return _get(f"league/{league_id}/rosters")
def get_matchups(league_id, week): return _get(f"league/{league_id}/matchups/{week}")
def get_transactions(league_id, week): return _get(f"league/{league_id}/transactions/{week}")
def get_traded_picks(league_id): return _get(f"league/{league_id}/traded_picks")
def get_winners_bracket(league_id): return _get(f"league/{league_id}/winners_bracket")
def get_losers_bracket(league_id): return _get(f"league/{league_id}/losers_bracket")

# Draft APIs
def get_league_drafts(league_id): return _get(f"league/{league_id}/drafts")
def get_draft(draft_id): return _get(f"draft/{draft_id}")
def get_draft_picks(draft_id): return _get(f"draft/{draft_id}/picks")
def get_draft_traded_picks(draft_id): return _get(f"draft/{draft_id}/traded_picks")

# Sport/player APIs
def get_sport_state(sport="nfl"): return _get(f"state/{sport}")
def get_players(sport="nfl"): return _get(f"players/{sport}")
def get_trending_players(action="add", sport="nfl", lookback_hours=24, limit=50):
    if action not in {"add","drop"}: raise ValueError("action must be add or drop")
    return _get(f"players/{sport}/trending/{action}",{"lookback_hours":lookback_hours,"limit":limit})
