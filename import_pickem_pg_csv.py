import argparse,csv
from datetime import datetime,timezone
from pickem_pg_store import connect,migrate

def main():
    p=argparse.ArgumentParser(); p.add_argument('csv_path'); p.add_argument('--season',type=int,default=2026); p.add_argument('--week',type=int)
    a=p.parse_args(); migrate(); conn=connect(); updated=0
    try:
        with open(a.csv_path,newline='',encoding='utf-8-sig') as f, conn.cursor() as cur:
            for line,row in enumerate(csv.DictReader(f),2):
                away=row['away_team'].strip().upper(); home=row['home_team'].strip().upper()
                ap=float(row['yahoo_away_pct']); hp=float(row['yahoo_home_pct']); mp=float(row['market_home_probability'])
                if abs(ap+hp-1)>0.02: raise ValueError(f'line {line}: Yahoo percentages must total approximately 1.0')
                if not all(0<=x<=1 for x in (ap,hp,mp)): raise ValueError(f'line {line}: probabilities must be between 0 and 1')
                week=int(row.get('week') or a.week or 0); season=int(row.get('season') or a.season)
                cur.execute('''UPDATE yahoo_pickem_games SET yahoo_away_pct=%s,yahoo_home_pct=%s,
                    market_home_probability=%s,away_elo=COALESCE(%s,away_elo),home_elo=COALESCE(%s,home_elo),
                    away_situation_points=COALESCE(%s,away_situation_points),home_situation_points=COALESCE(%s,home_situation_points),
                    projected_total=COALESCE(%s,projected_total),source_updated_at=NOW(),updated_at=NOW()
                    WHERE season=%s AND week=%s AND away_team=%s AND home_team=%s''',
                    (ap,hp,mp,row.get('away_elo') or None,row.get('home_elo') or None,row.get('away_situation_points') or None,
                     row.get('home_situation_points') or None,row.get('projected_total') or None,season,week,away,home))
                if cur.rowcount!=1: raise ValueError(f'line {line}: no seeded schedule match for {away} at {home}, week {week}')
                updated+=1
        conn.commit(); print(f'updated={updated}')
    except Exception:
        conn.rollback(); raise
    finally: conn.close()
if __name__=='__main__': main()
