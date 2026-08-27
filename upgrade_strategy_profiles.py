from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent
APP = ROOT / "app.py"
TEMPLATE = ROOT / "templates" / "draftboard.html"


def require(text, token, label):
    if token not in text:
        raise RuntimeError(f"Could not find {label}. No project files were changed.")


def patch_app(text):
    if 'app.secret_key =' not in text:
        marker = 'app = Flask(__name__)\n'
        require(text, marker, 'Flask app initialization')
        text = text.replace(
            marker,
            marker + 'app.secret_key = os.environ.get("FLASK_SECRET_KEY", "fantasy-intelligence-dev")\n',
            1,
        )

    # Session is used to persist the selected strategy in the current browser.
    old_import = 'from flask import Flask, render_template, request, redirect, url_for, jsonify\n'
    if old_import in text:
        text = text.replace(
            old_import,
            'from flask import Flask, render_template, request, redirect, url_for, jsonify, session\n',
            1,
        )
    elif ' session\n' not in text and ', session' not in text:
        simpler = 'from flask import Flask, render_template, request, redirect, url_for\n'
        require(text, simpler, 'Flask import line')
        text = text.replace(
            simpler,
            'from flask import Flask, render_template, request, redirect, url_for, session\n',
            1,
        )

    if 'STRATEGY_PROFILES = {' not in text:
        marker = 'ROSTER_TARGETS = {\n'
        require(text, marker, 'ROSTER_TARGETS configuration')
        block = '''STRATEGY_PROFILES = {
    "BEST_AVAILABLE": {
        "label": "Best Available",
        "description": "No positional bias. Let value, need, scarcity, and tiers decide.",
    },
    "HERO_RB": {
        "label": "Hero RB",
        "description": "Prioritize an elite running back early, then build wide receiver depth.",
    },
    "ZERO_RB": {
        "label": "Zero RB",
        "description": "Prioritize wide receivers and tight end early; delay running back.",
    },
    "ELITE_TE": {
        "label": "Elite TE",
        "description": "Aggressively target a premium tight end in the first four rounds.",
    },
}
DEFAULT_STRATEGY = "BEST_AVAILABLE"


def get_strategy_bonus(strategy, position, current_round):
    if strategy == "HERO_RB":
        if current_round <= 3 and position == "RB":
            return 50
        if current_round <= 3 and position == "WR":
            return 15
        return 0

    if strategy == "ZERO_RB":
        if current_round <= 5 and position == "WR":
            return 50
        if current_round <= 5 and position == "TE":
            return 25
        if current_round <= 5 and position == "RB":
            return -25
        return 0

    if strategy == "ELITE_TE":
        if current_round <= 4 and position == "TE":
            return 75
        return 0

    return 0


'''
        text = text.replace(marker, block + marker, 1)

    if 'def set_draft_strategy():' not in text:
        marker = '@app.route("/draftboard")\ndef draftboard():\n'
        require(text, marker, 'draftboard route')
        route = '''@app.route("/draftboard/strategy", methods=["POST"])
def set_draft_strategy():
    strategy = request.form.get("strategy", DEFAULT_STRATEGY)
    if strategy not in STRATEGY_PROFILES:
        strategy = DEFAULT_STRATEGY
    session["draft_strategy"] = strategy
    return redirect(url_for("draftboard"))


'''
        text = text.replace(marker, route + marker, 1)

    # Determine profile and round before candidate scoring.
    if '    active_strategy = session.get(' not in text:
        marker = '    recommendation_candidates = []\n'
        require(text, marker, 'recommendation candidate engine')
        block = '''    active_strategy = session.get("draft_strategy", DEFAULT_STRATEGY)
    if active_strategy not in STRATEGY_PROFILES:
        active_strategy = DEFAULT_STRATEGY

    completed_picks = int(pick_forecast.get("current_pick") or 0)
    league_size = 10
    try:
        draft_details = get_draft(SLEEPER_DRAFT_ID)
        league_size = int(
            (draft_details.get("settings") or {}).get("teams") or 10
        )
    except Exception:
        pass
    current_round = (completed_picks // league_size) + 1

'''
        text = text.replace(marker, block + marker, 1)

    # Add strategy to each candidate score.
    old_score = '''        player_draft_score = (
            player_rank_score
            + player_need_score
            + player_scarcity_score
            + player_tier_bonus
        )
'''
    new_score = '''        player_strategy_bonus = get_strategy_bonus(
            active_strategy,
            position,
            current_round,
        )
        player_draft_score = (
            player_rank_score
            + player_need_score
            + player_scarcity_score
            + player_tier_bonus
            + player_strategy_bonus
        )
'''
    if old_score in text:
        text = text.replace(old_score, new_score, 1)
    elif 'player_strategy_bonus = get_strategy_bonus(' not in text:
        raise RuntimeError(
            'Could not find the candidate Draft Score formula. '
            'Run the recommendation-engine upgrade first.'
        )

    if '                "strategy_bonus": player_strategy_bonus,\n' not in text:
        marker = '                "tier_bonus": player_tier_bonus,\n'
        require(text, marker, 'candidate tier bonus field')
        text = text.replace(
            marker,
            marker + '                "strategy_bonus": player_strategy_bonus,\n',
            1,
        )

    # Explain strategy impact for the winner.
    if 'strategy_bonus_for_pick = get_strategy_bonus(' not in text:
        marker = '    recommended_tier = (\n'
        require(text, marker, 'recommended tier block')
        explanation = '''    strategy_bonus_for_pick = 0
    if team_recommendation:
        strategy_bonus_for_pick = get_strategy_bonus(
            active_strategy,
            team_recommendation[2],
            current_round,
        )
        if strategy_bonus_for_pick > 0:
            recommendation_reasons.append(
                f"{STRATEGY_PROFILES[active_strategy]['label']} strategy adds "
                f"{strategy_bonus_for_pick} points for "
                f"{team_recommendation[2]} in round {current_round}."
            )
        elif strategy_bonus_for_pick < 0:
            recommendation_reasons.append(
                f"{STRATEGY_PROFILES[active_strategy]['label']} strategy applies "
                f"a {abs(strategy_bonus_for_pick)}-point early-round penalty to "
                f"{team_recommendation[2]}."
            )

'''
        text = text.replace(marker, explanation + marker, 1)

    if '        strategy_profiles=STRATEGY_PROFILES,\n' not in text:
        marker = '        top_recommendations=top_recommendations,\n'
        require(text, marker, 'top recommendations template argument')
        args = '''        strategy_profiles=STRATEGY_PROFILES,
        active_strategy=active_strategy,
        strategy_profile=STRATEGY_PROFILES[active_strategy],
        current_round=current_round,
        strategy_bonus_for_pick=strategy_bonus_for_pick,
'''
        text = text.replace(marker, marker + args, 1)

    return text


def patch_template(text):
    if 'Draft Strategy Profile' not in text:
        anchor = '<section class="card">\n<h2>🏅 Top 5 Recommendations</h2>'
        require(text, anchor, 'Top 5 Recommendations panel')
        panel = '''<section class="card">
<h2>🧭 Draft Strategy Profile</h2>
<form method="POST" action="{{ url_for('set_draft_strategy') }}">
<label for="strategy"><strong>Active strategy:</strong></label>
<select id="strategy" name="strategy" style="padding:8px;margin:0 8px;border-radius:6px">
{% for key, profile in strategy_profiles.items() %}<option value="{{ key }}"{% if key == active_strategy %} selected{% endif %}>{{ profile.label }}</option>{% endfor %}
</select>
<button class="team" type="submit">Apply Strategy</button>
</form>
<p><strong>Current round:</strong> {{ current_round }}</p>
<p class="muted">{{ strategy_profile.description }}</p>
</section>

'''
        text = text.replace(anchor, panel + anchor, 1)

    # Add Strategy column to Top 5 table.
    old_header = '<th>Tier Bonus</th><th>Draft Score</th>'
    if old_header in text:
        text = text.replace(
            old_header,
            '<th>Tier Bonus</th><th>Strategy</th><th>Draft Score</th>',
            1,
        )
    old_cells = '<td>{{ candidate.tier_bonus }}</td><td><strong>{{ candidate.draft_score }}</strong></td>'
    if old_cells in text:
        text = text.replace(
            old_cells,
            '<td>{{ candidate.tier_bonus }}</td><td>{% if candidate.strategy_bonus > 0 %}+{% endif %}{{ candidate.strategy_bonus }}</td><td><strong>{{ candidate.draft_score }}</strong></td>',
            1,
        )

    # Add strategy metric to hero card.
    if 'Strategy Bonus</span>' not in text:
        marker = '<div class="metric metric-total"><span class="metric-label">Draft Score</span>'
        require(text, marker, 'Draft Score metric')
        metric = '''<div class="metric"><span class="metric-label">Strategy Bonus</span><span class="metric-value">{% if strategy_bonus_for_pick > 0 %}+{% endif %}{{ strategy_bonus_for_pick }}</span></div>
'''
        text = text.replace(marker, metric + marker, 1)

    return text


def main():
    if not APP.exists() or not TEMPLATE.exists():
        print('Place this script in ~/fantasy-intelligence and run it there.')
        print('Expected app.py and templates/draftboard.html.')
        sys.exit(1)

    app_text = APP.read_text(encoding='utf-8')
    template_text = TEMPLATE.read_text(encoding='utf-8')
    new_app = patch_app(app_text)
    new_template = patch_template(template_text)
    compile(new_app, str(APP), 'exec')

    shutil.copy2(APP, APP.with_suffix('.py.before-strategy-profiles'))
    shutil.copy2(
        TEMPLATE,
        TEMPLATE.with_suffix('.html.before-strategy-profiles'),
    )
    APP.write_text(new_app, encoding='utf-8')
    TEMPLATE.write_text(new_template, encoding='utf-8')

    print('Draft strategy profiles installed successfully.')
    print('Backups created with .before-strategy-profiles suffixes.')


if __name__ == '__main__':
    main()
