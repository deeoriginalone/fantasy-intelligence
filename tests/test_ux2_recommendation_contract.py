from pathlib import Path


TEAM_TEMPLATE = Path("templates/_team_recommendations.html")


def _template_text():
    return TEAM_TEMPLATE.read_text(encoding="utf-8")


def test_recommendation_cards_contain_required_labels():
    """
    UXQA-011:
    Recommendation rows must expose manager-facing context.
    """

    text = _template_text()

    required_labels = (
        "Slot",
        "Player",
        "Opponent",
        "Weekly value",
        "Health",
        "decision-badge",
        "Recommendation confidence",
        "Why:",
        "Evidence issue",
    )

    for label in required_labels:
        assert label in text


def test_recommendation_table_uses_player_context_fields():
    """
    Route payload must expose:
    player, slot, opponent, value, health,
    confidence, reason, blockers.
    """

    text = _template_text()

    expected_fields = (
        "player.slot",
        "player.player",
        "player.opponent",
        "player.health_evidence",
        "player.decision",
        "player.reason",
        "player.confidence",
        "player.evidence_gaps",
    )

    for field in expected_fields:
        assert field in text


def test_weekly_score_distinguishes_unavailable_from_zero():
    """
    UXQA-006:
    Unavailable must not silently become 0.
    """

    text = _template_text()

    assert "weekly_score" in text

    disallowed_patterns = (
        "weekly_score or 0",
        "weekly_score, 0",
        "get('weekly_score', 0)",
        "or 0.0",
    )

    for pattern in disallowed_patterns:
        assert pattern not in text


def test_recommendation_row_contains_reason_and_confidence():
    """
    UX.2 recommendation behavior:
    supported recommendations require
    confidence and reason.
    """

    text = _template_text()

    assert "confidence" in text.lower()
    assert "reason" in text.lower()


def test_recommendation_row_contains_blockers():
    """
    Recommendation must identify
    the exact blocker impacting it.
    """

    text = _template_text()

    assert "evidence_gaps" in text or "blockers" in text.lower()


def test_template_contains_monitor_state():
    """
    Strategy contract:
    START / SIT / FLEX / MONITOR.
    """

    text = _template_text()

    assert "MONITOR" in text or "decision" in text


def test_template_contains_health_column():
    """
    Health must be visible and not implicit.
    """

    text = _template_text()

    assert "Health" in text
    assert "health_evidence.health_state" in text


def test_recommendation_evidence_exposes_health_impact_and_freshness():
    text = Path("templates/_team_recommendations.html").read_text(encoding="utf-8")
    for field in ("weekly_value_state", "player.health_evidence", "player.health_evidence.freshness_state", "player.health_evidence.recommendation_impact", "player.confidence", "player.reason", "player.evidence_gaps"):
        assert field in text
