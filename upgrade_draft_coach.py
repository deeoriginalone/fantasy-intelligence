from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
TEMPLATE = ROOT / "templates" / "draftboard.html"


def require(text, token, label):
    if token not in text:
        raise RuntimeError(
            f"Could not find {label}. No project files were changed."
        )


def patch_app(text):
    if "def build_draft_coach_summary(" not in text:
        marker = "def fetch_available_players(cur):\n"
        require(text, marker, "fetch_available_players()")
        helper = '''def build_draft_coach_summary(
    recommendation,
    top_recommendations,
    recommendation_reasons,
    draft_now_wait,
    expected_value_analysis,
    monte_carlo,
    active_strategy,
    current_round,
    pick_forecast,
):
    """Create one concise, explainable draft-coach recommendation."""
    summary = {
        "player": None,
        "position": None,
        "rank": None,
        "draft_score": 0,
        "decision": "NO RECOMMENDATION",
        "confidence": 0,
        "confidence_label": "UNKNOWN",
        "strategy": active_strategy,
        "round": current_round,
        "next_pick": pick_forecast.get("next_pick"),
        "picks_until_next": pick_forecast.get("picks_until_next"),
        "availability_pct": None,
        "value_at_risk": 0,
        "reasons": list(recommendation_reasons[:5]),
    }

    if not recommendation or not top_recommendations:
        summary["reasons"].append("No available player could be scored.")
        return summary

    winner = top_recommendations[0]
    summary.update(
        player=recommendation[1],
        position=recommendation[2],
        rank=recommendation[0],
        draft_score=winner["draft_score"],
        decision=draft_now_wait.get("decision", "DRAFT NOW"),
    )

    simulation = next(
        (
            row
            for row in (monte_carlo.get("players") or [])
            if row["player"] == recommendation[1]
        ),
        None,
    )
    if simulation:
        summary["availability_pct"] = simulation["availability_pct"]

    ev_row = next(
        (
            row
            for row in (expected_value_analysis.get("players") or [])
            if row["player"] == recommendation[1]
        ),
        None,
    )
    if ev_row:
        summary["value_at_risk"] = ev_row["expected_value_loss"]

    score_component = min(35, max(0, winner["draft_score"] / 10))
    scarcity_component = min(15, winner.get("scarcity_score", 0) * 0.15)
    tier_component = min(15, winner.get("tier_bonus", 0) * 0.15)
    value_component = min(20, summary["value_at_risk"] * 0.25)

    availability_component = 0
    if summary["availability_pct"] is not None:
        availability_component = min(
            15,
            (100 - summary["availability_pct"]) * 0.15,
        )

    confidence = round(
        score_component
        + scarcity_component
        + tier_component
        + value_component
        + availability_component
    )
    summary["confidence"] = max(0, min(100, confidence))

    if summary["confidence"] >= 80:
        summary["confidence_label"] = "HIGH"
    elif summary["confidence"] >= 60:
        summary["confidence_label"] = "MEDIUM"
    else:
        summary["confidence_label"] = "LOW"

    if summary["availability_pct"] is not None:
        summary["reasons"].append(
            f"Estimated next-pick availability: "
            f"{summary['availability_pct']}%."
        )
    if summary["value_at_risk"] >= 25:
        summary["reasons"].append(
            f"Waiting puts approximately {summary['value_at_risk']} "
            "recommendation points at risk."
        )

    # Preserve order while removing repeated messages.
    summary["reasons"] = list(dict.fromkeys(summary["reasons"]))[:6]
    return summary


'''
        text = text.replace(marker, helper + marker, 1)

    if "    draft_coach = build_draft_coach_summary(" not in text:
        marker = "    return render_template(\n        \"draftboard.html\",\n"
        require(text, marker, "draftboard render_template()")
        block = '''    draft_coach = build_draft_coach_summary(
        team_recommendation,
        top_recommendations,
        recommendation_reasons,
        draft_now_wait,
        expected_value_analysis,
        monte_carlo,
        active_strategy,
        current_round,
        pick_forecast,
    )

'''
        text = text.replace(marker, block + marker, 1)

    if "        draft_coach=draft_coach,\n" not in text:
        marker = "        expected_value_analysis=expected_value_analysis,\n"
        require(text, marker, "Expected Value template argument")
        text = text.replace(
            marker,
            marker + "        draft_coach=draft_coach,\n",
            1,
        )

    return text


def patch_template(text):
    if "Fantasy Intelligence Draft Coach" not in text:
        anchor = '<div class="grid">'
        require(text, anchor, "top Draft Board grid")
        panel = '''<section class="card agent-card" style="grid-column:1/-1">
<div class="agent-header"><div><span class="agent-label">FANTASY INTELLIGENCE</span><h2>🏆 Fantasy Intelligence Draft Coach</h2></div><span class="agent-status">{{ draft_coach.confidence_label }} CONFIDENCE · {{ draft_coach.confidence }}%</span></div>
{% if draft_coach.player %}
<div class="highlight">
<div class="recommendation-label">{{ draft_coach.decision }}</div>
<h2>{{ draft_coach.player }}</h2>
<p><strong>{{ draft_coach.position }}</strong> · Overall Rank #{{ draft_coach.rank }} · Draft Score {{ draft_coach.draft_score }}</p>
<div class="agent-metrics">
<div class="metric"><span class="metric-label">Strategy</span><span class="metric-value">{{ strategy_profile.label }}</span></div>
<div class="metric"><span class="metric-label">Round</span><span class="metric-value">{{ draft_coach.round }}</span></div>
<div class="metric"><span class="metric-label">Next-Pick Availability</span><span class="metric-value">{% if draft_coach.availability_pct is not none %}{{ draft_coach.availability_pct }}%{% else %}Pending{% endif %}</span></div>
<div class="metric"><span class="metric-label">Value at Risk</span><span class="metric-value">{{ draft_coach.value_at_risk }}</span></div>
</div>
<strong>Coach rationale:</strong><ul>{% for reason in draft_coach.reasons %}<li>{{ reason }}</li>{% endfor %}</ul>
{% if draft_coach.next_pick %}<p class="muted">Next pick: {{ draft_coach.next_pick }} · Selections before then: {{ draft_coach.picks_until_next }}</p>{% endif %}
</div>
{% else %}<p class="muted">No recommendation is currently available.</p>{% endif %}
<p class="muted">Confidence summarizes internal recommendation signals. It is not a calibrated probability or guarantee of fantasy performance.</p>
</section>

'''
        text = text.replace(anchor, anchor + "\n" + panel, 1)
    return text


def main():
    if not APP.exists() or not TEMPLATE.exists():
        print("Place this script in ~/fantasy-intelligence and run it there.")
        print("Expected app.py and templates/draftboard.html.")
        sys.exit(1)

    app_text = APP.read_text(encoding="utf-8")
    template_text = TEMPLATE.read_text(encoding="utf-8")
    new_app = patch_app(app_text)
    new_template = patch_template(template_text)
    compile(new_app, str(APP), "exec")

    shutil.copy2(APP, APP.with_suffix(".py.before-draft-coach"))
    shutil.copy2(
        TEMPLATE,
        TEMPLATE.with_suffix(".html.before-draft-coach"),
    )
    APP.write_text(new_app, encoding="utf-8")
    TEMPLATE.write_text(new_template, encoding="utf-8")

    print("Fantasy Intelligence Draft Coach installed successfully.")
    print("Backups created with .before-draft-coach suffixes.")


if __name__ == "__main__":
    main()
