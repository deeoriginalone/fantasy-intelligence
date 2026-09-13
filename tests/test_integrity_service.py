from services.integrity import (
    build_integrity_report,
    calculate_completeness_score,
)


def player(**kw):
    row = {
        "player": "Test",
        "injury_status": "Healthy",
        "weekly_score": 10,
        "weekly_baseline": 10,
        "opponent": "KC",
        "matchup_rank": 15,
        "evidence_gaps": [],
    }

    row.update(kw)
    return row


def test_complete_player_scores_100():
    assert calculate_completeness_score(
        player()
    ) == 100


def test_missing_matchup_lowers_score():
    assert (
        calculate_completeness_score(
            player(matchup_rank=None)
        )
        < 100
    )


def test_integrity_report_builds():
    report = build_integrity_report(
        [
            player(),
            player(
                injury_status="Unknown",
                matchup_rank=None,
                evidence_gaps=[
                    "INJURY_STATUS_UNRESOLVED"
                ],
            ),
        ]
    )

    assert report["player_count"] == 2

    assert (
        "INJURY_STATUS_UNRESOLVED"
        in report["blockers"]
    )
