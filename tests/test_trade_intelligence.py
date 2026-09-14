from services.trade_intelligence import build_trade_intelligence,generate_one_for_one,generate_two_for_one,trade_evidence_coverage,trade_freshness_metadata,trade_identity_lineage,trade_value
from services.trade_target_center import build_trade_target_center
from datetime import datetime, timedelta, timezone

def p(name,pos,projection,rank=100,**kw):
 row={"player":name,"position":pos,"projection":projection,"weekly_score":projection/17,"rank":rank,"tier":4,"injury_status":"Healthy","injury_multiplier":1,"is_bye":False};row.update(kw);return row

def mine():return [p("MQ","QB",300),p("MR1","RB",260),p("MR2","RB",230),p("MR3","RB",180),p("MR4","RB",150),p("MR5","RB",140),p("MW1","WR",250),p("MW2","WR",220),p("MW3","WR",190),p("MW4","WR",170),p("MT","TE",160),p("MK","K",120),p("MD","DEF",130)]

def theirs():return [p("TQ","QB",280),p("TR1","RB",240),p("TR2","RB",210),p("TW1","WR",270),p("TW2","WR",230),p("TW3","WR",180),p("TW4","WR",160),p("TT","TE",190),p("TK","K",110),p("TD","DEF",125)]

def test_value_is_deterministic_and_injury_reduces_value():
 healthy=p("A","RB",200);out=p("A","RB",200,injury_status="Out",injury_multiplier=0);assert trade_value(healthy)==trade_value(dict(healthy));assert trade_value(out)<trade_value(healthy)

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
 partner_rows=[supported(row,f"partner-{index}") for index,row in enumerate(theirs())]
 result=build_trade_intelligence(mine_rows,partner_rows,{"name":"Them"})
 center=build_trade_target_center(result)
 owner_ids={row["source_player_id"] for row in mine_rows}; partner_ids={row["source_player_id"] for row in partner_rows}
 assert result["allowed"] is True and center["ranked_opportunities"]
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
 assert injury_stale["publication_state"] == "BLOCKED" and "INJURY_DATA_STALE" in injury_stale["blockers"]
 assert matchup_stale["publication_state"] == "BLOCKED" and "MATCHUP_DATA_STALE" in matchup_stale["blockers"]
 assert projection_stale["publication_state"] == "BLOCKED" and "PROJECTION_DATA_STALE" in projection_stale["blockers"]
 assert matchup_unavailable["publication_state"] == "BLOCKED" and "MATCHUP_FRESHNESS_UNKNOWN" in matchup_unavailable["blockers"]
 assert projection_unavailable["publication_state"] == "BLOCKED" and "PROJECTION_FRESHNESS_UNKNOWN" in projection_unavailable["blockers"]
