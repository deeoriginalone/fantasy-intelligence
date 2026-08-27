import csv
import psycopg2


def import_rankings(filepath):

    conn = psycopg2.connect(
        host="localhost",
        port=5433,
        database="fantasy_intelligence",
        user="fantasy",
        password="fantasy"
    )

    cur = conn.cursor()

    with open(filepath, newline="", encoding="utf-8-sig") as f:

        reader = csv.DictReader(f)
        print(reader.fieldnames)

        for row in reader:

            cur.execute("""
                INSERT INTO players
                (
                    player_name,
                    position,
                    nfl_team,
                    ranking
                )
                VALUES (%s,%s,%s,%s)
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
