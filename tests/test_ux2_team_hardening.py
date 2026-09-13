from services.team_hardening import build_bench_decisions, build_roster_outlook, build_team_trust_summary, build_weekly_risks


def starter(name, slot="WR1", decision="START", score=10):
    return {"player": name, "slot": slot, "position": "WR", "decision": decision, "weekly_score": score, "health_evidence": {"state": "AVAILABLE", "freshness_state": "FRESH", "recommendation_impact": "Supported."}, "reason": "Supported role.", "evidence_gaps": []}


def test_trust_summary_keeps_domains_separate():
    result = build_team_trust_summary({"matchups": {"state": "UNAVAILABLE"}, "blockers": ["MATCHUP_RANK_CONTRACT_INCOMPLETE"]}, {"freshness_state": "UNAVAILABLE", "recommendation_impact": "Health unavailable."}, [starter("A")], [starter("B")])
    assert result["health"]["state"] == "UNAVAILABLE"
    assert result["matchups"]["state"] == "UNAVAILABLE"
    assert result["weekly_values"]["state"] == "AVAILABLE"
    assert result["confidence"]["label"] == "LOW"


def test_bench_decision_respects_slot_eligibility():
    result = build_bench_decisions([starter("Starter", slot="WR1", decision="MONITOR")], [starter("Bench", slot="BN", score=12)])
    assert result[0]["state"] == "AVAILABLE"
    assert result[0]["slot"] == "WR1"
    assert result[0]["player"] == "Bench"


def test_bench_decision_fails_closed_without_alternative():
    result = build_bench_decisions([starter("Starter", slot="WR1", decision="MONITOR")], [starter("Bench", slot="BN", score=None)])
    assert result[0]["state"] == "UNAVAILABLE"
    assert "No supported alternative" in result[0]["reason"]


def test_k_and_def_contingencies_require_position_valid_alternatives():
    starters = [starter("Kicker", slot="K", decision="MONITOR"), starter("Defense", slot="DEF", decision="MONITOR")]
    bench = [dict(starter("Bench K", slot="BN", score=12), position="K"), dict(starter("Bench DEF", slot="BN", score=11), position="DEF")]
    result = build_bench_decisions(starters, bench)
    assert [(item["slot"], item["player"], item["state"]) for item in result] == [("K", "Bench K", "AVAILABLE"), ("DEF", "Bench DEF", "AVAILABLE")]


def test_reused_bench_alternative_is_marked_conditional():
    starters = [starter("Starter A", slot="WR1", decision="MONITOR"), starter("Starter B", slot="WR2", decision="MONITOR")]
    bench = [starter("One Bench", slot="BN", score=12)]
    result = build_bench_decisions(starters, bench)
    assert len(result) == 2
    assert result[1]["player"] == "One Bench"
    assert "Conditional alternative" in result[1]["reason"]


def test_weekly_risks_are_deterministic_and_deduplicated():
    result = build_weekly_risks([starter("Starter", decision="MONITOR", score=None)], {"RB": {"strategic_need": "ADD_DEPTH", "drivers": ["3 RB options against target 4"]}}, {"freshness_state": "UNAVAILABLE", "recommendation_impact": "Health unavailable."}, {"matchups": {"state": "UNAVAILABLE"}})
    keys = [risk["key"] for risk in result]
    assert keys == sorted(set(keys))
    assert "health:players" in keys
    assert "need:RB" in keys
    assert "matchup:team" in keys


def test_roster_outlook_does_not_invent_playoff_readiness():
    result = build_roster_outlook({"RB": {"strategic_need": "ADD_DEPTH"}}, {"freshness_state": "UNAVAILABLE"})
    assert result["depth"]["state"] == "REVIEW"
    assert result["playoff_readiness"]["state"] == "UNAVAILABLE"
