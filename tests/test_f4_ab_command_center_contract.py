from pathlib import Path

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
