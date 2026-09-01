def enrich_recommendation_snapshot(snapshot, identity):
    row=dict(snapshot)
    row["local_player_id"]=identity.local_player_id
    row["source_name"]="sleeper"
    row["source_player_id"]=identity.sleeper_player_id
    row["player_name"]=identity.player_name
    row["position"]=identity.position
    row["nfl_team"]=identity.nfl_team
    return row
