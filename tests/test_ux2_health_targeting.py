def test_unknown_health_forces_monitor():
    from services.team_health import (
        apply_player_health_to_recommendations,
    )

    players = [
        {
            "player": "Unknown Player",
            "injury_status": "Unknown",
            "decision": "START",
            "confidence": {
                "label": "HIGH",
                "score": 90,
            },
            "evidence_gaps": [],
        }
    ]

    result = apply_player_health_to_recommendations(
        players,
        source="Sleeper",
        freshness_state="FRESH",
    )

    player = result[0]

    assert player["decision"] == "MONITOR"


def test_healthy_player_remains_start():
    from services.team_health import (
        apply_player_health_to_recommendations,
    )

    players = [
        {
            "player": "Healthy Player",
            "injury_status": "Healthy / Not listed",
            "decision": "START",
            "confidence": {
                "label": "HIGH",
                "score": 90,
            },
            "evidence_gaps": [],
        }
    ]

    result = apply_player_health_to_recommendations(
        players,
        source="Sleeper",
        freshness_state="FRESH",
    )

    player = result[0]

    assert player["decision"] == "START"
