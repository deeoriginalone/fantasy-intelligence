from __future__ import annotations

def _norm(v): return " ".join(str(v or "").lower().split())
def _row(rows,name):
 target=_norm(name)
 return next((r for r in (rows or []) if _norm(r.get("name"))==target),None)
def fuse_sleeper_context(coach,signals,overlay,survival):
 if not isinstance(coach,dict): return coach
 out=dict(coach); reasons=list(out.get("reasons") or []); name=str(out.get("player") or ""); pos=str(out.get("position") or "").upper()
 if isinstance(out.get("player"),(list,tuple)):
  p=out["player"];name=str(p[1]) if len(p)>1 else name;pos=str(p[2]).upper() if len(p)>2 else pos
 sr=_row((survival or {}).get("rows"),name);ors=_row((overlay or {}).get("rows"),name);sig=signals or {};risk=int((sig.get("position_risk_pct") or {}).get(pos,0) or 0);pressure=int((sig.get("position_pressure") or {}).get(pos,0) or 0);before=sig.get("teams_before_next") or [];interested=sum(1 for t in before if str(t.get("primary_need") or "").upper()==pos);picks=sig.get("picks_until_next")
 add=[]
 if risk:add.append(f"Live Sleeper pressure for {pos} is {risk}% relative to the other core positions.")
 if pressure and picks is not None:add.append(f"{pos} need pressure is {pressure} across the {picks} selection(s) before the next turn.")
 if interested:add.append(f"{interested} intervening manager(s) currently project {pos} as the primary roster need.")
 if sr:add.append(f"Next-pick survival estimate for {name} is {float(sr.get('survival_pct') or 0):.1f}% ({sr.get('decision') or ''}).")
 if ors and float(ors.get("sleeper_bonus") or 0):add.append(f"The advisory Sleeper overlay adds {float(ors.get('sleeper_bonus')):.1f} points without changing the canonical Draft Coach score.")
 seen={_norm(x) for x in reasons}
 for x in add:
  if _norm(x) not in seen:reasons.append(x);seen.add(_norm(x))
 out["reasons"]=reasons;out["sleeper_context_active"]=bool(add);out["sleeper_context"]={"position":pos,"risk_pct":risk,"pressure":pressure,"interested_teams":interested,"picks_before_next":picks,"canonical_score_unchanged":True}
 return out
