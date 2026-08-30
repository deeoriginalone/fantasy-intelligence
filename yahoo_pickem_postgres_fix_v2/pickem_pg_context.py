from yahoo_pickem import PickemGame, PickemSettings, build_week, summarize_week
from pickem_pg_store import list_complete_games, save_predictions, seed_from_schedule
MODEL_VERSION='pickem-pg-v1.0.0'

def build_pickem_context(season,week,strategy='balanced'):
    seed_from_schedule(season,week)
    rows=list_complete_games(season,week)
    fields=PickemGame.__dataclass_fields__.keys()
    games=[]
    for row in rows:
        payload={k:row[k] for k in fields if k in row}
        payload['kickoff']=str(payload.get('kickoff') or '')
        for k in ('yahoo_away_pct','yahoo_home_pct','market_home_probability','away_elo','home_elo','away_situation_points','home_situation_points','projected_total'):
            if payload.get(k) is not None: payload[k]=float(payload[k])
        games.append(PickemGame(**payload))
    recs=build_week(games,PickemSettings(strategy=strategy))
    save_predictions(recs,MODEL_VERSION,strategy)
    return {'pickem_recommendations':recs,'pickem_summary':summarize_week(recs),'pickem_strategy':strategy,
            'pickem_week':int(week),'pickem_season':int(season),'pickem_model_version':MODEL_VERSION}
