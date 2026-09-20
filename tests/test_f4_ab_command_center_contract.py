from pathlib import Path

from owner_operations import build_gm_waiver_watch_actions

def test_gm_template_contract():
    t=Path("templates/gm.html").read_text(encoding="utf-8")
    assert "decision_ranking.actions" in t and "decision_ranking.blocked_actions" in t
    assert "matchup_intelligence.favorable_matchups" in t and "matchup_intelligence.difficult_matchups" in t
    assert "No lineup, waiver, or trade transaction is submitted" in t

def test_owner_integration_contract():
    t=Path("owner_operations.py").read_text(encoding="utf-8")
    assert "from services.decision_ranking import build_action, build_decision_ranking" in t
    assert "from services.matchup_intelligence import build_matchup_intelligence" in t
    assert "decision_ranking=decision_ranking" in t and "matchup_intelligence=matchup_intelligence" in t


def test_unverified_gm_waivers_are_informational_only():
    waivers = [{"player": "Candidate", "faab": 12, "priority_score": 8.5, "need": 1}]
    assert build_gm_waiver_watch_actions(waivers, "UNVERIFIED") == []


def test_verified_gm_waivers_keep_existing_watch_actions():
    waivers = [{"player": "Candidate", "faab": 12, "priority_score": 8.5, "need": 1}]
    actions = build_gm_waiver_watch_actions(waivers, "VERIFIED")
    assert len(actions) == 1
    assert actions[0].action_id == "waiver-watch:1:Candidate"


def test_gm_template_labels_unverified_faab_as_informational():
    template = Path("templates/gm.html").read_text(encoding="utf-8")
    assert "Local FAAB estimate" in template
    assert "Informational estimate" in template
