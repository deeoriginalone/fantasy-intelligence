import requests

BASE_URL = "https://api.sleeper.app/v1"
DEFAULT_TIMEOUT = 20


def _get_json(path):
    response = requests.get(
        f"{BASE_URL}{path}",
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def get_league(league_id):
    return _get_json(f"/league/{league_id}")


def get_users(league_id):
    return _get_json(f"/league/{league_id}/users")


def get_rosters(league_id):
    return _get_json(f"/league/{league_id}/rosters")


def get_drafts(league_id):
    return _get_json(f"/league/{league_id}/drafts")


def get_draft(draft_id):
    return _get_json(f"/draft/{draft_id}")


def get_draft_picks(draft_id):
    return _get_json(f"/draft/{draft_id}/picks")


def get_all_players():
    """Return Sleeper's NFL player dictionary keyed by Sleeper player ID."""
    return _get_json("/players/nfl")

# === Sleeper Full Integration (managed block) ===
def get_user(user): return _get_json(f"/user/{user}")
def get_user_leagues(user_id, season, sport="nfl"): return _get_json(f"/user/{user_id}/leagues/{sport}/{season}")
def get_matchups(league_id, week): return _get_json(f"/league/{league_id}/matchups/{week}")
def get_transactions(league_id, week): return _get_json(f"/league/{league_id}/transactions/{week}")
def get_traded_picks(league_id): return _get_json(f"/league/{league_id}/traded_picks")
def get_winners_bracket(league_id): return _get_json(f"/league/{league_id}/winners_bracket")
def get_losers_bracket(league_id): return _get_json(f"/league/{league_id}/losers_bracket")
def get_draft_traded_picks(draft_id): return _get_json(f"/draft/{draft_id}/traded_picks")
def get_nfl_state(): return _get_json("/state/nfl")
def get_trending_players(action="add", lookback_hours=24, limit=50):
    if action not in {"add", "drop"}: raise ValueError("action must be add or drop")
    return _get_json(f"/players/nfl/trending/{action}?lookback_hours={int(lookback_hours)}&limit={int(limit)}")
def get_trending_adds(lookback_hours=24, limit=50): return get_trending_players("add",lookback_hours,limit)
def get_trending_drops(lookback_hours=24, limit=50): return get_trending_players("drop",lookback_hours,limit)
# === End Sleeper Full Integration ===
