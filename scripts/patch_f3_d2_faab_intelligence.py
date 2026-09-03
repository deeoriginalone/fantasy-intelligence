#!/usr/bin/env python3
from datetime import datetime,timezone
from pathlib import Path
p=Path("sleeper_intelligence.py");t=p.read_text()
if "def estimate_faab(" in t:raise SystemExit("ERROR: already applied")
marker="def waiver_candidates(trending_available,my_team,position_pressure,limit=10):\n"
if t.count(marker)!=1:raise SystemExit(f"ERROR: waiver marker count={t.count(marker)}")
fn='''def estimate_faab(waiver_score,trend_count,primary_need_match,pressure_score,remaining_budget=None):
    """Return bounded decision-support FAAB guidance; never submits a claim."""
    score=float(waiver_score or 0)
    if score>=375: urgency,base,spread="CRITICAL",17,5
    elif score>=275: urgency,base,spread="HIGH",12,4
    elif score>=175: urgency,base,spread="MEDIUM",7,3
    elif score>=90: urgency,base,spread="LOW",3,2
    else: urgency,base,spread="WATCH",1,1
    recommended=min(25,base+(3 if primary_need_match else 0));low=max(0,recommended-spread);high=min(30,recommended+spread)
    if remaining_budget is None: budget=bid=bid_low=bid_high=None
    else:
        budget=int(remaining_budget)
        if budget<0: raise ValueError("remaining_budget must be non-negative")
        bid=round(budget*recommended/100);bid_low=round(budget*low/100);bid_high=round(budget*high/100)
    return {"urgency":urgency,"recommended_bid_pct":recommended,"bid_range_low_pct":low,"bid_range_high_pct":high,"remaining_budget":budget,"recommended_bid":bid,"bid_range_low":bid_low,"bid_range_high":bid_high,"faab_reason":f"{urgency} priority from waiver score {round(score,2)}"}

'''
t=t.replace(marker,fn+marker).replace(marker,"def waiver_candidates(trending_available,my_team,position_pressure,limit=10,remaining_budget=None):\n",1)
old='        rows.append({**item,"position":pos,"trend_count":trend,"need_score":need,"pressure_score":pressure_score,"primary_need_match":primary_match,"primary_need_bonus":primary_need_bonus,"waiver_score":trend+need*25+pressure_score*5+primary_need_bonus,"reason":"; ".join(reasons) or "Available Sleeper trending player"})\n'
new='        waiver_score=trend+need*25+pressure_score*5+primary_need_bonus\n        faab=estimate_faab(waiver_score,trend,primary_match,pressure_score,remaining_budget)\n        rows.append({**item,"position":pos,"trend_count":trend,"need_score":need,"pressure_score":pressure_score,"primary_need_match":primary_match,"primary_need_bonus":primary_need_bonus,"waiver_score":waiver_score,"reason":"; ".join(reasons) or "Available Sleeper trending player",**faab})\n'
if t.count(old)!=1:raise SystemExit(f"ERROR: row anchor count={t.count(old)}")
b=Path(f"sleeper_intelligence.py.before_f3d2_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}");b.write_text(p.read_text());p.write_text(t.replace(old,new));print(f"Patched: {p}\nBackup: {b}")
