"""Import normalized Yahoo Pick'em records from CSV into the installed SQLite store."""
from __future__ import annotations
import argparse, csv
from pathlib import Path
from pickem_store import PickemStore
from yahoo_pickem import PickemGame

REQUIRED = ["game_id","season","week","kickoff","away_team","home_team","yahoo_away_pct","yahoo_home_pct","market_home_probability"]
FLOATS = {"yahoo_away_pct","yahoo_home_pct","market_home_probability","away_elo","home_elo","away_situation_points","home_situation_points","projected_total"}
INTS = {"season","week"}


def parse_row(row):
    missing = [k for k in REQUIRED if row.get(k, "").strip() == ""]
    if missing: raise ValueError("missing required fields: " + ", ".join(missing))
    clean = {}
    for key, value in row.items():
        if value is None or value.strip() == "": continue
        clean[key] = int(value) if key in INTS else float(value) if key in FLOATS else value.strip()
    game = PickemGame(**clean)
    game.validate()
    return clean


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path")
    parser.add_argument("--database", default="data/fantasy_intelligence.db")
    args = parser.parse_args()
    store = PickemStore(args.database); store.migrate()
    imported = 0
    with open(args.csv_path, newline="", encoding="utf-8-sig") as handle:
        for line, row in enumerate(csv.DictReader(handle), start=2):
            try: payload = parse_row(row)
            except Exception as exc: raise SystemExit(f"line {line}: {exc}")
            store.upsert_game(payload); imported += 1
    print(f"imported={imported} database={args.database}")

if __name__ == "__main__": main()
