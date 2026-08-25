import csv
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5433,
    database="fantasy_intelligence",
    user="fantasy",
    password="fantasy"
)

cur = conn.cursor()

with open("imports/players.csv", newline="", encoding="utf-8") as f:

    reader = csv.DictReader(f)

    for row in reader:

        cur.execute("""
            INSERT INTO players
            (
                player_name,
                position,
                nfl_team,
                ranking
            )
            VALUES
            (%s,%s,%s,%s)
        """,
        (
            row["player_name"],
            row["position"],
            row["nfl_team"],
            row["ranking"]
        ))

conn.commit()

cur.close()
conn.close()

print("Players Imported Successfully")
