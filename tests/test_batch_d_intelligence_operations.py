import pytest
from intelligence.intelligence_explainability import build_explanation
from intelligence.intelligence_readiness import calculate_readiness, validate_weekly_inputs
from intelligence.intelligence_reconciliation import reconcile
from intelligence.intelligence_calibration import calibration_summary
from weekly_intelligence_report import build_weekly_report

def test_explanation_components_and_edge():
    result = build_explanation(pick="AAA", probability=.70, crowd_percentage=.55, components=[
        {"name":"market", "value":.72, "weight":.55},
        {"name":"elo", "value":.68, "weight":.25},
        {"name":"situation", "value":.67, "weight":.20},
    ])
    assert result["contrarian_edge"] == pytest.approx(.15)
    assert len(result["components"]) == 3

def test_explanation_rejects_bad_weights():
    with pytest.raises(ValueError):
        build_explanation(pick="AAA", probability=.7, components=[{"name":"market","value":.7,"weight":.5}])

def test_readiness_publish_gate():
    result = calculate_readiness({k: 1 for k in ["schedule","market","crowd","ratings","injuries","weather","validation"]})
    assert result["score"] == 100 and result["publishable"]
    blocked = calculate_readiness({k: 1 for k in ["schedule","market","crowd","ratings","injuries","weather","validation"]}, blockers=["stale odds"])
    assert not blocked["publishable"]

def test_input_validation_rejects_duplicate_and_bad_yahoo_sum():
    g = {"season":2026,"week":1,"away_team":"A","home_team":"B","market_probability_home":.6,"yahoo_percentage_away":.2,"yahoo_percentage_home":.7}
    result = validate_weekly_inputs([g, g])
    assert any("duplicate" in x for x in result["blockers"])
    assert any("Yahoo" in x for x in result["blockers"])

def test_reconciliation_signals():
    assert reconcile(model_pick="A", model_probability=.7, crowd_pick="A", market_favorite="A")["signal"] == "CONSENSUS"
    assert reconcile(model_pick="A", model_probability=.7, crowd_pick="B", market_favorite="B")["signal"] == "EXTREME_CONTRARIAN"

def test_calibration_metrics():
    result = calibration_summary([{"probability":.8,"outcome":1},{"probability":.2,"outcome":0}])
    assert result["accuracy"] == 1
    assert result["brier_score"] == pytest.approx(.04)

def test_report_blocks_without_readiness():
    result = build_weekly_report(season=2026, week=1, recommendations=[])
    assert result["status"] == "BLOCKED"

def test_report_generates_from_real_inputs_only():
    rows = [
        {"model_pick":"A","model_probability":.80,"crowd_percentage":.75,"contrarian_edge":.05},
        {"model_pick":"B","model_probability":.62,"crowd_percentage":.30,"contrarian_edge":.32},
    ]
    result = build_weekly_report(season=2026, week=1, recommendations=rows, readiness={"publishable":True,"status":"READY","blockers":[]})
    assert result["lock_of_week"]["model_pick"] == "A"
    assert result["best_upset"]["model_pick"] == "B"
    assert result["expected_correct_picks"] == pytest.approx(1.42)
