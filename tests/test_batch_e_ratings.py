from datetime import datetime, timedelta, timezone

import pytest

from batch_e_ratings import (
    INITIAL_RATING,
    MODEL_NAME,
    MODEL_VERSION,
    REPLAY_CLASSIFICATIONS,
    _source_timestamp,
    build_evidence_batch,
    reconstruct_ratings,
)
from batch_e_common import canonical_schedule_games
from imports.import_weekly_intelligence import abbr
from services.model_only_future_probability import build_model_only_future_probability

NOW = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
BASE = {
    "season": 2026,
    "week": 3,
    "scheduled_games": [
        {"game_id": "2026-w3-sf-mia", "home_team": "MIA", "away_team": "SF", "scheduled_at": NOW + timedelta(days=3)},
        {"game_id": "2026-w3-dal-phi", "home_team": "PHI", "away_team": "DAL", "scheduled_at": NOW + timedelta(days=3)},
    ],
    "historical_rows": [
        {"season": 2026, "week": 1, "home_team": "SF", "away_team": "MIA", "home_score": 24, "away_score": 17, "gameday": "2026-09-01"},
        {"season": 2026, "week": 1, "home_team": "DAL", "away_team": "PHI", "home_score": 21, "away_score": 20, "gameday": "2026-09-01"},
    ],
    "source_identifier": "nflverse_games",
    "source_url": "https://github.com/nflverse/nfldata/raw/master/data/games.csv",
    "retrieved_at": "2026-09-19T10:00:00+00:00",
    "generated_at": "2026-09-19T10:05:00+00:00",
    "model_version": MODEL_VERSION,
    "freshness_threshold_id": "elo-source-12h",
    "freshness_threshold_seconds": 43200,
    "source_checksum": "sha256:test",
    "now": NOW,
}


def build(**updates):
    values = {**BASE, **updates}
    values["scheduled_games"] = [{"scheduled_at": NOW + timedelta(days=3), **game} for game in values["scheduled_games"]]
    values["historical_rows"] = [{"gameday": "2026-09-01", **row} for row in values["historical_rows"]]
    return build_evidence_batch(**values)


class ScheduleCursor:
    def __init__(self, rows):
        self.rows = rows
        self.query = ""

    def execute(self, query, params):
        self.query = query

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def fetchall(self):
        return self.rows


class ScheduleConnection:
    def __init__(self, rows):
        self.cursor_instance = ScheduleCursor(rows)

    def cursor(self):
        return self.cursor_instance


def test_canonical_schedule_reader_returns_week_rows_and_identity():
    connection = ScheduleConnection([(2026, 3, 17, NOW, "MIA", "SF")])
    rows = canonical_schedule_games(connection, 2026, 3)
    assert rows == [{"season": 2026, "week": 3, "game_id": "2026-w3-sf-mia", "match_number": 17, "scheduled_at": NOW, "home_team": "MIA", "away_team": "SF"}]
    assert "FROM nfl_schedule" in connection.cursor_instance.query
    assert "yahoo_pickem_games" not in connection.cursor_instance.query


def test_empty_canonical_schedule_does_not_fall_back_to_partial_pickem_data():
    connection = ScheduleConnection([])
    assert canonical_schedule_games(connection, 2026, 3) == []
    assert "FROM nfl_schedule" in connection.cursor_instance.query


def test_current_and_verified_historical_identities_resolve():
    assert abbr("SF") == "SF"
    assert abbr("OAK") == "LV"
    result = build(
        scheduled_games=[{"game_id": "2026-w3-lv-sf", "home_team": "SF", "away_team": "LV"}],
        historical_rows=[{"season": 2025, "week": 1, "home_team": "OAK", "away_team": "SF", "home_score": 20, "away_score": 17, "gameday": "2025-09-01"}],
    )
    assert result["available"] is True
    assert result["historical_rows_unresolved"] == []
    assert result["lineage"]["historical_identity_lineage"][0]["raw_identity"] == "OAK"
    assert result["lineage"]["historical_identity_lineage"][0]["canonical_identity"] == "LV"


def test_unknown_historical_identity_is_disclosed_without_guessing_when_irrelevant():
    result = build(historical_rows=BASE["historical_rows"] + [{"season": 2025, "week": 1, "home_team": "XXX", "away_team": "YYY", "home_score": 20, "away_score": 17, "gameday": "2025-09-01"}])
    assert result["available"] is True
    assert result["historical_rows_unresolved"][0]["classification"] == "UNSUPPORTED"
    assert result["historical_rows_unresolved"][0]["home_team"] == "XXX"


def test_unknown_historical_identity_affecting_scheduled_team_blocks():
    result = build(historical_rows=BASE["historical_rows"] + [{"season": 2025, "week": 1, "home_team": "XXX", "away_team": "SF", "home_score": 20, "away_score": 17, "gameday": "2025-09-01"}])
    assert result["available"] is False
    assert "ELO_HISTORICAL_RECONSTRUCTION_INCOMPLETE" in result["blocker_reasons"]


def test_missing_freshness_threshold_remains_unavailable_after_complete_coverage():
    result = build(freshness_threshold_id=None, freshness_threshold_seconds=None)
    assert result["expected_game_count"] == result["usable_game_count"] == 2
    assert result["expected_team_count"] == result["resolved_team_count"] == 4
    assert result["available"] is False
    assert result["freshness_state"] == "UNAVAILABLE"
    assert "ELO_FRESHNESS_THRESHOLD_UNAVAILABLE" in result["blocker_reasons"]
    assert result["validated_games"]
    assert result["authority_state"] == "INFORMATIONAL_ONLY"
    assert result["decision_effect"] == "NONE"


def test_structural_blockers_keep_validated_games_empty():
    result = build(
        scheduled_games=[{"game_id": "2026-w3-dal-phi", "home_team": "PHI", "away_team": "DAL"}],
        historical_rows=[BASE["historical_rows"][0]],
    )
    assert result["validated_games"] == []
    assert "ELO_SCHEDULE_TEAM_RATING_MISSING" in result["blocker_reasons"]


def test_target_week_future_rows_are_excluded_before_score_parsing():
    result = build(historical_rows=BASE["historical_rows"] + [{"season": 2026, "week": 3, "home_team": "XXX", "away_team": "YYY", "home_score": "", "away_score": ""}])
    assert result["available"] is True
    assert result["replay_classification_counts"]["EXCLUDED_FUTURE_GAME"] == 1
    assert result["replay_classification_counts"]["BLOCKING_MALFORMED_COMPLETED_GAME"] == 0


def test_unplayed_prior_row_is_excluded_not_malformed():
    result = build(historical_rows=BASE["historical_rows"] + [{"season": 2026, "week": 2, "home_team": "ARI", "away_team": "ATL", "home_score": "", "away_score": "", "gameday": "2026-09-10"}])
    assert result["available"] is True
    assert result["replay_classification_counts"]["EXCLUDED_UNPLAYED_GAME"] == 1
    assert result["replay_classification_counts"]["BLOCKING_MALFORMED_COMPLETED_GAME"] == 0


def test_unsupported_status_is_excluded_without_guessing_completion():
    result = build(historical_rows=BASE["historical_rows"] + [{"season": 2026, "week": 2, "home_team": "ARI", "away_team": "ATL", "home_score": 20, "away_score": 17, "status": "unknown-status", "gameday": "2026-09-10"}])
    assert result["available"] is True
    assert result["replay_classification_counts"]["EXCLUDED_UNSUPPORTED_STATUS"] == 1


def test_completed_row_missing_score_blocks_replay():
    result = build(historical_rows=BASE["historical_rows"] + [{"season": 2026, "week": 2, "home_team": "SF", "away_team": "MIA", "home_score": "", "away_score": 17, "status": "final", "gameday": "2026-09-10"}])
    assert result["available"] is False
    assert result["replay_classification_counts"]["BLOCKING_MALFORMED_COMPLETED_GAME"] == 1
    assert "ELO_HISTORICAL_RECONSTRUCTION_INCOMPLETE" in result["blocker_reasons"]


def test_classification_counts_reconcile_to_every_input_row():
    rows = BASE["historical_rows"] + [
        {"season": 2026, "week": 3, "home_team": "XXX", "away_team": "YYY", "home_score": "", "away_score": ""},
        {"season": 2026, "week": 2, "home_team": "ARI", "away_team": "ATL", "home_score": "", "away_score": "", "gameday": "2026-09-10"},
    ]
    result = build(historical_rows=rows)
    assert sum(result["replay_classification_counts"].values()) == len(rows)
    assert set(result["replay_classification_counts"]) == set(REPLAY_CLASSIFICATIONS)


def test_completed_prior_game_updates_rating_and_cutoff_game_does_not():
    prior = [{"season": 2026, "week": 1, "home_team": "SF", "away_team": "MIA", "home_score": 30, "away_score": 0, "gameday": "2026-09-01"}]
    ratings, _, _, _, counts = reconstruct_ratings(prior, 2026, 3, NOW + timedelta(days=3))
    assert ratings["SF"] != INITIAL_RATING
    assert counts["INCLUDED_COMPLETED_GAME"] == 1
    cutoff_row = [{"season": 2026, "week": 3, "home_team": "SF", "away_team": "MIA", "home_score": 30, "away_score": 0, "gameday": "2026-09-22"}]
    ratings, _, _, _, counts = reconstruct_ratings(cutoff_row, 2026, 3, NOW + timedelta(days=3))
    assert ratings == {}
    assert counts["EXCLUDED_FUTURE_GAME"] == 1


def test_retrieval_and_source_recorded_timestamps_are_distinct_utc_values():
    class Response:
        headers = {"Last-Modified": "Fri, 19 Sep 2026 10:00:00 GMT"}

    source_recorded_at, raw_header = _source_timestamp(Response())
    result = build(retrieved_at=NOW, source_recorded_at=source_recorded_at, source_recorded_raw=raw_header)
    assert result["retrieved_at"] != result["source_recorded_at"]
    assert result["retrieved_at"].tzinfo is not None
    assert result["source_recorded_at"].tzinfo is not None
    assert result["generated_at"].tzinfo is not None
    assert result["lineage"]["source_recorded_raw"] == raw_header


def test_missing_optional_source_recorded_timestamp_does_not_erase_retrieval_time():
    result = build(source_recorded_at=None)
    assert result["available"] is True
    assert result["retrieved_at"] is not None
    assert result["source_recorded_at"] is None


def test_complete_week_has_explicit_model_and_exact_counts():
    result = build()
    assert result["available"] is True
    assert result["model_name"] == MODEL_NAME
    assert result["model_version"] == MODEL_VERSION
    assert result["initial_rating"] == INITIAL_RATING
    assert result["expected_team_count"] == 4
    assert result["resolved_team_count"] == 4
    assert result["expected_game_count"] == 2
    assert result["usable_game_count"] == 2
    assert result["completeness_state"] == "COMPLETE"
    assert result["validated_games"][0] == {
        "game_id": "2026-w3-dal-phi",
        "home_team": "PHI",
        "away_team": "DAL",
        "home_rating": result["team_ratings"]["PHI"],
        "away_rating": result["team_ratings"]["DAL"],
    }


def test_complete_week_has_model_only_informational_provenance():
    result = build()
    assert result["source_type"] == "MODEL_ONLY"
    assert result["authority_state"] == "INFORMATIONAL_ONLY"
    assert result["decision_effect"] == "NONE"
    assert result["source_identifier"] == "nflverse_games"
    assert result["source_checksum"] == "sha256:test"
    assert result["lineage"]["initial_rating_is_model_parameter"] is True


def test_missing_scheduled_team_does_not_use_1500_fallback():
    result = build(
        scheduled_games=[{"game_id": "2026-w3-dal-phi", "home_team": "PHI", "away_team": "DAL"}],
        historical_rows=[BASE["historical_rows"][0]],
    )
    assert result["available"] is False
    assert result["team_ratings"] == {}
    assert "ELO_SCHEDULE_TEAM_RATING_MISSING" in result["blocker_reasons"]


def test_unresolved_canonical_identity_blocks_batch():
    result = build(scheduled_games=[{"game_id": "2026-w3-xxx-mia", "home_team": "MIA", "away_team": "XXX"}])
    assert result["available"] is False
    assert "ELO_CANONICAL_IDENTITY_UNRESOLVED" in result["blocker_reasons"]
    assert "XXX" in result["unresolved_identities"]


def test_duplicate_schedule_identity_blocks_batch():
    games = [
        {"game_id": "2026-w3-sf-mia", "home_team": "MIA", "away_team": "SF"},
        {"game_id": "2026-w3-sf-dal", "home_team": "DAL", "away_team": "SF"},
    ]
    result = build(scheduled_games=games)
    assert result["available"] is False
    assert "ELO_DUPLICATE_IDENTITY" in result["blocker_reasons"]
    assert "SF" in result["duplicate_identities"]


@pytest.mark.parametrize(
    "field, blocker",
    [
        ("retrieved_at", "ELO_RETRIEVED_TIMESTAMP_UNAVAILABLE"),
        ("model_version", "ELO_MODEL_VERSION_UNAVAILABLE"),
        ("freshness_threshold_id", "ELO_FRESHNESS_THRESHOLD_UNAVAILABLE"),
    ],
)
def test_required_provenance_fields_fail_closed(field, blocker):
    result = build(**{field: None})
    assert result["available"] is False
    assert blocker in result["blocker_reasons"]


def test_stale_source_evidence_is_unavailable():
    result = build(retrieved_at="2026-09-17T00:00:00+00:00")
    assert result["available"] is False
    assert result["freshness_state"] == "STALE"
    assert result["completeness_state"] == "INCOMPLETE"
    assert "ELO_SOURCE_DATA_STALE" in result["blocker_reasons"]


def test_missing_schedule_evidence_is_unavailable():
    result = build(scheduled_games=[])
    assert result["available"] is False
    assert "ELO_SCHEDULE_EVIDENCE_UNAVAILABLE" in result["blocker_reasons"]


def test_output_is_compatible_with_model_only_probability_contract():
    result = build()
    game = result["validated_games"][0]
    probability = build_model_only_future_probability(
        season=result["season"],
        week=result["week"],
        game_id=game["game_id"],
        home_team=game["home_team"],
        away_team=game["away_team"],
        home_elo=game["home_rating"],
        away_elo=game["away_rating"],
        source_identifiers={"ratings": result["source_identifier"]},
        source_recorded_at=result["retrieved_at"],
        generated_at=result["generated_at"],
        model_version=result["model_version"],
        freshness_threshold_id=result["freshness_threshold_id"],
        freshness_threshold_seconds=BASE["freshness_threshold_seconds"],
        now=NOW,
    )
    assert probability["available"] is True
    assert probability["home_win_probability"] + probability["away_win_probability"] == pytest.approx(1.0)
    assert probability["source_type"] == "MODEL_ONLY"
    assert probability["authority_state"] == "INFORMATIONAL_ONLY"
    assert probability["decision_effect"] == "NONE"


# --- Elo source observation persistence (append-only, evidence collection only) ---

from batch_e_ratings import record_elo_source_observation, record_elo_source_retrieval_failure


class EloObservationCursor:
    def __init__(self, existing=None, fail_after=None):
        self.statements = []
        self.rows = list(existing or [])
        self.fail_after = fail_after
        self._next_id = len(self.rows) + 1
        self._last_result = None

    def execute(self, sql, params=None):
        self.statements.append((sql, params))
        if self.fail_after is not None and len(self.statements) > self.fail_after:
            raise RuntimeError("SIMULATED_TRANSACTION_FAILURE")
        normalized = " ".join(sql.split())
        if normalized.startswith("SELECT source_checksum, retrieved_at"):
            observed = [row for row in self.rows if row["observation_state"] == "OBSERVED"]
            self._last_result = (observed[-1]["source_checksum"], observed[-1]["retrieved_at"]) if observed else None
        elif normalized.startswith("INSERT INTO model_only_elo_source_observations"):
            keys = ["domain", "source_identifier", "source_url", "retrieved_at", "source_recorded_at",
                    "source_recorded_at_available", "source_checksum", "etag", "content_length_header",
                    "content_length_actual", "http_status", "changed_from_previous", "previous_checksum",
                    "previous_retrieved_at", "observation_state", "blocker_reason"]
            self.rows.append(dict(zip(keys, params)))
            self._last_result = (self._next_id,)
            self._next_id += 1
        else:
            self._last_result = None

    def fetchone(self):
        return self._last_result

    def close(self):
        pass


class EloObservationConnection:
    def __init__(self, existing=None, fail_after=None):
        self.cursor_instance = EloObservationCursor(existing=existing, fail_after=fail_after)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    @property
    def rows(self):
        return self.cursor_instance.rows


def observe(conn, checksum="checksum-a", source_recorded_at=None, retrieved_at=NOW):
    return record_elo_source_observation(
        conn, source_identifier="nflverse_games", source_url=BASE["source_url"], retrieved_at=retrieved_at,
        source_recorded_at=source_recorded_at, source_checksum=checksum, etag="etag-1",
        content_length_header="511630", content_length_actual=2179202, http_status=200,
    )


def test_first_observation_has_no_prior_reference():
    conn = EloObservationConnection()
    result = observe(conn)
    assert result["changed_from_previous"] is None
    assert result["previous_checksum"] is None
    assert result["previous_retrieved_at"] is None
    assert len(conn.rows) == 1
    assert conn.rows[0]["observation_state"] == "OBSERVED"
    assert conn.commits == 1 and conn.rollbacks == 0


def test_second_observation_with_same_checksum_is_unchanged():
    conn = EloObservationConnection()
    observe(conn, checksum="checksum-a", retrieved_at=NOW)
    result = observe(conn, checksum="checksum-a", retrieved_at=NOW + timedelta(hours=1))
    assert result["changed_from_previous"] is False
    assert result["previous_checksum"] == "checksum-a"
    assert result["previous_retrieved_at"] == NOW
    assert len(conn.rows) == 2


def test_later_observation_with_different_checksum_is_changed():
    conn = EloObservationConnection()
    observe(conn, checksum="checksum-a", retrieved_at=NOW)
    observe(conn, checksum="checksum-a", retrieved_at=NOW + timedelta(hours=1))
    result = observe(conn, checksum="checksum-b", retrieved_at=NOW + timedelta(hours=2))
    assert result["changed_from_previous"] is True
    assert result["previous_checksum"] == "checksum-a"
    assert result["previous_retrieved_at"] == NOW + timedelta(hours=1)
    assert len(conn.rows) == 3


def test_missing_last_modified_stores_unavailable_not_fabricated():
    conn = EloObservationConnection()
    observe(conn, source_recorded_at=None)
    stored = conn.rows[0]
    assert stored["source_recorded_at"] is None
    assert stored["source_recorded_at_available"] is False


def test_retrieval_time_is_never_copied_into_source_recorded_at():
    conn = EloObservationConnection()
    observe(conn, source_recorded_at=None, retrieved_at=NOW)
    stored = conn.rows[0]
    assert stored["retrieved_at"] == NOW
    assert stored["source_recorded_at"] is None
    assert stored["source_recorded_at"] != stored["retrieved_at"]


def test_etag_is_stored_but_not_treated_as_a_timestamp():
    conn = EloObservationConnection()
    observe(conn)
    stored = conn.rows[0]
    assert stored["etag"] == "etag-1"
    assert not isinstance(stored["etag"], datetime)


def test_identical_observations_remain_separate_append_only_records():
    conn = EloObservationConnection()
    observe(conn, checksum="checksum-a", retrieved_at=NOW)
    observe(conn, checksum="checksum-a", retrieved_at=NOW + timedelta(hours=1))
    observe(conn, checksum="checksum-a", retrieved_at=NOW + timedelta(hours=2))
    assert len(conn.rows) == 3
    assert len({row["retrieved_at"] for row in conn.rows}) == 3
    for statement, _ in conn.cursor_instance.statements:
        normalized = " ".join(statement.split()).upper()
        assert not normalized.startswith("UPDATE ")
        assert not normalized.startswith("DELETE ")


def test_failed_retrieval_never_replaces_prior_successful_evidence():
    conn = EloObservationConnection()
    observe(conn, checksum="checksum-a", retrieved_at=NOW)
    record_elo_source_retrieval_failure(
        conn, source_identifier="nflverse_games", source_url=BASE["source_url"],
        http_status=503, blocker_reason="ELO_SOURCE_RETRIEVAL_FAILED",
    )
    assert len(conn.rows) == 2
    assert conn.rows[0]["observation_state"] == "OBSERVED"
    assert conn.rows[0]["source_checksum"] == "checksum-a"
    assert conn.rows[1]["observation_state"] == "RETRIEVAL_FAILED"
    assert conn.rows[1]["source_checksum"] is None
    prior = _latest_observation_for_test(conn)
    assert prior == ("checksum-a", NOW)


def _latest_observation_for_test(conn):
    observed = [row for row in conn.rows if row["observation_state"] == "OBSERVED"]
    last = observed[-1]
    return (last["source_checksum"], last["retrieved_at"])


def test_observation_persistence_does_not_alter_probability_fail_closed_contract():
    conn = EloObservationConnection()
    observe(conn)
    result = build(freshness_threshold_id=None, freshness_threshold_seconds=None)
    assert result["available"] is False
    assert result["freshness_state"] == "UNAVAILABLE"
    assert result["authority_state"] == "INFORMATIONAL_ONLY"
    assert result["decision_effect"] == "NONE"
    assert "ELO_FRESHNESS_THRESHOLD_UNAVAILABLE" in result["blocker_reasons"]


def test_transaction_failure_rolls_back_partial_observation_write():
    conn = EloObservationConnection(fail_after=2)
    with pytest.raises(RuntimeError):
        observe(conn)
    assert conn.rollbacks == 1
    assert conn.commits == 0
    assert conn.rows == []


def test_existing_rating_publication_behavior_is_unchanged():
    result = build()
    assert result["available"] is True
    assert result["team_ratings"]
    assert result["validated_games"]
