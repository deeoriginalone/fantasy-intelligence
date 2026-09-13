from datetime import datetime,timedelta,timezone
from services.integrity import build_freshness_report,build_integrity_report,calculate_confidence_score,calculate_freshness
NOW=datetime(2026,9,9,12,0,tzinfo=timezone.utc)
def ts(s): return (NOW-timedelta(seconds=s)).isoformat()
def player(**kw):
    r={"player":"A","injury_status":"Healthy","weekly_score":10,"weekly_baseline":10,"opponent":"X","matchup_rank":15,"is_bye":False,"evidence_gaps":[]}; r.update(kw); return r
def fresh(): return {"roster_updated_at":ts(60),"injury_updated_at":ts(60),"matchup_updated_at":ts(60),"projection_updated_at":ts(60)}
def test_fresh(): assert calculate_freshness({"roster_updated_at":ts(60)},"roster",NOW)["status"]=="FRESH"
def test_unknown(): assert calculate_freshness({},"injury",NOW)["blocker"]=="INJURY_FRESHNESS_UNKNOWN"
def test_stale_expired():
    assert calculate_freshness({"matchup_updated_at":ts(90000)},"matchup",NOW)["status"]=="STALE"
    assert calculate_freshness({"projection_updated_at":ts(200000)},"projection",NOW)["status"]=="EXPIRED"
def test_unknown_health_low(): assert calculate_confidence_score(player(injury_status="Unknown"))["label"]=="LOW"
def test_missing_matchup_low(): assert calculate_confidence_score(player(matchup_rank=None))["label"]=="LOW"
def test_bye_high(): assert calculate_confidence_score(player(is_bye=True,opponent=None,matchup_rank=None))["label"]=="HIGH"
def test_ready(): assert build_integrity_report([player()],fresh(),NOW)["recommendation_ready"] is True
def test_unknown_freshness_blocked(): assert build_integrity_report([player()],{},NOW)["recommendation_ready"] is False
def test_domains(): assert set(build_freshness_report(fresh(),NOW)["domains"])=={"roster","injury","matchup","projection"}
