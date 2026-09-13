from services.team_health import apply_player_health_to_recommendations

def row(status="ACTIVE", score=100):
    return {"player":"Player","injury_status":status,"confidence":{"label":"HIGH","score":score},"reason":"Supported reason.","evidence_gaps":[],"vacant":False}

def test_unknown_health_becomes_monitor():
    p=row(None); apply_player_health_to_recommendations([p])
    assert p["decision"]=="MONITOR" and p["confidence"]["score"]<=50
    assert "PLAYER_HEALTH_UNAVAILABLE" in p["evidence_gaps"]

def test_supported_health_is_not_degraded():
    p=row("ACTIVE",92); apply_player_health_to_recommendations([p])
    assert p["decision"]=="START" and p["confidence"]=={"label":"HIGH","score":92}

def test_stale_health_monitors():
    p=row("ACTIVE",95); apply_player_health_to_recommendations([p],freshness_state="STALE")
    assert p["decision"]=="MONITOR" and p["confidence"]["score"]<=50

def test_blocked_health_blocks():
    p=row("ACTIVE",95); apply_player_health_to_recommendations([p],blocker="HEALTH_REFRESH_FAILED")
    assert p["decision"]=="BLOCKED" and p["confidence"]=={"label":"BLOCKED","score":0}

def test_templates_show_decision_and_metadata():
    team=open("templates/_team_recommendations.html",encoding="utf-8").read(); health=open("templates/_team_health.html",encoding="utf-8").read()
    assert "decision-badge" in team and "player.decision or \"START\"" in team
    assert "team_health.last_verified" in health and "team_health.age" in health
