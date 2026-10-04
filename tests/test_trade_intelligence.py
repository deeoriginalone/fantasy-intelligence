from services.trade_intelligence import build_trade_intelligence,confidence,generate_one_for_one,generate_two_for_one,trade_evidence_coverage,trade_freshness_metadata,trade_identity_lineage,trade_value
from services.trade_target_center import build_trade_target_center
from datetime import datetime, timedelta, timezone

def p(name,pos,projection,rank=100,**kw):
 row={"player":name,"position":pos,"source_player_id":f"id-{name}","identity_state":"RESOLVED","projection":projection,"weekly_score":projection/17,"rank":rank,"tier":4,"injury_status":"Healthy","injury_multiplier":1,"is_bye":False};row.update(kw);return row

def mine():return [p("MQ","QB",300),p("MR1","RB",260),p("MR2","RB",230),p("MR3","RB",180),p("MR4","RB",150),p("MR5","RB",140),p("MW1","WR",250),p("MW2","WR",220),p("MW3","WR",190),p("MW4","WR",170),p("MT","TE",160),p("MK","K",120),p("MD","DEF",130)]

def theirs():return [p("TQ","QB",280),p("TR1","RB",240),p("TR2","RB",210),p("TW1","WR",270),p("TW2","WR",230),p("TW3","WR",180),p("TW4","WR",160),p("TT","TE",190),p("TK","K",110),p("TD","DEF",125)]

def test_value_is_deterministic_and_injury_reduces_value():
 healthy=p("A","RB",200);out=p("A","RB",200,injury_status="Out",injury_multiplier=0);assert trade_value(healthy)==trade_value(dict(healthy));assert trade_value(out)<trade_value(healthy)

def test_matchup_uncertainty_keeps_existing_confidence_penalty():
 ready=complete(p("A","RB",200))
 uncertain={**ready,"weekly_evidence":{"matchup":{"authoritative":False}}}
 assert confidence([ready])=={"score":100,"label":"HIGH"}
 assert confidence([uncertain])=={"score":85,"label":"MEDIUM"}

def test_one_for_one_packages_are_unique_and_balanced_ordered():
 rows=generate_one_for_one(mine(),theirs());assert rows;assert all(len(x["send"])==1 and len(x["receive"])==1 for x in rows);assert [x["balance_gap"] for x in rows]==sorted(x["balance_gap"] for x in rows)

def test_two_for_one_never_reuses_same_player():
 rows=generate_two_for_one(mine(),theirs())
 if not rows:
  return
 assert all(x["send"][0]["player"]!=x["send"][1]["player"] for x in rows)

def test_missing_roster_and_evidence_fail_closed():
 assert build_trade_intelligence([],theirs(),{"name":"Them"})["allowed"] is False
 result=build_trade_intelligence([{"player":"Unknown","position":"RB"}],theirs(),{"name":"Them"});assert "TRADE_EVIDENCE_INCOMPLETE" in result["blockers"]

def test_inputs_are_not_modified():
 a=mine();b=theirs();before_a=[dict(x) for x in a];before_b=[dict(x) for x in b];build_trade_intelligence(a,b,{"name":"Them"});assert a==before_a and b==before_b

def test_informational_rosters_expose_only_supplied_manager_context():
 now=datetime.now(timezone.utc).isoformat()
 owner=_timestamped_trade_player("Owner RB","RB",datetime.now(timezone.utc),opponent="KC",game_time_pacific="Sunday 1:25 PM",bye_week=8,is_bye=False,injury_status="Questionable",injury_source="Sleeper",injury_updated_at=now,matchup_rank=12,matchup_source="nflverse",matchup_retrieved_at=now)
 owner["weekly_evidence"]={"schedule":{"source":"nfl_schedule","retrieved_at":now,"freshness_state":"UNAVAILABLE","completeness_state":"COMPLETE","authoritative":False},"bye":{"source":"bye source","source_recorded_at":None,"retrieved_at":None,"imported_at":None,"freshness_state":"UNAVAILABLE","completeness_state":"INCOMPLETE","authoritative":False},"matchup":{"source":"nflverse","retrieved_at":now,"freshness_state":"UNAVAILABLE","completeness_state":"COMPLETE","authoritative":False}}
 partner=_timestamped_trade_player("Partner WR","WR",datetime.now(timezone.utc))
 result=_trade_diagnostic_result(owner,partner)
 info=result["informational_rosters"]["owner"][0]
 assert info["player_name"]=="Owner RB" and info["opponent"]=="KC" and info["game_time_pacific"]=="Sunday 1:25 PM"
 assert info["bye_week"]==8 and info["is_bye"] is False
 assert info["injury_status"]=="Questionable" and info["injury_retrieved_at"]==now
 assert info["matchup_rank"]==12 and info["matchup_source"]=="nflverse"
 assert info["bye_evidence"]["source_recorded_at"] is None and info["bye_evidence"]["retrieved_at"] is None
 assert "projection" not in info and "confidence" not in info and "score" not in info

def freshness(age=60):
 stamp=(datetime.now(timezone.utc)-timedelta(seconds=age)).isoformat()
 return {"roster_updated_at":stamp,"injury_updated_at":stamp,"matchup_updated_at":stamp,"projection_updated_at":stamp}
def complete(player):
 return {**player,"weekly_baseline":player["weekly_score"],"opponent":"KC","matchup_rank":15,"evidence_gaps":[]}

def test_trade_integrity_allows_complete_fresh_rosters():
 result=build_trade_intelligence([complete(p("A","RB",200))],[complete(p("B","WR",200))],{"name":"Them"},freshness(),)
 assert result["allowed"] is True
 assert result["integrity"]["recommendation_ready"] is True
 assert result["one_for_one"]

def test_trade_integrity_blocks_stale_unavailable_and_missing_rosters():
 mine_rows=[complete(p("A","RB",200))]; partner_rows=[complete(p("B","WR",200))]
 stale=build_trade_intelligence(mine_rows,partner_rows,{"name":"Them"},freshness(4000),)
 unavailable=build_trade_intelligence(mine_rows,partner_rows,{"name":"Them"},{},)
 missing=build_trade_intelligence(mine_rows,[],{"name":"Them"},freshness(),)
 assert stale["allowed"] is False and "ROSTER_DATA_STALE" in stale["blockers"]
 assert unavailable["allowed"] is False and "ROSTER_FRESHNESS_UNKNOWN" in unavailable["blockers"]
 assert missing["allowed"] is False and "PARTNER_ROSTER_EMPTY" in missing["blockers"]

def test_trade_freshness_metadata_requires_complete_domain_provenance():
 owner=complete(p("A","RB",200,roster_updated_at="2026-09-13T12:00:00+00:00",roster_source="Sleeper API",injury_updated_at="2026-09-13T12:00:00+00:00",injury_source="Sleeper API"))
 partner=complete(p("B","WR",200,roster_updated_at="2026-09-13T11:00:00+00:00",roster_source="Sleeper API",injury_updated_at="2026-09-13T11:00:00+00:00",injury_source="Sleeper API"))
 metadata=trade_freshness_metadata([owner],[partner])
 assert metadata["roster_updated_at"] == "2026-09-13T11:00:00+00:00"
 assert metadata["injury_source"] == "Sleeper API"
 assert metadata["matchup_updated_at"] is None
 assert metadata["projection_updated_at"] is None

def test_trade_matchup_freshness_ignores_non_applicable_kicker_and_defense_rows():
 timestamp="2026-09-13T12:00:00+00:00"
 offense=complete(p("A","RB",200,matchup_updated_at=timestamp,matchup_source="Supported matchup"))
 kicker=complete(p("K","K",120,matchup_rank=None,matchup_retrieved_at=None,matchup_source="Unavailable"))
 defense=complete(p("D","DEF",120,matchup_rank=None,matchup_retrieved_at=None,matchup_source="Unavailable"))
 metadata=trade_freshness_metadata([offense,kicker],[defense])
 assert metadata["matchup_updated_at"] == timestamp
 assert metadata["matchup_source"] == "Supported matchup"

def test_trade_population_coverage_reports_partial_source_and_identity_gaps():
 timestamp="2026-09-13T12:00:00+00:00"
 complete_row=complete(p("A","RB",200,source_player_id="1",roster_updated_at=timestamp,injury_updated_at=timestamp,matchup_retrieved_at=timestamp,matchup_rank=10,projection_retrieved_at=timestamp))
 unsupported=complete(p("K","K",120,source_player_id="2",roster_updated_at=timestamp,injury_updated_at=timestamp,matchup_rank=None,projection_retrieved_at=timestamp))
 missing_projection=complete(p("Unknown","WR",0,source_player_id="3",roster_updated_at=timestamp,injury_updated_at=timestamp,matchup_retrieved_at=timestamp,matchup_rank=10,projection_retrieved_at=None));missing_projection["projection"]=None
 coverage=trade_evidence_coverage([complete_row,unsupported],[missing_projection])
 assert coverage["matchup"] == {"applicable":2,"covered":2,"percentage":100,"missing_player_ids":[]}
 assert coverage["projection"]["percentage"] == 67
 assert coverage["projection"]["missing_player_ids"] == ["3"]

def test_trade_identity_lineage_preserves_stable_and_local_ids():
 rows=[{"player":"A","source_player_id":"sleeper-1","local_player_id":7,"normalized_name":"a","identity_match_method":"UNIQUE_NORMALIZED_NAME","identity_state":"RESOLVED"}]
 lineage=trade_identity_lineage(rows,[])
 assert lineage == [{"source_player_id":"sleeper-1","local_player_id":7,"player":"A","normalized_name":"a","identity_match_method":"UNIQUE_NORMALIZED_NAME","identity_state":"RESOLVED","projection_source":None,"projection_retrieved_at":None}]

def test_published_packages_preserve_owner_partner_identity_and_package_shapes():
 now=datetime.now(timezone.utc).isoformat()
 def supported(row, player_id):
  return complete({**row,"source_player_id":player_id,"roster_updated_at":now,"injury_updated_at":now,"matchup_updated_at":now,"matchup_source":"Controlled matchup","projection_updated_at":now,"projection_source":"Controlled projection"})
 mine_rows=[supported(row,f"owner-{index}") for index,row in enumerate(mine())]
 partner_candidates=[*theirs(),p("TT2","TE",180),p("TT3","TE",170)]
 partner_rows=[supported(row,f"partner-{index}") for index,row in enumerate(partner_candidates)]
 result=build_trade_intelligence(mine_rows,partner_rows,{"name":"Them"})
 center=build_trade_target_center(result)
 owner_ids={row["source_player_id"] for row in mine_rows}; partner_ids={row["source_player_id"] for row in partner_rows}
 assert result["allowed"] is True and center["ranked_opportunities"]
 assert center["best_package"]["roster_impact"]["need_improvement"]>0
 assert all(not row["roster_impact"]["hurts"] for row in center["ranked_opportunities"])
 assert all(max(0,row["roster_impact"]["owner"]["minimum"][position]-row["roster_impact"]["owner"]["after"][position]) <= max(0,row["roster_impact"]["owner"]["minimum"][position]-row["roster_impact"]["owner"]["before"][position]) for row in center["ranked_opportunities"] for position in row["roster_impact"]["owner"]["after"])
 for package in center["ranked_opportunities"]:
  sent={row["source_player_id"] for row in package["send"]}; received={row["source_player_id"] for row in package["receive"]}
  assert sent <= owner_ids and received <= partner_ids and not (sent & received)
  assert len(sent) == len(package["send"]) and len(received) == 1
  assert len(package["send"]) in {1,2}

def test_trade_publication_is_ready_degraded_or_blocked_by_domain_freshness():
 now=datetime.now(timezone.utc)
 def roster(name,position,ages):
  row=complete(p(name,position,200))
  for domain,age in ages.items():
   row[f"{domain}_updated_at"]=(now-timedelta(seconds=age)).isoformat()
   row[f"{domain}_source"]="Controlled source"
  row["roster_source"]="Sleeper API";row["injury_source"]="Sleeper API"
  return row
 fresh={"roster":60,"injury":60,"matchup":60,"projection":60}
 ready=build_trade_intelligence([roster("A","RB",fresh)],[roster("B","WR",fresh)],{"name":"Them"})
 aging=build_trade_intelligence([roster("A","RB",{**fresh,"roster":3000})],[roster("B","WR",fresh)],{"name":"Them"})
 matchup_aging=build_trade_intelligence([roster("A","RB",{**fresh,"matchup":70000})],[roster("B","WR",fresh)],{"name":"Them"})
 projection_aging=build_trade_intelligence([roster("A","RB",{**fresh,"projection":70000})],[roster("B","WR",fresh)],{"name":"Them"})
 injury_stale=build_trade_intelligence([roster("A","RB",{**fresh,"injury":90000})],[roster("B","WR",fresh)],{"name":"Them"})
 matchup_stale=build_trade_intelligence([roster("A","RB",{**fresh,"matchup":90000})],[roster("B","WR",fresh)],{"name":"Them"})
 projection_stale=build_trade_intelligence([roster("A","RB",{**fresh,"projection":90000})],[roster("B","WR",fresh)],{"name":"Them"})
 matchup_missing=roster("B","WR",fresh);matchup_missing.pop("matchup_updated_at")
 matchup_unavailable=build_trade_intelligence([roster("A","RB",fresh)],[matchup_missing],{"name":"Them"})
 projection_missing=roster("B","WR",fresh);projection_missing.pop("projection_updated_at")
 projection_unavailable=build_trade_intelligence([roster("A","RB",fresh)],[projection_missing],{"name":"Them"})
 assert ready["publication_state"] == "READY" and ready["allowed"] is True
 assert aging["publication_state"] == "DEGRADED" and aging["allowed"] is True
 assert matchup_aging["publication_state"] == "DEGRADED" and matchup_aging["allowed"] is True
 assert projection_aging["publication_state"] == "DEGRADED" and projection_aging["allowed"] is True
 assert injury_stale["publication_state"] == "PRELIMINARY" and "INJURY_DATA_STALE" in injury_stale["blockers"]
 assert matchup_stale["publication_state"] == "PRELIMINARY" and "MATCHUP_DATA_STALE" in matchup_stale["blockers"]
 assert projection_stale["publication_state"] == "PRELIMINARY" and "PROJECTION_DATA_STALE" in projection_stale["blockers"]
 assert matchup_unavailable["publication_state"] == "PRELIMINARY" and "MATCHUP_FRESHNESS_UNKNOWN" in matchup_unavailable["blockers"]
 assert projection_unavailable["publication_state"] == "PRELIMINARY" and "PROJECTION_FRESHNESS_UNKNOWN" in projection_unavailable["blockers"]

def _diagnostic_rows(result):
 return result["integrity"]["diagnostics"]

def _timestamped_trade_player(name,position,now,**overrides):
 stamp=now.isoformat()
 row=complete(p(name,position,200,source_player_id=f"id-{name}",projection_source="Stored projections",projection_retrieved_at=stamp,roster_updated_at=stamp,roster_source="Sleeper",injury_updated_at=stamp,injury_source="Sleeper",matchup_rank=12,matchup_source="nflverse",matchup_retrieved_at=stamp,matchup_updated_at=stamp,opponent="KC",schedule_source="nfl_schedule",bye_week=8))
 row.update(overrides)
 return row

def _trade_diagnostic_result(owner,partner):
 return build_trade_intelligence([owner],[partner],{"name":"Partner"})

def test_expired_projection_diagnostic_identifies_player_and_timestamp():
 now=datetime.now(timezone.utc)
 expired=(now-timedelta(days=4)).isoformat()
 owner=_timestamped_trade_player("Owner RB","RB",now,projection_retrieved_at=expired)
 partner=_timestamped_trade_player("Partner WR","WR",now)
 result=_trade_diagnostic_result(owner,partner)
 diagnostic=next(row for row in _diagnostic_rows(result) if row["domain"]=="PROJECTION" and row["player_name"]=="Owner RB")
 assert result["allowed"] is True and result["publication_state"]=="PRELIMINARY"
 assert diagnostic["player_id"]=="id-Owner RB"
 assert diagnostic["retrieved_at"]==expired
 assert diagnostic["freshness_state"]=="EXPIRED"
 assert diagnostic["blocker_code"]=="PROJECTION_DATA_EXPIRED"

def test_missing_projection_timestamp_reports_exact_field():
 now=datetime.now(timezone.utc)
 owner=_timestamped_trade_player("Owner RB","RB",now,projection_retrieved_at=None)
 partner=_timestamped_trade_player("Partner WR","WR",now)
 result=_trade_diagnostic_result(owner,partner)
 diagnostic=next(row for row in _diagnostic_rows(result) if row["domain"]=="PROJECTION" and row["player_name"]=="Owner RB")
 assert diagnostic["missing_field"]=="projection_retrieved_at"
 assert diagnostic["retrieved_at"] is None
 assert diagnostic["freshness_state"]=="UNKNOWN"

def test_null_projection_is_not_exposed_as_diagnostic_zero():
 now=datetime.now(timezone.utc)
 owner=_timestamped_trade_player("Owner RB","RB",now,projection=None,weekly_score=None,rank=None)
 partner=_timestamped_trade_player("Partner WR","WR",now)
 result=_trade_diagnostic_result(owner,partner)
 diagnostic=next(row for row in _diagnostic_rows(result) if row["domain"]=="TRADE_EVIDENCE" and row["player_name"]=="Owner RB")
 assert diagnostic["missing_field"]=="projection|weekly_score|rank"
 assert "projection" not in diagnostic
 assert "0" not in diagnostic.values()

def test_missing_matchup_row_reports_player_opponent_and_position():
 now=datetime.now(timezone.utc)
 owner=_timestamped_trade_player("Owner RB","RB",now,matchup_rank=None,evidence_gaps=["MATCHUP_EVIDENCE_UNAVAILABLE"])
 partner=_timestamped_trade_player("Partner WR","WR",now)
 diagnostics=_diagnostic_rows(_trade_diagnostic_result(owner,partner))
 diagnostic=next(row for row in diagnostics if row["domain"]=="MATCHUP" and row["player_name"]=="Owner RB")
 assert diagnostic["missing_field"]=="matchup_rank"
 assert "opponent='KC'" in diagnostic["failed_predicate"]
 assert "position='RB'" in diagnostic["failed_predicate"]

def test_missing_matchup_timestamp_reports_exact_row_and_domain():
 now=datetime.now(timezone.utc)
 owner=_timestamped_trade_player("Owner RB","RB",now,matchup_retrieved_at=None,matchup_updated_at=None,matchup_rank=12)
 partner=_timestamped_trade_player("Partner WR","WR",now)
 diagnostics=_diagnostic_rows(_trade_diagnostic_result(owner,partner))
 diagnostic=next(row for row in diagnostics if row["domain"]=="MATCHUP" and row["player_name"]=="Owner RB")
 assert diagnostic["missing_field"]=="matchup_retrieved_at"
 assert diagnostic["freshness_state"]=="UNKNOWN"

def test_non_applicable_kicker_and_defense_do_not_get_matchup_row_diagnostics():
 now=datetime.now(timezone.utc)
 kicker=_timestamped_trade_player("Kicker","K",now,matchup_rank=None,evidence_gaps=["MATCHUP_EVIDENCE_UNAVAILABLE"])
 defense=_timestamped_trade_player("Defense","DEF",now,matchup_rank=None,evidence_gaps=["MATCHUP_EVIDENCE_UNAVAILABLE"])
 partner=_timestamped_trade_player("Partner WR","WR",now)
 result=build_trade_intelligence([kicker,defense],[partner],{"name":"Partner"},freshness())
 diagnostics=_diagnostic_rows(result)
 assert result["allowed"] is True and result["publication_state"]=="PRELIMINARY"
 assert not any(row["domain"]=="MATCHUP" and row["player_name"] in {"Kicker","Defense"} for row in diagnostics)

def test_non_applicable_defense_does_not_get_injury_freshness_diagnostic():
 now=datetime.now(timezone.utc)
 defense=_timestamped_trade_player("Defense","DEF",now,injury_updated_at=None,evidence_gaps=["MATCHUP_EVIDENCE_UNAVAILABLE"])
 partner=_timestamped_trade_player("Partner WR","WR",now)
 result=build_trade_intelligence([defense],[partner],{"name":"Partner"},freshness())
 assert result["allowed"] is True and result["publication_state"]=="PRELIMINARY"
 assert not any(row["player_name"]=="Defense" and "injury freshness" in row["failed_predicate"] for row in _diagnostic_rows(result))

def test_schedule_and_bye_failures_have_distinct_domains():
 now=datetime.now(timezone.utc)
 owner=_timestamped_trade_player("Owner RB","RB",now,opponent=None,evidence_gaps=["SCHEDULE_NOT_LOADED_FOR_WEEK"])
 partner=_timestamped_trade_player("Partner WR","WR",now,bye_week=None,evidence_gaps=["BYE_WEEK_NOT_LOADED"])
 diagnostics=_diagnostic_rows(_trade_diagnostic_result(owner,partner))
 assert any(row["domain"]=="SCHEDULE" and row["player_name"]=="Owner RB" and row["missing_field"]=="opponent" for row in diagnostics)
 assert any(row["domain"]=="BYE" and row["player_name"]=="Partner WR" and row["missing_field"]=="bye_week" for row in diagnostics)

def test_invalid_player_and_position_report_exact_trade_predicates():
 now=datetime.now(timezone.utc)
 owner=_timestamped_trade_player(None,"INVALID",now)
 partner=_timestamped_trade_player("Partner WR","WR",now)
 diagnostics=_diagnostic_rows(_trade_diagnostic_result(owner,partner))
 player_diag=next(row for row in diagnostics if row["domain"]=="TRADE_EVIDENCE" and row["failed_predicate"]=="player must be non-empty")
 position_diag=next(row for row in diagnostics if row["domain"]=="TRADE_EVIDENCE" and row["player_name"] is None and "position must be one of" in row["failed_predicate"])
 assert player_diag["missing_field"]=="player"
 assert position_diag["missing_field"] is None

def test_diagnostics_are_deterministic_and_deduplicated():
 now=datetime.now(timezone.utc)
 owner=_timestamped_trade_player("Owner RB","RB",now,evidence_gaps=["MATCHUP_EVIDENCE_UNAVAILABLE","MATCHUP_EVIDENCE_UNAVAILABLE"],matchup_rank=None)
 partner=_timestamped_trade_player("Partner WR","WR",now)
 first=_diagnostic_rows(_trade_diagnostic_result(owner,partner))
 second=_diagnostic_rows(_trade_diagnostic_result(owner,partner))
 assert first==second
 assert len(first)==len({tuple(row.items()) for row in first})

def test_ready_trade_keeps_packages_and_has_no_blocker_diagnostics():
 now=datetime.now(timezone.utc)
 owner=_timestamped_trade_player("Owner RB","RB",now)
 partner=_timestamped_trade_player("Partner WR","WR",now)
 result=_trade_diagnostic_result(owner,partner)
 assert result["allowed"] is True
 assert result["integrity"]["diagnostics"]==[]
 assert result["one_for_one"]==generate_one_for_one([owner],[partner])

def test_diagnostics_preserve_aggregate_blocker_codes():
 now=datetime.now(timezone.utc)
 owner=_timestamped_trade_player("Owner RB","RB",now,projection_retrieved_at=(now-timedelta(days=4)).isoformat())
 partner=_timestamped_trade_player("Partner WR","WR",now)
 result=_trade_diagnostic_result(owner,partner)
 assert "PROJECTION_DATA_EXPIRED" in result["blockers"]
 assert result["integrity"]["blockers"]==["PROJECTION_DATA_EXPIRED"]

def _preliminary_player(name,position,side,index):
 now=datetime.now(timezone.utc).isoformat()
 player=_timestamped_trade_player(name,position,datetime.now(timezone.utc),source_player_id=f"{side}-{index}",identity_state="RESOLVED",opponent="KC",game_time_pacific="Sunday 1:00 PM",bye_week=8,matchup_rank=12,projection=200,projection_retrieved_at=None)
 player["weekly_evidence"]={
  "schedule":{"source":"nfl_schedule","retrieved_at":now,"freshness_state":"UNAVAILABLE","completeness_state":"COMPLETE","blocker":"SCHEDULE_FRESHNESS_THRESHOLD_UNVERIFIED","authoritative":False},
  "bye":{"source":"nflverse schedule","source_recorded_at":now,"retrieved_at":now,"freshness_state":"UNAVAILABLE","completeness_state":"COMPLETE","blocker":"BYE_FRESHNESS_THRESHOLD_UNVERIFIED","authoritative":False},
  "matchup":{"source":"nflverse","retrieved_at":None,"freshness_state":"UNAVAILABLE","completeness_state":"INCOMPLETE","blocker":"MATCHUP_SAMPLE_THRESHOLD_UNVERIFIED","authoritative":False},
  "projection":{"source":"players.projected_points","retrieved_at":None,"freshness_state":"UNAVAILABLE","completeness_state":"UNAVAILABLE","blocker":"PROJECTION_PROVIDER_AUTHORITY_UNVERIFIED","authoritative":False},
 }
 return player

def test_preliminary_mode_uses_supported_roster_context_without_authority_or_package_output():
 owner=[_preliminary_player(f"Owner RB {index}","RB","owner",index) for index in range(5)]+[_preliminary_player("Owner WR","WR","owner",5)]
 partner=[_preliminary_player("Partner RB","RB","partner",0)]+[_preliminary_player(f"Partner WR {index}","WR","partner",index+1) for index in range(5)]
 result=build_trade_intelligence(owner,partner,{"name":"Partner"})
 preliminary=result["preliminary_analysis"]
 assert result["allowed"] is True and result["publication_state"]=="PRELIMINARY"
 assert result["one_for_one"]==generate_one_for_one(owner,partner,allow_preliminary=True)
 assert result["two_for_one"]==generate_two_for_one(owner,partner,allow_preliminary=True)
 assert preliminary["state"]=="PRELIMINARY"
 assert all(preliminary["eligibility"].values())
 assert preliminary["evidence_domains"]=={"schedule":"PRELIMINARY","bye":"PRELIMINARY","matchup_signal":"PRELIMINARY","projection_source":"UNVERIFIED"}
 assert preliminary["benefits"]["owner_needs_addressable_by_partner_surplus"]==["WR"]
 assert preliminary["benefits"]["partner_needs_addressable_by_owner_surplus"]==["RB"]
 assert "confidence" not in preliminary and "score" not in preliminary and "ranking" not in preliminary

def test_preliminary_mode_blocks_missing_rosters_identity_and_contradictions():
 now=datetime.now(timezone.utc)
 owner=_preliminary_player("Owner RB","RB","owner",1)
 partner=_preliminary_player("Partner WR","WR","partner",1)
 assert build_trade_intelligence([], [partner], {"name":"Partner"})["preliminary_analysis"]["state"]=="BLOCKED"
 assert build_trade_intelligence([owner], [], {"name":"Partner"})["preliminary_analysis"]["state"]=="BLOCKED"
 unresolved={**partner,"identity_state":"UNRESOLVED"}
 assert build_trade_intelligence([owner],[unresolved],{"name":"Partner"})["preliminary_analysis"]["state"]=="BLOCKED"
 ownership_unresolved={**partner,"ownership_state":"UNRESOLVED"}
 assert build_trade_intelligence([owner],[ownership_unresolved],{"name":"Partner"})["preliminary_analysis"]["state"]=="BLOCKED"
 contradictory={**partner,"identity_state":"CONTRADICTORY","evidence_gaps":["PLAYER_IDENTITY_CONTRADICTORY"]}
 assert build_trade_intelligence([owner],[contradictory],{"name":"Partner"})["preliminary_analysis"]["state"]=="BLOCKED"

def test_preliminary_analysis_does_not_claim_opportunity_without_reciprocal_fit():
 owner=_preliminary_player("Owner RB","RB","owner",1)
 partner=_preliminary_player("Partner WR","WR","partner",1)
 preliminary=build_trade_intelligence([owner],[partner],{"name":"Partner"})["preliminary_analysis"]
 assert preliminary["state"]=="PRELIMINARY"
 assert preliminary["benefits"]["roster_fit_basis_available"] is False

def test_ready_authoritative_publication_state_and_packages_remain_unchanged():
 now=datetime.now(timezone.utc)
 owner=_timestamped_trade_player("Owner RB","RB",now,identity_state="RESOLVED")
 partner=_timestamped_trade_player("Partner WR","WR",now,identity_state="RESOLVED")
 result=build_trade_intelligence([owner],[partner],{"name":"Partner"},freshness())
 assert result["allowed"] is True and result["preliminary_analysis"]["state"]=="AUTHORITATIVE"
 assert result["one_for_one"]==generate_one_for_one([owner],[partner])
