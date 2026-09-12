from pathlib import Path

def test_team_template_wires_accuracy_partial():
    text=Path("templates/team.html").read_text(encoding="utf-8")
    assert '{% include "_team_accuracy.html" %}' in text
    assert text.index('{% include "_team_accuracy.html" %}') < text.index("Recommended Starting Lineup")

def test_accuracy_partial_explains_required_domains():
    text=Path("templates/_team_accuracy.html").read_text(encoding="utf-8")
    for phrase in ("Why This Recommendation Is Trusted","League and Scoring Settings","Full-PPR Team Needs","Starter Matchup Evidence","Displayed Metric Guidance"):
        assert phrase in text
    assert '{% include "_team_health.html" %}' in text
