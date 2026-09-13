from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_projection_importer_uses_normalized_source_team_for_identity_match():
    text = (ROOT / "imports/import_draft_intelligence.py").read_text(encoding="utf-8")
    assert 'team = normalize_team(row.get("Team"))' in text
    assert 'TEAM_ALIASES = {"JAC": "JAX", "JAX": "JAX"}' in text


def test_trade_route_preserves_missing_local_players_as_unavailable():
    text = (ROOT / "owner_operations.py").read_text(encoding="utf-8")
    assert '"projection":None' in text
    assert '"projection_retrieved_at":None' in text


def test_trade_route_uses_suffix_aware_unique_normalized_join():
    text = (ROOT / "owner_operations.py").read_text(encoding="utf-8")
    assert "REGEXP_REPLACE(REGEXP_REPLACE(LOWER(player_name)" in text
    assert "'(jr|sr|ii|iii|iv|il|ill)$'" in text


def test_trade_route_propagates_stable_and_local_identity_lineage():
    text = (ROOT / "owner_operations.py").read_text(encoding="utf-8")
    for marker in ('"source_player_id"', '"local_player_id"', '"normalized_name"', '"identity_match_method"', '"identity_state"'):
        assert marker in text