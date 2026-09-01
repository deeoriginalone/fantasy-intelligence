import pandas as pd
import psycopg2
import re

DB = {
    "host": "localhost",
    "port": 5433,
    "dbname": "fantasy_intelligence",
    "user": "fantasy",
    "password": "fantasy"
}

def normalize(name):
    if not name:
        return ""
    return re.sub(r'[^a-z0-9]', '', name.lower())

proj = pd.read_csv("data/master_player_projections.csv")
vbd = pd.read_csv("data/top150_vbd.csv")

proj["key"] = proj["Player"].apply(normalize)
vbd["key"] = vbd["Player"].apply(normalize)

projection_map = dict(
    zip(proj["key"], proj["Projected_FPTS"])
)

tier_map = {}

for _, row in vbd.iterrows():
    tier_text = str(row["Tier"]).strip()

    m = re.search(r'(\d+)', tier_text)

    if m:
        tier_map[row["key"]] = int(m.group(1))

conn = psycopg2.connect(**DB)
cur = conn.cursor()

cur.execute("""
    SELECT id, player_name
    FROM players
""")

players = cur.fetchall()

updated_projection = 0
updated_tier = 0

for player_id, player_name in players:

    key = normalize(player_name)

    if key in projection_map:
        cur.execute("""
            UPDATE players
            SET projected_points = %s
            WHERE id = %s
        """, (
            float(projection_map[key]),
            player_id
        ))
        updated_projection += 1

    if key in tier_map:
        cur.execute("""
            UPDATE players
            SET tier = %s
            WHERE id = %s
        """, (
            tier_map[key],
            player_id
        ))
        updated_tier += 1

conn.commit()

print("Updated projections:", updated_projection)
print("Updated tiers:", updated_tier)

cur.close()
conn.close()
