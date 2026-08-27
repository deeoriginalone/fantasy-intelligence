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
