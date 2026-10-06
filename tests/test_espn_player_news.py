from services.espn_player_news import news_for_espn_player, read_espn_nfl_news, reset_espn_news_cache


def test_espn_feed_uses_exact_athlete_ids_and_returns_dated_informational_news():
    reset_espn_news_cache()
    payload = {
        "articles": [
            {
                "id": 123,
                "headline": "Player update",
                "description": "Published player-specific report.",
                "published": "2026-10-06T12:00:00Z",
                "lastModified": "2026-10-06T12:30:00Z",
                "categories": [{"type": "athlete", "athleteId": 8154}],
                "links": {"web": {"href": "https://espn.example/story/123"}},
            },
            {"id": 456, "headline": "Team only", "categories": [{"type": "team", "teamId": 1}]},
        ]
    }
    feed = read_espn_nfl_news(fetch_json=lambda: payload, force_refresh=True)
    player_news = news_for_espn_player(feed, 8154)
    other_player = news_for_espn_player(feed, 8155)

    assert feed["state"] == "AVAILABLE"
    assert player_news["state"] == "AVAILABLE"
    assert player_news["freshness_state"] == "UNVERIFIED"
    assert player_news["decision_effect"] == "INFORMATIONAL_ONLY"
    assert player_news["articles"][0]["headline"] == "Player update"
    assert player_news["articles"][0]["published_at"] == "2026-10-06T12:00:00Z"
    assert other_player["state"] == "UNAVAILABLE"
    assert other_player["blockers"] == ["ESPN_PLAYER_NEWS_NOT_IN_FEED"]


def test_espn_feed_cache_avoids_repeated_network_reads_and_preserves_failure():
    reset_espn_news_cache()
    calls = []
    payload = {"articles": []}
    first = read_espn_nfl_news(fetch_json=lambda: calls.append(1) or payload, force_refresh=True)
    second = read_espn_nfl_news(fetch_json=lambda: calls.append(2) or payload)

    assert first["state"] == second["state"] == "AVAILABLE"
    assert len(calls) == 1
    reset_espn_news_cache()
    failed = read_espn_nfl_news(fetch_json=lambda: (_ for _ in ()).throw(ValueError("bad feed")), force_refresh=True)
    assert failed["state"] == "UNAVAILABLE"
    assert failed["blockers"] == ["ESPN_NEWS_FEED_REQUEST_FAILED"]


def test_espn_news_does_not_fall_back_to_player_name_when_id_is_missing():
    result = news_for_espn_player({"state": "AVAILABLE", "articles": [{"headline": "Brian Robinson update", "espn_athlete_ids": ["4241474"]}]}, None)

    assert result["state"] == "UNAVAILABLE"
    assert result["articles"] == []
    assert result["blockers"] == ["ESPN_PLAYER_ID_UNAVAILABLE"]