#!/usr/bin/env python3
"""Extract shared roster slots and integrate action plans into Sleeper Intelligence."""
from datetime import datetime, timezone
from pathlib import Path

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
app = Path("app.py")
intel = Path("sleeper_intelligence.py")
routes = Path("sleeper_intelligence_routes.py")

app_text = app.read_text(encoding="utf-8")
intel_text = intel.read_text(encoding="utf-8")
routes_text = routes.read_text(encoding="utf-8")

shared_import = "from services.roster_slots import build_roster_slots\n"
if shared_import in app_text or "def build_local_roster_context(" in intel_text:
    raise SystemExit("ERROR: F3-D.4 patch appears to be already applied")

app_anchor = "from sleeper_recommendation_overlay import build_recommendation_overlay\n"
old_function = '''def build_roster_slots(roster):
    slots = {
        "QB": None,
        "RB1": None,
        "RB2": None,
        "WR1": None,
        "WR2": None,
        "TE": None,
        "FLEX": None,
    }
    bench = []

    for player in roster:
        position = player[2]

        if position == "QB" and slots["QB"] is None:
            slots["QB"] = player
        elif position == "RB" and slots["RB1"] is None:
            slots["RB1"] = player
        elif position == "RB" and slots["RB2"] is None:
            slots["RB2"] = player
        elif position == "WR" and slots["WR1"] is None:
            slots["WR1"] = player
        elif position == "WR" and slots["WR2"] is None:
            slots["WR2"] = player
        elif position == "TE" and slots["TE"] is None:
            slots["TE"] = player
        elif position in {"RB", "WR", "TE"} and slots["FLEX"] is None:
            slots["FLEX"] = player
        else:
            bench.append(player)

    return slots, bench


'''
for label, text, anchor in (
    ("app import", app_text, app_anchor),
    ("app roster function", app_text, old_function),
):
    if text.count(anchor) != 1:
        raise SystemExit(f"ERROR: Expected one {label} anchor, found {text.count(anchor)}")

app_text = app_text.replace(app_anchor, app_anchor + shared_import)
app_text = app_text.replace(old_function, "")

intel_import_anchor = "from collections import Counter, defaultdict\n"
if intel_text.count(intel_import_anchor) != 1:
    raise SystemExit("ERROR: sleeper_intelligence import anchor mismatch")
intel_text = intel_text.replace(
    intel_import_anchor,
    intel_import_anchor + "from services.roster_slots import build_roster_slots\n",
)

build_marker = "def build(cur,league_id,week,season=2026):\n"
if intel_text.count(build_marker) != 1:
    raise SystemExit("ERROR: sleeper_intelligence build marker mismatch")
context_function = '''def build_local_roster_context(roster):
    """Build bench, counts, and need scores from authoritative local roster rows."""
    rows=list(roster or [])
    slots,bench=build_roster_slots(rows)
    counts={position:0 for position in CORE}
    for row in rows:
        if isinstance(row,(list,tuple)) and len(row)>=3:
            position=str(row[2] or "").upper()
            if position in counts: counts[position]+=1
    need_scores={}
    needs={}
    for position,target in DEPTH_TARGETS.items():
        missing=max(0,target-counts[position]);needs[position]=missing
        need_scores[position]=int((missing/target)*100) if target else 0
    primary=max(CORE,key=lambda position:(need_scores[position],STARTER_TARGETS[position]-counts[position]))
    return {"slots":slots,"bench":bench,"position_counts":counts,"need_scores":need_scores,
        "team":{"manager":"My Team","counts":counts,"needs":needs,"primary_need":primary,"players":len(rows)}}


'''
intel_text = intel_text.replace(build_marker, context_function + build_marker)

old_build_start = "def build(cur,league_id,week,season=2026):\n    users,_,_=_latest(cur,\"users\",league_id,season=season);rosters,_,_=_latest(cur,\"rosters\",league_id,season=season);players=_players(cur,league_id,season)\n"
new_build_start = "def build(cur,league_id,week,season=2026):\n    users,_,_=_latest(cur,\"users\",league_id,season=season);rosters,_,_=_latest(cur,\"rosters\",league_id,season=season);players=_players(cur,league_id,season)\n    cur.execute(\"SELECT id,player_name,position,COALESCE(slot,'') FROM my_roster WHERE player_name IS NOT NULL AND BTRIM(player_name)<>'' ORDER BY drafted_at,id\")\n    local_roster=cur.fetchall();local_context=build_local_roster_context(local_roster)\n"
if intel_text.count(old_build_start) != 1:
    raise SystemExit("ERROR: sleeper_intelligence build start anchor mismatch")
intel_text = intel_text.replace(old_build_start, new_build_start)

old_tail = '    pressure_map=pressure(active);trending_available=available_trending(trends or [],rosters or [],players);my_team=next((team for team in roster_teams if team.get("manager")=="My Team"),None)\n    return {"season":season,"week":week,"source":source,"draft_id":draft_id,"draft_status":draft.get("status"),"players_cached":bool(players),"pick_count":len(picks or []),"teams":active,"position_pressure":pressure_map,"recent_picks":recent,"position_run_counts":run_counts,"trending_available":trending_available,"waiver_candidates":waiver_candidates(trending_available,my_team,pressure_map),"transactions":dict(tx_types),"matchups":dict(games),"nfl_state":nfl_state or {}}\n'
new_tail = '    pressure_map=pressure(active);trending_available=available_trending(trends or [],rosters or [],players)\n    candidate_rows=waiver_candidates(trending_available,local_context["team"],pressure_map)\n    action_plans=build_waiver_action_plans(candidate_rows,local_context["bench"],local_context["position_counts"],local_context["need_scores"])\n    return {"season":season,"week":week,"source":source,"draft_id":draft_id,"draft_status":draft.get("status"),"players_cached":bool(players),"pick_count":len(picks or []),"teams":active,"position_pressure":pressure_map,"recent_picks":recent,"position_run_counts":run_counts,"trending_available":trending_available,"waiver_candidates":candidate_rows,"waiver_action_plans":action_plans,"local_roster_context":{"position_counts":local_context["position_counts"],"need_scores":local_context["need_scores"],"bench_count":len(local_context["bench"])},"transactions":dict(tx_types),"matchups":dict(games),"nfl_state":nfl_state or {}}\n'
if intel_text.count(old_tail) != 1:
    raise SystemExit(f"ERROR: sleeper_intelligence return anchor count={intel_text.count(old_tail)}")
intel_text = intel_text.replace(old_tail, new_tail)

old_load = "        conn=db();cur=conn.cursor();data=build(cur,league,week,season);cur.close();conn.close();return league,data\n"
new_load = '''        conn=db();cur=conn.cursor()
        try:
            data=build(cur,league,week,season)
            return league,data
        finally:
            cur.close();conn.close()
'''
if routes_text.count(old_load) != 1:
    raise SystemExit("ERROR: sleeper_intelligence_routes load anchor mismatch")
routes_text = routes_text.replace(old_load, new_load)

for path, original in ((app, app.read_text()), (intel, intel.read_text()), (routes, routes.read_text())):
    Path(f"{path}.before_f3d4_{stamp}").write_text(original, encoding="utf-8")
app.write_text(app_text, encoding="utf-8")
intel.write_text(intel_text, encoding="utf-8")
routes.write_text(routes_text, encoding="utf-8")
print("Patched: app.py, sleeper_intelligence.py, sleeper_intelligence_routes.py")
print(f"Backups use suffix: before_f3d4_{stamp}")
