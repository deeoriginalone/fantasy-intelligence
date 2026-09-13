from jinja2 import Environment

SCORE_CELL = """
{% if player.get('weekly_score') is not none %}
{{ '%.2f'|format(player.get('weekly_score')) }}
{% else %}
Unavailable
{% endif %}
"""

def render_score(value):
    return Environment().from_string(
        SCORE_CELL
    ).render(
        player={"weekly_score": value}
    ).strip()

def test_unavailable_weekly_score_renders_unavailable():
    assert render_score(None) == "Unavailable"

def test_verified_zero_weekly_score_renders_numeric_zero():
    assert render_score(0) == "0.00"

def test_supported_weekly_score_renders_two_decimals():
    assert render_score(12.345) == "12.35"
