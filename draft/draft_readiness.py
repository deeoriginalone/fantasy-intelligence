"""Operational readiness checks for live Draft HQ use."""
from __future__ import annotations
from datetime import datetime, timezone
CORE_RESOURCES = ('drafts', 'draft_picks', 'users', 'players')
LIVE_THRESHOLDS = {'drafts': 120, 'draft_picks': 60, 'users': 300, 'players': 86400}
PREDRAFT_THRESHOLDS = {'drafts': 86400, 'draft_picks': 86400, 'users': 86400, 'players': 86400}

def _age(value):
    if value is None:
        return None
    now = datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0, int((now - value).total_seconds()))

def _state(age, limit):
    if age is None:
        return 'MISSING'
    if age <= limit:
        return 'LIVE'
    if age <= limit * 2:
        return 'AGING'
    return 'STALE'

def _table_exists(cur, name):
    cur.execute('SELECT to_regclass(%s)', (name,))
    row = cur.fetchone()
    return bool(row and row[0])

def _count(cur, sql, params=()):
    cur.execute(sql, params)
    row = cur.fetchone()
    return int(row[0] or 0) if row else 0

def build_reconciliation(cur, league_id, draft_id, draft_status):
    pre = str(draft_status or '').lower() in ('pre_draft', 'predraft')
    cur.execute('SELECT draft_id,league_id,authoritative,last_validated_at FROM draft_sessions WHERE authoritative=true ORDER BY updated_at DESC LIMIT 1')
    session = cur.fetchone()
    identity_errors = []
    if not session:
        identity_errors.append('No authoritative draft session')
    else:
        if str(session[0]) != str(draft_id):
            identity_errors.append('Authoritative draft ID mismatch')
        if str(session[1]) != str(league_id):
            identity_errors.append('Authoritative league ID mismatch')
    cur.execute('SELECT status,received_count,stored_count,matched_count,quarantined_count,created_at FROM draft_sync_audit WHERE draft_id=%s ORDER BY id DESC LIMIT 1', (str(draft_id),))
    sync = cur.fetchone()
    sync_errors = []
    if not sync:
        sync_errors.append('No draft sync audit')
    elif str(sync[0]).upper() != 'SUCCESS':
        sync_errors.append('Latest draft sync did not succeed')
    sleeper_count = _count(cur, 'SELECT count(*) FROM sleeper_draft_picks WHERE draft_id=%s', (str(draft_id),)) if _table_exists(cur, 'sleeper_draft_picks') else 0
    board_count = _count(cur, 'SELECT count(*) FROM draft_board WHERE drafted=true') if _table_exists(cur, 'draft_board') else 0
    roster_count = _count(cur, 'SELECT count(*) FROM league_rosters') if _table_exists(cur, 'league_rosters') else 0
    quarantine_count = _count(cur, "SELECT count(*) FROM draft_player_quarantine WHERE draft_id=%s AND status='OPEN'", (str(draft_id),)) if _table_exists(cur, 'draft_player_quarantine') else 0
    multiple = _count(cur, 'SELECT count(*) FROM (SELECT player_name FROM league_rosters GROUP BY player_name HAVING count(DISTINCT team_name)>1)x') if _table_exists(cur, 'league_rosters') else 0
    roster_not_drafted = _count(cur, 'SELECT count(*) FROM league_rosters r WHERE NOT EXISTS(SELECT 1 FROM draft_board d WHERE d.player_name=r.player_name AND d.drafted=true)') if _table_exists(cur, 'league_rosters') and _table_exists(cur, 'draft_board') else 0
    drafted_without_owner = _count(cur, 'SELECT count(*) FROM draft_board d WHERE d.drafted=true AND NOT EXISTS(SELECT 1 FROM league_rosters r WHERE r.player_name=d.player_name)') if _table_exists(cur, 'draft_board') and _table_exists(cur, 'league_rosters') else 0
    my_orphans = _count(cur, 'SELECT count(*) FROM my_roster m WHERE NOT EXISTS(SELECT 1 FROM league_rosters r WHERE r.player_name=m.player_name)') if _table_exists(cur, 'my_roster') and _table_exists(cur, 'league_rosters') else 0
    reconcile_errors = []
    if not pre:
        if sleeper_count != board_count:
            reconcile_errors.append('Sleeper pick count differs from drafted board count')
        if sleeper_count != roster_count:
            reconcile_errors.append('Sleeper pick count differs from league roster count')
    elif any((sleeper_count, board_count, roster_count)) and len({sleeper_count, board_count, roster_count}) > 1:
        reconcile_errors.append('Pre-draft local counts are inconsistent')
    invariant_errors = []
    if multiple:
        invariant_errors.append('Players have multiple owners')
    if roster_not_drafted:
        invariant_errors.append('Roster players are not marked drafted')
    if drafted_without_owner:
        invariant_errors.append('Drafted players have no owner')
    if my_orphans:
        invariant_errors.append('My roster contains orphan players')
    sections = {'identity': {'status': 'PASS' if not identity_errors else 'FAIL', 'errors': identity_errors, 'session': session}, 'sync': {'status': 'PASS' if not sync_errors else 'FAIL', 'errors': sync_errors, 'latest': sync}, 'reconciliation': {'status': 'PASS' if not reconcile_errors else 'FAIL', 'errors': reconcile_errors, 'counts': {'sleeper_picks': sleeper_count, 'draft_board': board_count, 'league_rosters': roster_count}, 'pre_draft': pre}, 'quarantine': {'status': 'PASS' if quarantine_count == 0 else 'ATTENTION', 'open_count': quarantine_count}, 'invariants': {'status': 'PASS' if not invariant_errors else 'FAIL', 'errors': invariant_errors, 'counts': {'multiple_owners': multiple, 'roster_not_drafted': roster_not_drafted, 'drafted_without_owner': drafted_without_owner, 'my_roster_orphans': my_orphans}}}
    overall = 'READY' if all((v['status'] == 'PASS' for v in sections.values())) else 'ATTENTION REQUIRED'
    return {'overall': overall, 'sections': sections}

def ensure_reconciliation_table(cur):
    cur.execute("CREATE TABLE IF NOT EXISTS draft_reconciliation_runs(\n      id bigserial primary key,draft_id varchar(50) not null,league_id varchar(50) not null,\n      draft_status varchar(25),overall_status varchar(30) not null,sleeper_pick_count integer not null,\n      board_pick_count integer not null,roster_pick_count integer not null,quarantine_count integer not null,\n      details jsonb not null default '{}'::jsonb,created_at timestamptz not null default now())")

def record_reconciliation(cur, league_id, draft_id, draft_status, result):
    import json
    c = result['sections']['reconciliation']['counts']
    q = result['sections']['quarantine']['open_count']
    cur.execute('INSERT INTO draft_reconciliation_runs(draft_id,league_id,draft_status,overall_status,\n      sleeper_pick_count,board_pick_count,roster_pick_count,quarantine_count,details)\n      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)', (str(draft_id), str(league_id), str(draft_status or ''), result['overall'], c['sleeper_picks'], c['draft_board'], c['league_rosters'], q, json.dumps(result, default=str)))

def build_draft_readiness(cur, league_id, season, signals=None, model_health=None):
    signals = signals or {}
    draft_status = str(signals.get('draft_status') or '').lower()
    thresholds = PREDRAFT_THRESHOLDS if draft_status in ('pre_draft', 'predraft') else LIVE_THRESHOLDS
    health = model_health or {}
    snapshots = {}
    deductions = []
    for resource in CORE_RESOURCES:
        key = str(signals.get('draft_id')) if resource == 'draft_picks' and signals.get('draft_id') else str(league_id)
        cur.execute('SELECT fetched_at FROM sleeper_api_snapshots WHERE resource_type=%s AND resource_key=%s AND season=%s ORDER BY fetched_at DESC LIMIT 1', (resource, key, int(season)))
        row = cur.fetchone()
        age = _age(row[0] if row else None)
        state = _state(age, thresholds[resource])
        snapshots[resource] = {'age_seconds': age, 'state': state, 'threshold_seconds': thresholds[resource]}
        if state == 'MISSING':
            deductions.append((resource, 15))
        elif state == 'STALE':
            deductions.append((resource, 10))
        elif state == 'AGING':
            deductions.append((resource, 4))
    checks = {'sleeper_available': bool(signals.get('available')), 'draft_id': bool(signals.get('draft_id')), 'next_pick': signals.get('next_pick') is not None, 'outcome_table': _table_exists(cur, 'draft_decision_outcomes'), 'calibration_engine': bool(health)}
    for key, ok in checks.items():
        if not ok:
            deductions.append((key, 12))
    score = max(0, 100 - sum((p for _, p in deductions)))
    dp = snapshots.get('draft_picks', {})
    mode = 'LIVE' if dp.get('state') == 'LIVE' else 'CACHED' if dp.get('state') in ('AGING', 'STALE') else 'UNAVAILABLE'
    status = 'READY' if score >= 85 else 'CAUTION' if score > 65 else 'NOT READY'
    reconciliation = build_reconciliation(cur, league_id, signals.get('draft_id'), draft_status) if signals.get('draft_id') else {'overall': 'ATTENTION REQUIRED', 'sections': {}}
    publication_allowed = status == 'READY' and mode == 'LIVE'
    return {'score': score, 'status': status, 'mode': mode, 'publication_allowed': publication_allowed, 'checks': checks, 'snapshots': snapshots, 'deductions': [{'check': k, 'points': p} for k, p in deductions], 'calibration_active': bool(health.get('active')), 'resolved_predictions': int(health.get('resolved') or 0), 'draft_id': signals.get('draft_id'), 'draft_status': signals.get('draft_status'), 'user_slot': signals.get('user_slot'), 'pick_count': int(signals.get('pick_count') or 0), 'next_pick': signals.get('next_pick'), 'draft_day': reconciliation, 'overall': reconciliation['overall']}

def validate_runtime(recommendations, signals, model_health):
    errors = []
    warnings = []
    if not signals.get('draft_id'):
        errors.append('Sleeper draft ID is missing')
    if signals.get('next_pick') is not None and int(signals.get('next_pick')) <= int(signals.get('pick_count') or 0):
        errors.append('Next pick is not after current pick')
    if len(recommendations or []) > 100:
        errors.append('Recommendation pool exceeds 100 candidates')
    for c in recommendations or []:
        need = float(c.get('need_score') or 0)
        scarcity = float(c.get('scarcity_score') or 0)
        if not 0 <= need <= 100:
            errors.append('Need score outside 0..100')
        if not 0 <= scarcity <= 25:
            errors.append('Scarcity score outside 0..25')
    weights = (model_health or {}).get('weights') or {}
    if weights:
        total = sum((float(v) for v in weights.values()))
        if abs(total - 1) > 0.002:
            errors.append('Model weights do not sum to 1.0')
        if any((not 0.1 <= float(v) <= 0.7 for v in weights.values())):
            errors.append('Model weight outside 10%..70%')
    if not recommendations:
        warnings.append('No recommendation candidates available')
    return {'passed': not errors, 'errors': sorted(set(errors)), 'warnings': sorted(set(warnings))}
