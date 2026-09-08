import csv
import re
import unicodedata
from pathlib import Path

import app


ROOT = Path(__file__).resolve().parents[1]

PROJECTION_FILE = ROOT / "data/master_player_projections.csv"
ADP_FILE = ROOT / "data/reference/FantasyPros_2026_Overall_ADP_Rankings.csv"
VBD_FILE = ROOT / "data/top150_vbd.csv"


def normalize_name(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z0-9]", "", value)


def strip_suffix(value):
    value = normalize_name(value)

    # Normal suffixes plus known imported OCR-like variants:
    # II -> ii, III -> iii, Il -> il, Ill -> ill.
    return re.sub(r"(jr|sr|ii|iii|iv|il|ill)$", "", value)


def to_float(value):
    try:
        text = str(value).strip()
        if not text or text.lower() in {"nan", "none", "null", "n/a"}:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def to_int(value):
    number = to_float(value)
    return int(number) if number is not None else None


def adp_player_name(value):
    text = str(value or "").strip()

    # Example:
    # "Jahmyr Gibbs   DET (6)" -> "Jahmyr Gibbs"
    text = re.sub(r"\s+[A-Z]{2,3}\s+\(\d+\)\s*$", "", text)

    return text.strip()


def load_projection_rows():
    rows = []

    with PROJECTION_FILE.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            name = str(row.get("Player") or "").strip()
            projection = to_float(row.get("Projected_FPTS"))
            position = str(row.get("Position") or "").strip().upper()
            team = str(row.get("Team") or "").strip().upper()

            if name and projection is not None:
                rows.append(
                    {
                        "name": name,
                        "key": strip_suffix(name),
                        "position": position,
                        "team": team,
                        "projection": projection,
                    }
                )

    return rows


def load_adp_rows():
    rows = []

    with ADP_FILE.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            name = adp_player_name(row.get("Player (Bye)"))
            adp = to_float(row.get("AVG"))

            pos_text = str(row.get("POS") or "").strip().upper()
            position = re.sub(r"\d+$", "", pos_text)

            if name and adp is not None:
                rows.append(
                    {
                        "name": name,
                        "key": strip_suffix(name),
                        "position": position,
                        "adp": adp,
                    }
                )

    return rows


def load_tier_rows():
    if not VBD_FILE.exists():
        return []

    rows = []

    with VBD_FILE.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            name = str(row.get("Player") or "").strip()
            tier_text = str(row.get("Tier") or "").strip()
            match = re.search(r"\d+", tier_text)

            if name and match:
                rows.append(
                    {
                        "name": name,
                        "key": strip_suffix(name),
                        "tier": int(match.group()),
                    }
                )

    return rows


def unique_by_key(rows):
    grouped = {}

    for row in rows:
        grouped.setdefault(row["key"], []).append(row)

    return {
        key: matches[0]
        for key, matches in grouped.items()
        if key and len(matches) == 1
    }


def main():
    projection_map = unique_by_key(load_projection_rows())
    adp_map = unique_by_key(load_adp_rows())
    tier_map = unique_by_key(load_tier_rows())

    print("SOURCE_PROJECTIONS:", len(projection_map))
    print("SOURCE_ADP:", len(adp_map))
    print("SOURCE_TIERS:", len(tier_map))

    conn = app.get_db_connection()
    cur = conn.cursor()

    updated_projection = 0
    updated_adp = 0
    updated_tier = 0
    unmatched = []

    try:
        cur.execute(
            """
            SELECT id, player_name, UPPER(position), UPPER(COALESCE(nfl_team, ''))
            FROM players
            ORDER BY ranking NULLS LAST, player_name
            """
        )

        players = cur.fetchall()

        for player_id, player_name, position, team in players:
            key = strip_suffix(player_name)

            projection_row = projection_map.get(key)
            adp_row = adp_map.get(key)
            tier_row = tier_map.get(key)

            projection = None
            adp = None
            tier = None

            if projection_row:
                position_matches = (
                    not projection_row["position"]
                    or projection_row["position"] == position
                    or {projection_row["position"], position} == {"DEF", "DST"}
                )

                team_matches = (
                    not projection_row["team"]
                    or not team
                    or projection_row["team"] == team
                )

                if position_matches and team_matches:
                    projection = projection_row["projection"]

            if adp_row:
                position_matches = (
                    not adp_row["position"]
                    or adp_row["position"] == position
                    or {adp_row["position"], position} == {"DEF", "DST"}
                )

                if position_matches:
                    adp = adp_row["adp"]

            if tier_row:
                tier = tier_row["tier"]

            if projection is not None:
                cur.execute(
                    """
                    UPDATE players
                    SET projected_points = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (projection, player_id),
                )
                updated_projection += cur.rowcount

            if adp is not None:
                cur.execute(
                    """
                    UPDATE players
                    SET adp = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (adp, player_id),
                )
                updated_adp += cur.rowcount

            if tier is not None:
                cur.execute(
                    """
                    UPDATE players
                    SET tier = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (tier, player_id),
                )
                updated_tier += cur.rowcount

            if projection is None and adp is None and tier is None:
                unmatched.append((player_name, position, team))

        conn.commit()

        print("UPDATED_PROJECTIONS:", updated_projection)
        print("UPDATED_ADP:", updated_adp)
        print("UPDATED_TIERS:", updated_tier)
        print("FULLY_UNMATCHED:", len(unmatched))

        print("\nUNMATCHED_SAMPLE:")
        for row in unmatched[:25]:
            print(row)

        cur.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(projected_points) AS projections,
                COUNT(adp) AS adp,
                COUNT(tier) AS tiers
            FROM players
            """
        )

        total, projections, adp_count, tiers = cur.fetchone()

        print("\nFINAL_COVERAGE:")
        print("TOTAL:", total)
        print("WITH_PROJECTIONS:", projections)
        print("WITH_ADP:", adp_count)
        print("WITH_TIERS:", tiers)

    except Exception:
        conn.rollback()
        raise

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
