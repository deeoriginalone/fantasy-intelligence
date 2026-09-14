"""NFL Intelligence: weekly decision-support signals derived from existing/free data.

Not a sportsbook page. No wagering terminology or wager-sizing guidance is produced here.
Reuses existing contracts: pickem_pg_store.connect, survivor_intelligence freshness/agreement
helpers, market_intelligence_predictions, and the free-data ingestion pipeline already built in
batch_e_ratings.py (real historical Elo via nflverse), batch_e_injuries.py (real Sleeper injury
status), and batch_e_weather.py (real Open-Meteo forecasts) via ingestion_records.
"""
from __future__ import annotations
from datetime import datetime, timezone
from psycopg2.extras import RealDictCursor
from pickem_pg_store import connect
from survivor_intelligence import evidence_freshness_state, stability_score

MODULE_VERSION = 'nfl-intelligence-v2.0.0'


def fetch_all_games(season, week):
    """All scheduled games for the week, with prediction fields NULL when not yet ingested."""
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                '''SELECT g.game_id, g.away_team, g.home_team, g.kickoff, g.market_updated_at, g.projected_total,
                          p.model_probability, p.model_pick, p.market_home_probability,
                          p.elo_home_probability, p.situation_home_probability
                   FROM yahoo_pickem_games g
                   LEFT JOIN market_intelligence_predictions p ON p.game_id = g.game_id
                   WHERE g.season=%s AND g.week=%s ORDER BY g.kickoff''',
                (season, week),
            )
            return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def available_weeks(season):
    """Weeks already present in the repository-owned schedule table for this season."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT DISTINCT week FROM yahoo_pickem_games WHERE season=%s ORDER BY week',
                (season,),
            )
            return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()


def fetch_ingestion(source_name, season, week):
    """Reads real free-data records already written by batch_e_ratings.py / batch_e_injuries.py / batch_e_weather.py."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT payload FROM ingestion_records WHERE source_name=%s AND season=%s AND week=%s',
                (source_name, season, week),
            )
            return [dict(r[0]) for r in cur.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()


def fetch_ratings_map(season, week):
    return {r['team']: r for r in fetch_ingestion('ratings', season, week)}


def fetch_injuries_map(season, week):
    return {r['team']: r for r in fetch_ingestion('situations', season, week)}


def fetch_weather_map(season, week):
    return {r['game_id']: r for r in fetch_ingestion('weather', season, week)}


def classify_signal(win_probability, confidence_available, confidence, freshness):
    """Model output vocabulary: STRONG/MODERATE/LOW SIGNAL or INSUFFICIENT EVIDENCE. Never BET/PICK/LOCK."""
    if freshness in ('STALE', 'UNAVAILABLE'):
        return 'INSUFFICIENT EVIDENCE'
    edge = abs(win_probability - 0.5)
    if not confidence_available:
        return 'LOW SIGNAL'
    if confidence >= 0.85 and edge >= 0.15:
        return 'STRONG SIGNAL'
    if confidence >= 0.65 and edge >= 0.08:
        return 'MODERATE SIGNAL'
    return 'LOW SIGNAL'


def confidence_label(confidence_available, confidence, freshness, has_prediction=True):
    """Top Signals presentation label reusing the same confidence value. Never BET/PICK/LOCK."""
    if not has_prediction or freshness in ('STALE', 'UNAVAILABLE') or not confidence_available:
        return 'INSUFFICIENT EVIDENCE'
    if confidence >= 0.8:
        return 'HIGH CONFIDENCE'
    if confidence >= 0.6:
        return 'MEDIUM CONFIDENCE'
    return 'LOW CONFIDENCE'


def _injury_total(injury_row):
    if not injury_row:
        return None
    return round(sum(float(injury_row.get(k) or 0) for k in ('quarterback_points', 'offensive_line_points', 'defense_points')), 2)


def _weather_flag(weather_row):
    if not weather_row:
        return None
    wind = float(weather_row.get('wind_speed_10m') or 0)
    precip = float(weather_row.get('precipitation') or 0)
    if wind >= 20 or precip >= 1:
        return 'HIGH'
    if wind >= 12 or precip > 0:
        return 'MODERATE'
    return 'LOW'


def injury_impact_label(injury_total):
    """Presentation tier for the existing combined injury impact."""
    if injury_total is None:
        return 'UNAVAILABLE'
    if injury_total <= -6:
        return 'HIGH'
    if injury_total <= -2:
        return 'MEDIUM'
    return 'LOW'


def game_action(has_prediction, confidence_available, signal, freshness, injury_impact, weather_impact):
    """Manager action label derived from existing prediction, injury, and weather fields."""
    if not has_prediction or not confidence_available or freshness in ('STALE', 'UNAVAILABLE'):
        return 'INSUFFICIENT EVIDENCE'
    if injury_impact == 'HIGH' or weather_impact == 'HIGH':
        return 'HIGH RISK'
    if signal == 'STRONG SIGNAL':
        return 'STRONG SIGNAL'
    return 'WATCH CLOSELY'


def grade_label(confidence_available, confidence, freshness, has_prediction=True):
    """Manager-facing grade for a prediction's confidence. Same inputs as confidence_label, different vocabulary."""
    if not has_prediction or freshness in ('STALE', 'UNAVAILABLE') or not confidence_available:
        return 'INSUFFICIENT EVIDENCE'
    if confidence >= 0.85:
        return 'ELITE'
    if confidence >= 0.7:
        return 'STRONG'
    if confidence >= 0.55:
        return 'SOLID'
    return 'QUESTIONABLE'


def build_game(row, ratings=None, injuries=None, weather=None, now=None):
    now = now or datetime.now(timezone.utc)
    ratings = ratings or {}
    injuries = injuries or {}
    weather = weather or {}
    away, home = row['away_team'], row['home_team']
    has_prediction = row.get('model_probability') is not None and row.get('model_pick') is not None

    win_probability = float(row['model_probability']) if has_prediction else None
    win_team = row['model_pick'] if has_prediction else None
    opponent = (away if win_team == home else home) if has_prediction else None
    confidence = stability_score(row) if has_prediction else None
    confidence_available = confidence is not None
    freshness = evidence_freshness_state(row.get('market_updated_at'), now) if has_prediction else 'UNAVAILABLE'
    signal = classify_signal(win_probability, confidence_available, confidence, freshness) if has_prediction else 'INSUFFICIENT EVIDENCE'

    reason = None
    if not has_prediction:
        reason = 'No market-derived prediction has been ingested for this game yet.'
    elif freshness in ('STALE', 'UNAVAILABLE'):
        reason = 'Prediction evidence is stale or its freshness could not be verified.'
    elif not confidence_available:
        reason = 'Model agreement could not be computed (a supporting component is missing).'

    away_rating, home_rating = ratings.get(away), ratings.get(home)
    team_strength_supported = bool(away_rating and home_rating)
    elo_diff = round(home_rating['elo_rating'] - away_rating['elo_rating'], 2) if team_strength_supported else None

    away_injury, home_injury = injuries.get(away), injuries.get(home)
    injury_supported = bool(away_injury and home_injury)
    injury_total = round((_injury_total(away_injury) or 0) + (_injury_total(home_injury) or 0), 2) if injury_supported else None
    injury_impact = injury_impact_label(injury_total)

    game_weather = weather.get(row['game_id'])
    weather_supported = game_weather is not None
    weather_flag = _weather_flag(game_weather)

    risk = None
    if freshness in ('STALE', 'UNAVAILABLE') and has_prediction:
        risk = 'Prediction evidence is stale or unavailable; treat this prediction as unsupported.'
    elif not has_prediction:
        risk = 'No supported prediction exists for this game.'
    elif not confidence_available:
        risk = 'Confidence is unavailable; treat as low signal.'
    elif confidence is not None and confidence < 0.5:
        risk = 'Underlying signals disagree; this prediction carries elevated uncertainty.'

    return {
        'game_id': row['game_id'], 'away_team': away, 'home_team': home, 'kickoff': row.get('kickoff'),
        'has_prediction': has_prediction, 'win_team': win_team, 'opponent': opponent,
        'win_probability': win_probability, 'confidence_available': confidence_available, 'confidence': confidence,
        'disagreement': (1 - confidence) if confidence_available else None,
        'signal': signal, 'confidence_label': confidence_label(confidence_available, confidence, freshness, has_prediction),
        'grade': grade_label(confidence_available, confidence, freshness, has_prediction),
        'reason': reason, 'risk': risk, 'freshness': freshness,
        'market_updated_at': row.get('market_updated_at'), 'market_home_probability': row.get('market_home_probability'),
        'projected_total': row.get('projected_total'),
        'team_strength_supported': team_strength_supported, 'elo_diff': elo_diff,
        'away_elo': away_rating.get('elo_rating') if away_rating else None,
        'home_elo': home_rating.get('elo_rating') if home_rating else None,
        'injury_supported': injury_supported, 'injury_total': injury_total, 'injury_impact': injury_impact,
        'away_injury': away_injury, 'home_injury': home_injury,
        'weather_supported': weather_supported, 'weather': game_weather, 'weather_flag': weather_flag,
        'action': game_action(has_prediction, confidence_available, signal, freshness, injury_impact, weather_flag),
    }


def build_week_intelligence(season, week, now=None):
    now = now or datetime.now(timezone.utc)
    rows = fetch_all_games(season, week)
    ratings = fetch_ratings_map(season, week)
    injuries = fetch_injuries_map(season, week)
    weather = fetch_weather_map(season, week)
    games = [build_game(row, ratings, injuries, weather, now=now) for row in rows]

    predicted = [g for g in games if g['has_prediction']]
    missing_predictions = len(games) - len(predicted)
    timestamps = [g['market_updated_at'] for g in predicted if g.get('market_updated_at')]
    oldest = min(timestamps) if timestamps else None
    freshness_state = evidence_freshness_state(oldest, now)
    evidence_state = 'UNAVAILABLE' if not predicted else ('BLOCKED' if freshness_state in ('STALE', 'UNAVAILABLE') else 'AVAILABLE')

    # Top Picks uses the highest supported prediction confidence; it never hides scheduled games.
    top_signals = sorted(
        games,
        key=lambda g: (g['has_prediction'], g['confidence'] if g['confidence'] is not None else -1, g['win_probability'] if g['win_probability'] is not None else -1),
        reverse=True,
    )[:5]

    for index, g in enumerate(top_signals):
        if not g['has_prediction']:
            g['top_pick_reason'] = 'No supported prediction is available yet.'
        elif index == 0:
            g['top_pick_reason'] = 'Highest confidence available'
        elif g['confidence'] is not None and g['confidence'] >= 0.7:
            g['top_pick_reason'] = 'Strong model agreement'
        else:
            g['top_pick_reason'] = 'Best supported prediction remaining'

    # Risk ranking order: major injuries, severe weather, missing predictions, then low confidence.
    def _risk_reason(g):
        if g['injury_impact'] == 'HIGH':
            return 'Major injury uncertainty'
        if g['weather_flag'] == 'HIGH':
            return 'High weather impact'
        if not g['has_prediction']:
            return 'No supported prediction'
        if g['confidence'] is not None and g['confidence'] < 0.6:
            return 'Low confidence signal'
        return None

    def _risk_rank(g):
        if g['injury_impact'] == 'HIGH':
            return 0
        if g['weather_flag'] == 'HIGH':
            return 1
        if not g['has_prediction']:
            return 2
        if g['confidence'] is not None and g['confidence'] < 0.6:
            return 3
        return 4

    risky_games = [g for g in games if _risk_rank(g) < 4]
    high_risk = sorted(risky_games, key=_risk_rank)[:5]
    for g in high_risk:
        g['risk_reason'] = _risk_reason(g)

    # Insights: keep only entries that answer "so what?" for a manager; no raw internal metrics exposed.
    insights = {}
    if predicted:
        biggest_favorite = max(predicted, key=lambda g: g['win_probability'])
        insights['biggest_favorite'] = {'team': biggest_favorite['win_team'], 'opponent': biggest_favorite['opponent'], 'win_probability': biggest_favorite['win_probability']}
        closest_game = min(predicted, key=lambda g: abs(g['win_probability'] - 0.5))
        insights['closest_game'] = {'away_team': closest_game['away_team'], 'home_team': closest_game['home_team'], 'win_probability': closest_game['win_probability']}
    totals = [g for g in games if g.get('projected_total') is not None]
    if totals:
        highest = max(totals, key=lambda g: g['projected_total'])
        lowest = min(totals, key=lambda g: g['projected_total'])
        insights['highest_projected_scoring'] = {'away_team': highest['away_team'], 'home_team': highest['home_team'], 'projected_total': highest['projected_total']}
        insights['lowest_projected_scoring'] = {'away_team': lowest['away_team'], 'home_team': lowest['home_team'], 'projected_total': lowest['projected_total']}

    blockers = []
    if missing_predictions:
        blockers.append({'name': 'Missing predictions', 'detail': f'{missing_predictions} of {len(games)} scheduled game(s) have no supported prediction yet.', 'impact': 'Those games render INSUFFICIENT EVIDENCE and rank last in Top Signals.'})
    if not ratings:
        blockers.append({'name': 'Missing team strength ratings', 'detail': 'No real Elo ratings are loaded for this week.', 'impact': 'Matchup context is unavailable.'})
    if not injuries:
        blockers.append({'name': 'Missing injury reports', 'detail': 'No Sleeper injury data is loaded for this week.', 'impact': 'Injury context is unavailable.'})
    if not weather:
        blockers.append({'name': 'Missing weather data', 'detail': 'No Open-Meteo forecast is loaded for this week (only available within a ~16-day forecast window).', 'impact': 'Weather context is unavailable.'})
    blockers.append({'name': 'Offense/defense unit rankings', 'detail': 'No free source in this repository currently provides split offensive or defensive unit statistics (passing, rushing, scoring, or defensive rank).', 'impact': 'Those sections are intentionally absent rather than estimated.'})

    return {
        'season': season, 'week': week, 'games': games, 'top_signals': top_signals, 'high_risk': high_risk,
        'insights': insights,
        'blockers': blockers, 'freshness_state': freshness_state, 'evidence_state': evidence_state,
        'last_verified': oldest.isoformat() if oldest else None,
        'scheduled_games': len(games), 'missing_predictions': missing_predictions,
    }


def team_signal_payload(season, week):
    """Reusable structure Survivor (or any other consumer) can read without duplicating this logic.
    Not wired into Survivor in this batch; exposed for future reuse only."""
    intelligence = build_week_intelligence(season, week)
    payload = {}
    for g in intelligence['games']:
        for team, opponent in ((g['away_team'], g['home_team']), (g['home_team'], g['away_team'])):
            payload[team] = {
                'opponent': opponent, 'game_id': g['game_id'],
                'win_probability': g['win_probability'] if g['win_team'] == team else (1 - g['win_probability'] if g['win_probability'] is not None else None),
                'confidence': g['confidence'], 'team_strength_supported': g['team_strength_supported'],
                'matchup_edge': g['elo_diff'] if team == g['home_team'] else (-g['elo_diff'] if g['elo_diff'] is not None else None),
                'injury_adjustment': (g['home_injury'] if team == g['home_team'] else g['away_injury']),
            }
    return payload
