from __future__ import annotations
from decimal import Decimal, InvalidOperation
from flask import Blueprint, flash, redirect, render_template, request, url_for
from auth import admin_required
from pickem_pg_store import connect, seed_from_schedule

pickem_inputs_bp = Blueprint('pickem_inputs', __name__)


def american_implied(odds: int) -> float:
    if odds == 0:
        raise ValueError('Moneyline cannot be zero')
    if odds > 0:
        return 100.0 / (odds + 100.0)
    return abs(odds) / (abs(odds) + 100.0)


def no_vig_home_probability(away_moneyline: int, home_moneyline: int) -> float:
    away = american_implied(away_moneyline)
    home = american_implied(home_moneyline)
    total = away + home
    if total <= 0:
        raise ValueError('Invalid moneylines')
    return home / total


def parse_pct(value: str, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{label} must be numeric')
    if number > 1:
        number /= 100.0
    if not 0 <= number <= 1:
        raise ValueError(f'{label} must be between 0 and 100')
    return number


def current_week_from_postgres() -> int:
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT state_value FROM application_state WHERE state_key='current_week'")
            row = cur.fetchone()
            if row and row[0] and row[0].get('week'):
                return int(row[0]['week'])
    finally:
        conn.close()
    return 1


def list_week_games(season: int, week: int):
    seed_from_schedule(season, week)
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute('''SELECT game_id, kickoff, away_team, home_team,
                yahoo_away_pct, yahoo_home_pct, market_home_probability,
                away_elo, home_elo, away_situation_points, home_situation_points, projected_total
                FROM yahoo_pickem_games WHERE season=%s AND week=%s ORDER BY kickoff, away_team''',
                (season, week))
            columns = [d[0] for d in cur.description]
            return [dict(zip(columns, row)) for row in cur.fetchall()]
    finally:
        conn.close()


@pickem_inputs_bp.route('/pickem/inputs', methods=['GET', 'POST'])
@admin_required
def inputs_home():
    season = request.values.get('season', 2026, type=int)
    week = request.values.get('week', type=int) or current_week_from_postgres()
    week = max(1, min(25, week))

    if request.method == 'POST':
        game_ids = request.form.getlist('game_id')
        conn = connect()
        updated = 0
        errors = []
        try:
            with conn.cursor() as cur:
                for game_id in game_ids:
                    prefix = game_id + '__'
                    away_raw = request.form.get(prefix + 'yahoo_away_pct', '').strip()
                    home_raw = request.form.get(prefix + 'yahoo_home_pct', '').strip()
                    away_ml_raw = request.form.get(prefix + 'away_moneyline', '').strip()
                    home_ml_raw = request.form.get(prefix + 'home_moneyline', '').strip()
                    total_raw = request.form.get(prefix + 'projected_total', '').strip()

                    # Completely blank rows remain incomplete and are skipped.
                    if not any((away_raw, home_raw, away_ml_raw, home_ml_raw, total_raw)):
                        continue
                    try:
                        away_pct = parse_pct(away_raw, 'Yahoo away percentage')
                        home_pct = parse_pct(home_raw, 'Yahoo home percentage')
                        if abs((away_pct + home_pct) - 1.0) > 0.02:
                            raise ValueError('Yahoo percentages must total approximately 100%')
                        away_ml = int(away_ml_raw)
                        home_ml = int(home_ml_raw)
                        market_home = no_vig_home_probability(away_ml, home_ml)
                        projected_total = float(total_raw) if total_raw else None
                        cur.execute('''UPDATE yahoo_pickem_games SET
                            yahoo_away_pct=%s, yahoo_home_pct=%s,
                            market_home_probability=%s, projected_total=%s,
                            source_updated_at=NOW(), updated_at=NOW()
                            WHERE game_id=%s AND season=%s AND week=%s''',
                            (away_pct, home_pct, market_home, projected_total, game_id, season, week))
                        if cur.rowcount != 1:
                            raise ValueError('Game record was not found')
                        updated += 1
                    except Exception as exc:
                        errors.append(f'{game_id}: {exc}')
            if errors:
                conn.rollback()
            else:
                conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        if errors:
            for error in errors[:10]:
                flash(error, 'error')
        else:
            flash(f'Saved {updated} Pick’em games for Week {week}.', 'success')
            return redirect(url_for('pickem.pickem_page', season=season, week=week))

    games = list_week_games(season, week)
    return render_template('pickem_inputs.html', title='Pick’em Inputs', season=season, week=week, games=games)
