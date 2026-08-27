from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
TEMPLATE = ROOT / "templates" / "draftboard.html"


def require(text, token, description):
    if token not in text:
        raise RuntimeError(
            f"Could not find {description}. No project files were changed."
        )


def patch_app(text):
    # Add configurable strategic roster targets near the existing Sleeper IDs.
    if "ROSTER_TARGETS = {" not in text:
        preferred = 'SLEEPER_DRAFT_ID = "1398094331272794112"\n'
        fallback = 'os.makedirs(UPLOAD_FOLDER, exist_ok=True)\n'
        targets = '''\n# Strategic final-roster targets used by the Draft Agent.\n# K and DEF remain outside this offensive recommendation model.\nROSTER_TARGETS = {\n    "QB": 2,\n    "RB": 5,\n    "WR": 5,\n    "TE": 2,\n}\n'''
        if preferred in text:
            text = text.replace(preferred, preferred + targets, 1)
        else:
            require(text, fallback, "the application configuration block")
            text = text.replace(fallback, fallback + targets, 1)

    # Count the user's roster by position after slots are constructed.
    if "    position_counts = {position: 0 for position in ROSTER_TARGETS}" not in text:
        marker = "    roster_slots, bench = build_roster_slots(roster)\n"
        require(text, marker, "roster_slots calculation")
        block = '''    roster_slots, bench = build_roster_slots(roster)\n\n    position_counts = {position: 0 for position in ROSTER_TARGETS}\n    for roster_player in roster:\n        position = roster_player[2]\n        if position in position_counts:\n            position_counts[position] += 1\n\n    roster_progress = {\n        position: {\n            "current": position_counts[position],\n            "target": target,\n            "missing": max(0, target - position_counts[position]),\n        }\n        for position, target in ROSTER_TARGETS.items()\n    }\n'''
        text = text.replace(marker, block, 1)

    # Replace the old binary need score with proportional positional need.
    old_need = '''    need_score = {}\n\n    for position in ["QB", "RB", "WR", "TE"]:\n\n        if position in needed_positions:\n            need_score[position] = 100\n        else:\n            need_score[position] = 25\n'''
    new_need = '''    need_score = {}\n\n    for position, target in ROSTER_TARGETS.items():\n        current = position_counts[position]\n        missing = max(0, target - current)\n        need_score[position] = int((missing / target) * 100) if target else 0\n'''
    if old_need in text:
        text = text.replace(old_need, new_need, 1)
    elif "missing = max(0, target - current)" not in text:
        raise RuntimeError(
            "Could not identify the current Need Score block. "
            "No project files were changed."
        )

    # Calculate tier-risk bonuses for every offensive position.
    if "    tier_bonus = {position: 0 for position in ROSTER_TARGETS}" not in text:
        marker = "    team_recommendation = next(\n"
        require(text, marker, "team_recommendation calculation")
        block = '''    tier_bonus = {position: 0 for position in ROSTER_TARGETS}\n    tier_risk_details = {}\n\n    for position in ROSTER_TARGETS:\n        leader = next(\n            (player for player in available_players if player[2] == position),\n            None,\n        )\n        if not leader:\n            continue\n\n        leader_tier = get_player_tier(leader[0])\n        remaining_in_tier = tier_counts[position][leader_tier]\n        tier_risk_details[position] = {\n            "tier": leader_tier,\n            "remaining": remaining_in_tier,\n        }\n\n        if remaining_in_tier <= 2:\n            tier_bonus[position] = 100\n        elif remaining_in_tier <= 4:\n            tier_bonus[position] = 50\n\n'''
        text = text.replace(marker, block + marker, 1)

    # Add tier bonus to the backend score.
    old_score = '''        agent_draft_score = (\n            rank_score\n            + need_score.get(recommended_position, 25)\n            + scarcity_score.get(recommended_position, 25)\n        )\n'''
    new_score = '''        agent_draft_score = (\n            rank_score\n            + need_score.get(recommended_position, 0)\n            + scarcity_score.get(recommended_position, 0)\n            + tier_bonus.get(recommended_position, 0)\n        )\n'''
    if old_score in text:
        text = text.replace(old_score, new_score, 1)
    elif "+ tier_bonus.get(recommended_position, 0)" not in text:
        raise RuntimeError(
            "Could not identify the Draft Score calculation. "
            "No project files were changed."
        )

    # Build explanations after the recommendation score is known.
    if "    recommendation_reasons = []\n" not in text:
        marker = "    recommended_tier = (\n"
        require(text, marker, "recommended_tier calculation")
        reasons = '''    recommendation_reasons = []\n\n    if team_recommendation:\n        recommended_position = team_recommendation[2]\n        target = ROSTER_TARGETS.get(recommended_position, 0)\n        current = position_counts.get(recommended_position, 0)\n\n        if need_score.get(recommended_position, 0) >= 75:\n            recommendation_reasons.append(\n                f"{recommended_position} is a major roster need "\n                f"({current} of {target} target players rostered)."\n            )\n        elif need_score.get(recommended_position, 0) >= 40:\n            recommendation_reasons.append(\n                f"{recommended_position} depth is still below target "\n                f"({current} of {target})."\n            )\n        else:\n            recommendation_reasons.append(\n                f"{recommended_position} is near the strategic roster target "\n                f"({current} of {target})."\n            )\n\n        risk = tier_risk_details.get(recommended_position)\n        if risk and tier_bonus.get(recommended_position, 0) > 0:\n            recommendation_reasons.append(\n                f"Only {risk['remaining']} Tier-{risk['tier']} "\n                f"{recommended_position} players remain."\n            )\n\n        if rank_score >= 75:\n            recommendation_reasons.append(\n                "Elite overall value remains available."\n            )\n        elif rank_score >= 40:\n            recommendation_reasons.append(\n                "The player still offers strong overall value."\n            )\n\n        if scarcity_score.get(recommended_position, 0) >= 50:\n            recommendation_reasons.append(\n                f"Available {recommended_position} depth is shrinking."\n            )\n\n'''
        text = text.replace(marker, reasons + marker, 1)

    # Pass all new values to Jinja.
    if "        roster_targets=ROSTER_TARGETS,\n" not in text:
        marker = "        tier_alert=tier_alert,\n"
        require(text, marker, "tier_alert template argument")
        args = '''        tier_alert=tier_alert,\n        roster_targets=ROSTER_TARGETS,\n        position_counts=position_counts,\n        roster_progress=roster_progress,\n        tier_bonus=tier_bonus,\n        tier_risk_details=tier_risk_details,\n        recommendation_reasons=recommendation_reasons,\n'''
        text = text.replace(marker, args, 1)

    return text


def patch_template(text):
    # Include tier risk in the score shown by the template.
    old_score = '''{% set recommendation_draft_score = recommendation_rank_score + recommendation_need + recommendation_scarcity_score %}'''
    new_score = '''{% set recommendation_tier_bonus = tier_bonus.get(recommended_position, 0) %}\n{% set recommendation_draft_score = recommendation_rank_score + recommendation_need + recommendation_scarcity_score + recommendation_tier_bonus %}'''
    if old_score in text:
        text = text.replace(old_score, new_score, 1)
    elif "recommendation_tier_bonus" not in text:
        raise RuntimeError(
            "Could not find the Draft Score variables in draftboard.html. "
            "No project files were changed."
        )

    # Add the tier-risk metric beside existing score metrics.
    if "Tier Risk Bonus" not in text:
        marker = '<div class="metric metric-total"><span class="metric-label">Draft Score</span>'
        require(text, marker, "the Draft Score metric")
        metric = '''<div class="metric"><span class="metric-label">Tier Risk Bonus</span><span class="metric-value">{{ recommendation_tier_bonus }}</span></div>\n'''
        text = text.replace(marker, metric + marker, 1)

    # Replace the generic recommendation sentence with explainable reasons.
    if "Why this pick?" not in text:
        start = '''{% if best_available and team_recommendation[1] == best_available[1] %}<p class="agent-reason">Highest-ranked available player and a fit for an open roster position.</p>{% else %}<p class="agent-reason">Best-ranked available player who fills an open roster position.</p>{% endif %}'''
        replacement = '''<div class="agent-reason"><strong>Why this pick?</strong><ul>{% for reason in recommendation_reasons %}<li>{{ reason }}</li>{% endfor %}</ul></div>'''
        if start in text:
            text = text.replace(start, replacement, 1)
        else:
            raise RuntimeError(
                "Could not find the current recommendation reason block. "
                "No project files were changed."
            )

    # Add a strategic roster-target progress panel ahead of My Team.
    if "Strategic Roster Targets" not in text:
        anchor = '<section class="card"><h2>🏆 My Team</h2>'
        require(text, anchor, "the My Team panel")
        panel = '''<section class="card">\n<h2>🎯 Strategic Roster Targets</h2>\n<div class="roster-grid">{% for position in ["QB", "RB", "WR", "TE"] %}{% set progress = roster_progress[position] %}<div class="slot"><strong>{{ position }}: {{ progress.current }} / {{ progress.target }}</strong><br>Missing: {{ progress.missing }}<br>Need score: {{ need_score[position] }}</div>{% endfor %}</div>\n<p class="muted">Targets guide offensive depth and are separate from Sleeper starting-lineup requirements.</p>\n</section>\n\n'''
        text = text.replace(anchor, panel + anchor, 1)

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

    # Compile before writing to avoid replacing a working Python file.
    compile(new_app, str(APP), "exec")

    shutil.copy2(APP, APP.with_suffix(".py.before-position-targets"))
    shutil.copy2(
        TEMPLATE,
        TEMPLATE.with_suffix(".html.before-position-targets"),
    )
    APP.write_text(new_app, encoding="utf-8")
    TEMPLATE.write_text(new_template, encoding="utf-8")

    print("Position targets and explainable recommendations installed.")
    print("Backups created with .before-position-targets suffixes.")


if __name__ == "__main__":
    main()
