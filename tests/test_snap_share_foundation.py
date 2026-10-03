import csv
import gzip
from datetime import datetime, timezone

import pytest

import imports.import_nflverse_snap_counts as snap_import
from imports.import_nflverse_snap_counts import build_pfr_to_gsis_crosswalk, build_snap_share_evidence
from services.snap_share_foundation import normalize_snap_counts_batch

NOW = "2026-09-17T12:00:00+00:00"
COLUMNS = ["season", "week", "player", "pfr_player_id", "position", "team", "opponent", "offense_snaps", "offense_pct", "defense_snaps", "defense_pct", "st_snaps", "st_pct"]


def snap_row(pfr_player_id, team, opponent, week=1, offense_snaps=55, offense_pct=1.0, player="Cole Strange", season=2026, position="WR", defense_snaps=0, defense_pct=0.0, st_snaps=0, st_pct=0.0):
    return {
        "season": season, "week": week, "player": player, "pfr_player_id": pfr_player_id, "position": position,
        "team": team, "opponent": opponent, "offense_snaps": offense_snaps, "offense_pct": offense_pct,
        "defense_snaps": defense_snaps, "defense_pct": defense_pct, "st_snaps": st_snaps, "st_pct": st_pct,
    }


def rows():
    return [
        snap_row("StraCo01", "LAC", "ARI", offense_pct=1.0),
        snap_row("AltxJo01", "LAC", "ARI", player="Joe Alt", offense_pct=0.08),
        snap_row("SlatRa00", "DEN", "KC", player="Rashawn Slater", offense_pct=0.0),
    ]


def batch(**overrides):
    kwargs = {"season": 2026, "source": "automated:nflverse", "retrieved_at": NOW, "checksum": "abc123", "source_recorded_at": NOW, "version": "snap_counts_2026"}
    kwargs.update(overrides)
    return normalize_snap_counts_batch(rows(), **kwargs)


# 1. official source metadata and attribution are preserved
def test_source_metadata_and_attribution_are_preserved():
    result = batch()
    assert result["provenance"]["source"] == "automated:nflverse"
    assert result["provenance"]["artifact_identifier"] == "snap_counts"
    assert result["provenance"]["checksum"] == "abc123"
    assert result["provenance"]["version"] == "snap_counts_2026"
    assert result["provenance"]["attribution"] == "NFLverse data, licensed under CC BY 4.0."
    assert result["decision_effect"] == "INFORMATIONAL_ONLY"


# 2. required source columns are validated
def test_missing_required_column_excludes_row_with_specific_blocker():
    incomplete = rows()
    del incomplete[0]["offense_pct"]
    result = normalize_snap_counts_batch(incomplete, season=2026, retrieved_at=NOW, checksum="abc123")
    assert result["reconciliation"]["missing_field_count"] == 1
    assert result["reconciliation"]["normalized_row_count"] == 2


# 3. actual offense_pct scale (0-1 ratio) is detected and normalized correctly
def test_offense_pct_ratio_scale_is_normalized_correctly():
    result = batch()
    by_pfr = {row["pfr_player_id"]: row for row in result["rows"]}
    assert by_pfr["StraCo01"]["snap_share"] == 1.0
    assert by_pfr["AltxJo01"]["snap_share"] == 0.08


# 4. verified zero remains distinct from unavailable
def test_verified_zero_snap_share_is_distinct_from_unavailable():
    result = batch()
    by_pfr = {row["pfr_player_id"]: row for row in result["rows"]}
    assert by_pfr["SlatRa00"]["snap_share"] == 0.0
    assert by_pfr["SlatRa00"]["snap_share"] is not None
    missing = normalize_snap_counts_batch([snap_row("Missing01", "KC", "DEN", offense_pct=None)], season=2026, retrieved_at=NOW, checksum="abc123")
    assert missing["rows"] == []
    assert missing["reconciliation"]["missing_field_count"] == 1


# 5. missing offense_pct remains unavailable (covered above) + malformed/out-of-range block
def test_malformed_or_out_of_range_values_block():
    malformed = normalize_snap_counts_batch([snap_row("Bad01", "KC", "DEN", offense_pct="not-a-number")], season=2026, retrieved_at=NOW, checksum="abc123")
    assert malformed["rows"][0]["snap_share"] is None
    assert "SNAP_SHARE_VALUE_MALFORMED" in malformed["rows"][0]["blockers"]

    out_of_range = normalize_snap_counts_batch([snap_row("Big01", "KC", "DEN", offense_pct=72.0)], season=2026, retrieved_at=NOW, checksum="abc123")
    assert out_of_range["rows"][0]["snap_share"] is None
    assert "SNAP_SHARE_SCALE_UNVERIFIED" in out_of_range["rows"][0]["blockers"]


# 7. exact PFR identity mapping resolves when uniquely supported
def test_exact_pfr_crosswalk_resolves_uniquely():
    result = batch(identity_crosswalk={"StraCo01": "local-player-42"})
    by_pfr = {row["pfr_player_id"]: row for row in result["rows"]}
    assert by_pfr["StraCo01"]["resolved_player_id"] == "local-player-42"
    assert by_pfr["StraCo01"]["gsis_id"] == "local-player-42"
    assert by_pfr["StraCo01"]["identity_resolution_state"] == "RESOLVED"
    assert by_pfr["StraCo01"]["identity_resolution_method"] == "repository_owned_pfr_crosswalk"
    assert "SNAP_SHARE_PLAYER_IDENTITY_UNAVAILABLE" not in by_pfr["StraCo01"]["blockers"]


# 8. unresolved PFR identity fails closed (default, no crosswalk supplied)
def test_unresolved_pfr_identity_fails_closed_by_default():
    result = batch()
    for row in result["rows"]:
        assert row["resolved_player_id"] is None
        assert row["gsis_id"] is None
        assert row["identity_resolution_state"] == "UNRESOLVED"
        assert "SNAP_SHARE_PLAYER_IDENTITY_UNAVAILABLE" in row["blockers"]
    assert result["reconciliation"]["unresolved_identity_count"] == 3
    assert result["reconciliation"]["resolved_row_count"] == 0


# 9. ambiguous PFR identity fails closed
def test_ambiguous_pfr_identity_fails_closed():
    result = batch(identity_crosswalk={"StraCo01": ["local-player-42", "local-player-99"]})
    row = next(r for r in result["rows"] if r["pfr_player_id"] == "StraCo01")
    assert row["resolved_player_id"] is None
    assert row["identity_resolution_state"] == "AMBIGUOUS"
    assert "SNAP_SHARE_PLAYER_IDENTITY_AMBIGUOUS" in row["blockers"]
    assert result["reconciliation"]["ambiguous_identity_count"] == 1


# contradictory: two distinct pfr_ids resolving to the same gsis_id must both block
def test_contradictory_gsis_id_collision_blocks_both_rows():
    result = batch(identity_crosswalk={"StraCo01": "shared-gsis", "AltxJo01": "shared-gsis", "SlatRa00": "local-player-7"})
    by_pfr = {row["pfr_player_id"]: row for row in result["rows"]}
    assert by_pfr["StraCo01"]["gsis_id"] is None
    assert by_pfr["AltxJo01"]["gsis_id"] is None
    assert by_pfr["StraCo01"]["identity_resolution_state"] == "CONTRADICTORY"
    assert "SNAP_SHARE_PLAYER_IDENTITY_CONTRADICTORY" in by_pfr["StraCo01"]["blockers"]
    assert by_pfr["SlatRa00"]["gsis_id"] == "local-player-7"
    assert result["reconciliation"]["contradictory_identity_count"] == 2


# 10. player names cannot independently authorize identity
def test_player_name_is_never_used_as_identity_authority():
    result = normalize_snap_counts_batch(
        [snap_row("StraCo01", "LAC", "ARI", player="Cole Strange")],
        season=2026, retrieved_at=NOW, checksum="abc123",
        identity_crosswalk={"Cole Strange": "local-player-42"},  # keyed by name, not pfr_player_id
    )
    assert result["rows"][0]["resolved_player_id"] is None
    assert "SNAP_SHARE_PLAYER_IDENTITY_UNAVAILABLE" in result["rows"][0]["blockers"]


# 11/12/13. missing season, week, and team fail closed with specific blockers
def test_missing_season_week_team_fail_closed_with_specific_blockers():
    missing_season = dict(snap_row("A01", "KC", "DEN")); missing_season["season"] = None
    missing_week = dict(snap_row("A01", "KC", "DEN")); missing_week["week"] = None
    missing_team = dict(snap_row("A01", "KC", "DEN")); missing_team["team"] = None

    for row, blocker in ((missing_season, "SNAP_SHARE_SEASON_UNAVAILABLE"), (missing_week, "SNAP_SHARE_WEEK_UNAVAILABLE"), (missing_team, "SNAP_SHARE_TEAM_IDENTITY_UNAVAILABLE")):
        result = normalize_snap_counts_batch([row], season=2026, retrieved_at=NOW, checksum="abc123")
        assert result["reconciliation"]["missing_field_count"] == 1
        assert result["reconciliation"]["normalized_row_count"] == 0


# 14. duplicate player-team-week blocks
def test_identical_duplicate_player_team_week_reconciles_safely():
    duplicated = rows() + [snap_row("StraCo01", "LAC", "ARI", offense_pct=1.0)]
    result = normalize_snap_counts_batch(duplicated, season=2026, retrieved_at=NOW, checksum="abc123")
    assert result["reconciliation"]["duplicate_count"] == 1
    assert "SNAP_SHARE_DUPLICATE_PLAYER_WEEK" not in result["blockers"]
    assert "StraCo01" in {row["pfr_player_id"] for row in result["rows"]}


# 15. contradictory player-team-week blocks
def test_contradictory_player_team_week_blocks():
    contradictory = rows() + [snap_row("StraCo01", "LAC", "ARI", offense_pct=0.5, offense_snaps=30)]
    result = normalize_snap_counts_batch(contradictory, season=2026, retrieved_at=NOW, checksum="abc123")
    assert result["reconciliation"]["contradictory_count"] == 2
    assert "SNAP_SHARE_CONTRADICTORY_PLAYER_WEEK" in result["blockers"]
    assert "StraCo01" not in {row["pfr_player_id"] for row in result["rows"]}


# 16. multi-team player-weeks are not silently collapsed
def test_multi_team_player_week_is_preserved_as_separate_rows():
    multi_team = [snap_row("Trad01", "KC", "DEN", week=5, offense_pct=0.6), snap_row("Trad01", "DEN", "KC", week=5, offense_pct=0.2)]
    result = normalize_snap_counts_batch(multi_team, season=2026, retrieved_at=NOW, checksum="abc123")
    teams = {row["team"] for row in result["rows"] if row["pfr_player_id"] == "Trad01"}
    assert teams == {"KC", "DEN"}
    assert result["reconciliation"]["normalized_row_count"] == 2
    assert result["reconciliation"]["duplicate_count"] == 0
    assert result["reconciliation"]["contradictory_count"] == 0


# 17. every input row is reconciled
def test_every_input_row_is_reconciled():
    mixed = rows() + [snap_row("Dup01", "KC", "DEN"), snap_row("Dup01", "KC", "DEN")]
    incomplete = dict(snap_row("Bad01", "KC", "DEN")); incomplete["team"] = None
    mixed.append(incomplete)
    result = normalize_snap_counts_batch(mixed, season=2026, retrieved_at=NOW, checksum="abc123")
    r = result["reconciliation"]
    assert r["normalized_row_count"] + r["excluded_row_count"] == r["input_row_count"]
    assert r["reconciled"] is True


# 18. missing retrieved_at fails closed
def test_missing_retrieved_at_fails_closed():
    result = batch(retrieved_at=None)
    assert "SNAP_SHARE_RETRIEVAL_TIME_UNAVAILABLE" in result["blockers"]
    assert result["authoritative"] is False


# 19. missing checksum fails closed
def test_missing_checksum_fails_closed():
    result = batch(checksum=None)
    assert "SNAP_SHARE_CHECKSUM_UNAVAILABLE" in result["blockers"]
    assert result["authoritative"] is False


# 20. the implementation-owned 24-hour freshness threshold is verified by default
def test_implementation_freshness_threshold_is_verified_by_default():
    result = batch(retrieved_at=datetime.now(timezone.utc).isoformat())
    assert "SNAP_SHARE_FRESHNESS_THRESHOLD_UNAVAILABLE" not in result["blockers"]
    assert result["provenance"]["freshness_threshold_id"] == "snap_share.evidence.v1"
    assert result["provenance"]["freshness_threshold_seconds"] == 86400
    assert result["freshness_state"] == "FRESH"
    assert result["authoritative"] is False
    assert all(not row["authoritative"] for row in result["rows"])


def test_approved_threshold_produces_fresh_aging_and_stale_states():
    now = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)
    fresh = batch(threshold_environment={"SNAP_SHARE_EVIDENCE_MAX_AGE_SECONDS": "100"}, now=now)
    aging = batch(threshold_environment={"SNAP_SHARE_EVIDENCE_MAX_AGE_SECONDS": "100"}, retrieved_at="2026-09-17T11:58:30+00:00", now=now)
    stale = batch(threshold_environment={"SNAP_SHARE_EVIDENCE_MAX_AGE_SECONDS": "100"}, retrieved_at="2026-09-17T11:57:30+00:00", now=now)
    assert fresh["freshness_state"] == "FRESH"
    assert aging["freshness_state"] == "AGING"
    assert stale["freshness_state"] == "STALE"
    assert "SNAP_SHARE_DATA_STALE" in stale["blockers"]


@pytest.mark.parametrize("value", ["not-a-number", "0", "-1"])
def test_malformed_or_non_positive_threshold_blocks(value):
    result = batch(threshold_environment={"SNAP_SHARE_EVIDENCE_MAX_AGE_SECONDS": value})
    assert result["freshness_state"] == "BLOCKED"
    assert any("SNAP_SHARE_FRESHNESS_THRESHOLD_BLOCKED" == blocker for blocker in result["blockers"])


# CSV source cannot claim automated authority
def test_non_automated_source_is_blocked():
    result = batch(source="fixture:manual.csv")
    assert "SNAP_SHARE_SOURCE_UNAVAILABLE" in result["blockers"]


# retrieval adapter reuses the existing generic loader against a real-shaped fixture (gzip + plain)
def test_retrieval_adapter_parses_real_shaped_fixture(tmp_path):
    path = tmp_path / "snap_counts_2026.csv"
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows())
    evidence = build_snap_share_evidence(path, season=2026, retrieved_at=NOW)
    assert evidence["provenance"]["source"] == f"fixture:{path.name}"
    assert evidence["provenance"]["checksum"]
    assert evidence["reconciliation"]["normalized_row_count"] == 3
    assert evidence["authoritative"] is False


def test_retrieval_adapter_handles_gzip_like_existing_convention(tmp_path):
    path = tmp_path / "snap_counts_2026.csv.gz"
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows())
    evidence = build_snap_share_evidence(path, season=2026, retrieved_at=NOW)
    assert evidence["reconciliation"]["normalized_row_count"] == 3


def test_retrieval_adapter_excludes_incomplete_later_weeks(tmp_path):
    path = tmp_path / "snap_counts_2026.csv"
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows([snap_row("Week01", "KC", "DEN", week=1), snap_row("Week04", "KC", "DEN", week=4)])

    evidence = build_snap_share_evidence(path, season=2026, retrieved_at=NOW, through_week=3)

    assert evidence["weeks"] == [1]
    assert evidence["provenance"]["selected_row_count"] == 1
    assert {int(row["week"]) for row in evidence["rows"]} == {1}


def test_retrieval_adapter_requires_actual_source_schema(tmp_path):
    path = tmp_path / "wrong_schema.csv"
    path.write_text("player,pfr_player_id\nExample,Player01\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SNAP_SHARE_SOURCE_SCHEMA_UNVERIFIED"):
        build_snap_share_evidence(path, season=2026, retrieved_at=NOW)


# crosswalk builder: deterministic (1 gsis_id), ambiguous (>1 gsis_id), and unresolved (no gsis_id) cases
def test_crosswalk_builder_classifies_deterministic_ambiguous_and_unresolved_pfr_ids(tmp_path):
    path = tmp_path / "players.csv"
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["pfr_id", "gsis_id"])
        writer.writeheader()
        writer.writerow({"pfr_id": "StraCo01", "gsis_id": "00-0012345"})
        writer.writerow({"pfr_id": "AmbigP01", "gsis_id": "00-0011111"})
        writer.writerow({"pfr_id": "AmbigP01", "gsis_id": "00-0022222"})
        writer.writerow({"pfr_id": "NoGsis01", "gsis_id": ""})
    crosswalk = build_pfr_to_gsis_crosswalk(path)
    assert crosswalk["StraCo01"] == {"00-0012345"}
    assert crosswalk["AmbigP01"] == {"00-0011111", "00-0022222"}
    assert crosswalk["NoGsis01"] == set()


def test_crosswalk_builder_requires_verified_columns(tmp_path):
    path = tmp_path / "players.csv"
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["pfr_id"])
        writer.writeheader()
        writer.writerow({"pfr_id": "StraCo01"})
    with pytest.raises(ValueError, match="NFLVERSE_PLAYERS_SCHEMA_UNVERIFIED"):
        build_pfr_to_gsis_crosswalk(path)


def test_remote_pfr_crosswalk_records_artifact_provenance(monkeypatch):
    monkeypatch.setattr(snap_import, "load_weekly_stats", lambda path: ([{"pfr_id": "StraCo01", "gsis_id": "00-0012345"}], "sha256:players"))
    monkeypatch.setattr(snap_import, "urlopen", lambda url, timeout: type("Response", (), {"read": lambda self: b"2026-09-17T10:00:00Z"})())

    crosswalk, lineage = snap_import.build_pfr_to_gsis_crosswalk(
        snap_import.NFLVERSE_PLAYERS_RELEASE_URL,
        include_lineage=True,
        retrieved_at=NOW,
    )

    assert crosswalk["StraCo01"] == {"00-0012345"}
    assert lineage["source_authority"] == "automated:nflverse"
    assert lineage["artifact_id"] == "nflverse.players.csv"
    assert lineage["source_recorded_at"] == "2026-09-17T10:00:00Z"
    assert lineage["retrieved_at"] == NOW
    assert lineage["checksum"] == "sha256:players"


def test_end_to_end_crosswalk_resolves_snap_share_batch(tmp_path):
    crosswalk_path = tmp_path / "players.csv"
    with open(crosswalk_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["pfr_id", "gsis_id"])
        writer.writeheader()
        writer.writerow({"pfr_id": "StraCo01", "gsis_id": "00-0012345"})
    crosswalk = build_pfr_to_gsis_crosswalk(crosswalk_path)

    snap_path = tmp_path / "snap_counts_2026.csv"
    with open(snap_path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows())

    evidence = build_snap_share_evidence(snap_path, season=2026, retrieved_at=NOW, identity_crosswalk=crosswalk)
    by_pfr = {row["pfr_player_id"]: row for row in evidence["rows"]}
    assert by_pfr["StraCo01"]["gsis_id"] == "00-0012345"
    assert by_pfr["AltxJo01"]["gsis_id"] is None  # not present in this small crosswalk fixture
    assert evidence["reconciliation"]["resolved_row_count"] == 1
    assert evidence["authoritative"] is False  # local fixture source cannot claim automated authority


@pytest.mark.parametrize(
    ("position", "count_field", "percentage_field", "domain"),
    [("WR", "offense_snaps", "offense_pct", "OFFENSE"), ("LB", "defense_snaps", "defense_pct", "DEFENSE"), ("K", "st_snaps", "st_pct", "SPECIAL_TEAMS")],
)
def test_snap_share_uses_documented_position_participation_domain(position, count_field, percentage_field, domain):
    row = snap_row("Domain01", "KC", "DEN", position=position, offense_pct=0.25, defense_pct=0.5, st_pct=0.75)
    result = normalize_snap_counts_batch([row], season=2026, retrieved_at=NOW, source_recorded_at=NOW, checksum="abc123", identity_crosswalk={"Domain01": "gsis-1"}, threshold_environment={"SNAP_SHARE_EVIDENCE_MAX_AGE_SECONDS": "86400"}, now=datetime.fromisoformat(NOW))
    normalized = result["rows"][0]
    assert normalized["participation_domain"] == domain
    assert normalized["source_percentage_field"] == percentage_field
    assert normalized["source_snap_count"] == row[count_field]
    assert normalized["snap_share"] == row[percentage_field]
    assert normalized["authoritative"] is True


def test_unsupported_participation_position_is_explicit_and_not_zero():
    result = normalize_snap_counts_batch(
        [snap_row("Unknown01", "KC", "DEN", position="UNKNOWN")],
        season=2026,
        retrieved_at=NOW,
        source_recorded_at=NOW,
        checksum="abc123",
        threshold_environment={"SNAP_SHARE_EVIDENCE_MAX_AGE_SECONDS": "86400"},
    )
    assert result["reconciliation"]["unsupported_position_count"] == 1
    assert result["reconciliation"]["normalized_row_count"] == 0
    assert result["provenance"]["completeness_state"] == "PARTIAL"


def test_missing_source_record_time_blocks_publication_authority():
    result = batch(source_recorded_at=None)
    assert "SNAP_SHARE_SOURCE_RECORD_TIME_UNAVAILABLE" in result["blockers"]
    assert result["authoritative"] is False
