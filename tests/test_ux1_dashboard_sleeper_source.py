import app as application


def install_sources(monkeypatch, league, users, rosters):
    monkeypatch.setattr(application, "get_league", lambda _league_id: league)
    monkeypatch.setattr(application, "get_users", lambda _league_id: users)
    monkeypatch.setattr(application, "get_rosters", lambda _league_id: rosters)


def test_verified_sleeper_metadata(monkeypatch):
    install_sources(monkeypatch,
        {"name":"Verified League","total_rosters":10,"scoring_settings":{"rec":1.0}},
        [{"is_owner":True,"display_name":"Owner","metadata":{"team_name":"Verified Team"}}],
        [{"roster_id":1}],
    )
    row,error=application.get_local_league()
    assert row == ("Verified League","Verified Team",10,"Full PPR")
    assert error is None


def test_half_ppr_and_display_name_fallback(monkeypatch):
    install_sources(monkeypatch,
        {"name":"Verified League","total_rosters":10,"scoring_settings":{"rec":0.5}},
        [{"is_owner":True,"display_name":"Owner"}],
        [{"roster_id":1}],
    )
    row,error=application.get_local_league()
    assert row == ("Verified League","Owner",10,"Half PPR")
    assert error is None


def test_missing_owner_fails_closed(monkeypatch):
    install_sources(monkeypatch,
        {"name":"Verified League","total_rosters":10,"scoring_settings":{"rec":1.0}},
        [],
        [{"roster_id":1}],
    )
    row,error=application.get_local_league()
    assert row == ("Verified League",None,10,"Full PPR")
    assert error == "LEAGUE_METADATA_INCOMPLETE"


def test_missing_source_fails_closed(monkeypatch):
    install_sources(monkeypatch, None, [], [])
    row,error=application.get_local_league()
    assert row is None
    assert error == "LEAGUE_SOURCE_UNAVAILABLE"
