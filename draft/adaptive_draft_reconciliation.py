"""Apply calibrated model weights to an already-computed decision."""
def apply_calibrated_reconciliation(draft_now_wait, calibration):
 out=dict(draft_now_wait or {});calibration=calibration or {};weights=calibration.get("weights") or {};sources=out.get("source_estimates") or {}
 values=[]
 for model,key in (("monte_carlo","monte_carlo"),("opponent","opponent_model"),("survival","sleeper_survival")):
  value=sources.get(key)
  if value is not None:values.append((float(value),float(weights.get(model,0))))
 if not values:return out
 total=sum(w for _,w in values) or 1;consensus=round(sum(v*w for v,w in values)/total,1);loss=float(out.get("expected_value_loss") or 0)
 if consensus<=35 or (loss>=25 and consensus<60):decision="DRAFT NOW"
 elif consensus>=70 and loss<5:decision="WAIT MAY BE SAFE"
 elif consensus<55 or loss>=15:decision="HIGH RISK"
 elif consensus<75 or loss>=5:decision="BALANCED"
 else:decision="WAIT MAY BE SAFE"
 risk="HIGH" if consensus<45 else ("MEDIUM" if consensus<70 else "LOW")
 out.update({"decision":decision,"risk":risk,"risk_level":risk,"risk_label":risk,"availability_pct":consensus,"availability":consensus,"chance_at_next_pick":consensus,"survival_probability":consensus,"calibration_active":bool(calibration.get("active")),"calibration_weights":weights})
 reasons=list(out.get("reasons") or [])
 reasons.append(("Adaptive calibration active" if calibration.get("active") else "Default calibration weights active")+f": Monte Carlo {weights.get('monte_carlo',0)*100:.0f}%, Opponent {weights.get('opponent',0)*100:.0f}%, Survival {weights.get('survival',0)*100:.0f}%.")
 out["reasons"]=reasons;return out
