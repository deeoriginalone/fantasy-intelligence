import pytest

from survivor_store import (
    SurvivorConflictError,
    SurvivorHistoryReadError,
    ensure_pool,
    history,
    migrate,
    save_selection,
    used_teams,
)

TEST_POOL = "ux8-test-pool"
TEST_SEASON = 9999


@pytest.fixture(autouse=True)
def isolated_test_pool():
    migrate()
    ensure_pool(TEST_POOL, "UX.8 Test Pool", TEST_SEASON)
    yield
    import survivor_store
    conn = survivor_store.connect()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM survivor_selections WHERE pool_key=%s AND season=%s", (TEST_POOL, TEST_SEASON))
            cur.execute("DELETE FROM survivor_pools WHERE pool_key=%s", (TEST_POOL,))
        conn.commit()
    finally:
        conn.close()


def test_first_write_for_a_week_succeeds():
    save_selection(TEST_POOL, TEST_SEASON, 1, "JAX", "pending", None, None, "USER_RECORDED")
    rows = history(TEST_POOL, TEST_SEASON)
    assert [r["team"] for r in rows] == ["JAX"]


def test_status_update_for_same_team_does_not_conflict():
    save_selection(TEST_POOL, TEST_SEASON, 1, "JAX", "pending", None, None, "USER_RECORDED")
    save_selection(TEST_POOL, TEST_SEASON, 1, "JAX", "won", 0.7, 0.65, "result recorded")
    rows = history(TEST_POOL, TEST_SEASON)
    assert len(rows) == 1
    assert rows[0]["status"] == "won"


def test_different_team_same_week_raises_conflict_and_preserves_existing():
    save_selection(TEST_POOL, TEST_SEASON, 1, "JAX", "pending", None, None, "USER_RECORDED")
    with pytest.raises(SurvivorConflictError):
        save_selection(TEST_POOL, TEST_SEASON, 1, "KC", "pending", 0.6, 0.6, "")
    rows = history(TEST_POOL, TEST_SEASON)
    assert [r["team"] for r in rows] == ["JAX"]


def test_same_team_reused_in_a_different_week_fails_safely():
    save_selection(TEST_POOL, TEST_SEASON, 1, "JAX", "pending", None, None, "")
    with pytest.raises(Exception):
        save_selection(TEST_POOL, TEST_SEASON, 2, "JAX", "pending", 0.6, 0.6, "")


def test_used_teams_read_failure_raises_history_read_error(monkeypatch):
    import survivor_store

    def _boom():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(survivor_store, "connect", _boom)
    with pytest.raises(SurvivorHistoryReadError):
        used_teams(TEST_POOL, TEST_SEASON)


def test_empty_verified_history_differs_from_read_failure():
    assert used_teams(TEST_POOL, TEST_SEASON) == []
