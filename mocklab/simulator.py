from __future__ import annotations

import argparse
import os
import random
import statistics
from dataclasses import dataclass, field

import psycopg
from psycopg.rows import dict_row


# PostgreSQL runs in Docker and is published to host port 5433.
# DATABASE_URL can still override this value from the environment.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://fantasy:fantasy@127.0.0.1:5433/fantasy_intelligence",
)

POSITIONS = ("QB", "RB", "WR", "TE", "K", "DST")
DEFAULT_ROUNDS = 15
STRATEGIES = (
    "balanced",
    "hero_rb",
    "zero_rb",
    "bpa",
    "wr_heavy",
    "qb_early",
)
USER_TEAM_NAME = "DiE-HaRd-9eRs-FaN"


@dataclass
class Player:
    id: int
    name: str
    position: str
    nfl_team: str | None
    projected: float
    ranking: int
    tier: int
    adp: float


@dataclass
class Team:
    slot: int
    strategy: str
    league_size: int
    roster: list[Player] = field(default_factory=list)

    def count(self, position: str) -> int:
        return sum(player.position == position for player in self.roster)

    def need_bonus(self, player: Player, round_no: int) -> float:
        count = self.count(player.position)
        bonus = 0.0

        if player.position == "QB" and count == 0:
            bonus += 10 if round_no >= 6 else 2
        if player.position == "RB" and count < 2:
            bonus += 12
        if player.position == "WR" and count < 2:
            bonus += 12
        if player.position == "TE" and count == 0:
            bonus += 8 if round_no >= 5 else 2
        if player.position in ("K", "DST"):
            bonus += 8 if round_no >= 13 and count == 0 else -35
        if player.position == "QB" and count >= 2:
            bonus -= 25
        if player.position == "TE" and count >= 2:
            bonus -= 18
        if player.position in ("K", "DST") and count >= 1:
            bonus -= 40

        return bonus

    def strategy_bonus(self, player: Player, round_no: int) -> float:
        bonus = 0.0

        # Full PPR baseline: receivers gain value from catches.
        if player.position == "WR":
            bonus += 8
        elif player.position == "TE":
            bonus += 4

        if self.strategy == "hero_rb":
            if (
                player.position == "RB"
                and round_no <= 2
                and self.count("RB") == 0
            ):
                bonus += 25
            elif player.position == "RB" and 3 <= round_no <= 6:
                bonus -= 8

        elif self.strategy == "zero_rb":
            if player.position == "RB" and round_no <= 5:
                bonus -= 30
            elif player.position in ("WR", "TE") and round_no <= 5:
                bonus += 15

        elif self.strategy == "wr_heavy":
            if player.position == "WR" and round_no <= 5:
                bonus += 18

        elif self.strategy == "qb_early":
            if (
                player.position == "QB"
                and round_no <= 3
                and self.count("QB") == 0
            ):
                bonus += 22

        return bonus

    def score(
        self,
        player: Player,
        round_no: int,
        overall_pick: int,
        rng: random.Random,
    ) -> float:
        ranking_value = 650 - min(player.ranking, 650)
        projection_value = player.projected * 0.25
        adp_value = max(0.0, overall_pick - player.adp) * 0.35
        tier_value = max(0.0, 20 - player.tier) * 0.5
        noise = rng.gauss(0, 7)

        return (
            ranking_value
            + projection_value
            + adp_value
            + tier_value
            + self.need_bonus(player, round_no)
            + self.strategy_bonus(player, round_no)
            + noise
        )


def snake_slot(overall_pick: int, league_size: int) -> tuple[int, int]:
    round_no = (overall_pick - 1) // league_size + 1
    within_round = (overall_pick - 1) % league_size + 1

    if round_no % 2 == 1:
        slot = within_round
    else:
        slot = league_size + 1 - within_round

    return round_no, slot


def load_players(conn: psycopg.Connection) -> list[Player]:
    sql = """
        SELECT
            id,
            player_name,
            UPPER(position) AS position,
            nfl_team,
            COALESCE(projected_points, 0) AS projected,
            COALESCE(ranking, 9999) AS ranking,
            COALESCE(tier, 99) AS tier,
            COALESCE(adp, ranking, 9999) AS adp
        FROM players
        WHERE UPPER(position) = ANY(%s)
        ORDER BY
            COALESCE(ranking, 9999),
            COALESCE(adp, 9999),
            player_name
    """

    rows = conn.execute(sql, (list(POSITIONS),)).fetchall()

    return [
        Player(
            id=int(row["id"]),
            name=row["player_name"],
            position=row["position"],
            nfl_team=row["nfl_team"],
            projected=float(row["projected"]),
            ranking=int(row["ranking"]),
            tier=int(row["tier"]),
            adp=float(row["adp"]),
        )
        for row in rows
    ]


def get_league_size(conn: psycopg.Connection) -> int:
    row = conn.execute(
        """
        SELECT COALESCE(team_count, teams, 12) AS league_size
        FROM league_info
        ORDER BY id
        LIMIT 1
        """
    ).fetchone()

    if row is None:
        return 12

    size = int(row["league_size"] or 12)
    if size < 2 or size > 20:
        raise ValueError(f"Invalid league size in league_info: {size}")

    return size


def roster_score(team: Team) -> float:
    """Grade a roster without projections, using rank, tier, and Full PPR value."""
    score = 0.0

    for player in team.roster:
        score += max(0, 650 - player.ranking)

        if player.tier <= 3:
            score += 50
        elif player.tier <= 6:
            score += 25

        if player.position == "WR":
            score += 15
        elif player.position == "TE":
            score += 10

    return score


def simulate(
    conn: psycopg.Connection,
    user_slot: int = 1,
    user_strategy: str = "balanced",
    rounds: int = DEFAULT_ROUNDS,
    seed: int | None = None,
    save: bool = True,
) -> dict:
    if user_strategy not in STRATEGIES:
        raise ValueError(
            f"Unknown strategy '{user_strategy}'. Choose from: {', '.join(STRATEGIES)}"
        )

    rng = random.Random(seed)
    league_size = get_league_size(conn)

    if not 1 <= user_slot <= league_size:
        raise ValueError(f"Draft slot must be between 1 and {league_size}")

    if rounds < 1 or rounds > 30:
        raise ValueError("Rounds must be between 1 and 30")

    players = load_players(conn)
    required_players = league_size * rounds

    if len(players) < required_players:
        raise ValueError(
            f"Need at least {required_players} draftable players, but found {len(players)}"
        )

    opponent_strategies = list(STRATEGIES)
    teams = {
        slot: Team(
            slot=slot,
            strategy=(
                user_strategy
                if slot == user_slot
                else rng.choice(opponent_strategies)
            ),
            league_size=league_size,
        )
        for slot in range(1, league_size + 1)
    }

    available = {player.id: player for player in players}
    picks: list[tuple[int, int, int, Player, str, float, float]] = []

    for overall_pick in range(1, required_players + 1):
        round_no, slot = snake_slot(overall_pick, league_size)
        team = teams[slot]

        candidate_pool = list(available.values())
        candidate_sample = candidate_pool[: min(len(candidate_pool), 45)]

        scored_candidates = [
            (
                team.score(player, round_no, overall_pick, rng),
                team.strategy_bonus(player, round_no),
                player,
            )
            for player in candidate_sample
        ]

        value_score, strategy_bonus, chosen = max(
            scored_candidates,
            key=lambda item: item[0],
        )

        team.roster.append(chosen)
        available.pop(chosen.id)

        picks.append(
            (
                round_no,
                overall_pick,
                slot,
                chosen,
                team.strategy,
                value_score,
                strategy_bonus,
            )
        )

    user_score = roster_score(teams[user_slot])
    all_team_scores = [roster_score(team) for team in teams.values()]
    baseline = statistics.mean(all_team_scores)

    if baseline > 0:
        grade = 75 + ((user_score - baseline) / baseline) * 100
    else:
        grade = 75.0

    grade = max(0.0, min(100.0, grade))
    draft_id = None

    if save:
        try:
            row = conn.execute(
                """
                INSERT INTO mock_drafts
                (
                    draft_name,
                    strategy,
                    teams,
                    rounds,
                    draft_position,
                    overall_grade,
                    roster_score,
                    mode,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    f"Mock Draft - {user_strategy} - Seed {seed}",
                    user_strategy,
                    league_size,
                    rounds,
                    user_slot,
                    f"{grade:.1f}",
                    round(user_score, 2),
                    "simulation",
                    "complete",
                ),
            ).fetchone()

            draft_id = row["id"]

            insert_pick_sql = """
                INSERT INTO mock_picks
                (
                    draft_id,
                    round_num,
                    pick_no,
                    team_name,
                    player_name,
                    position,
                    draft_score,
                    draft_slot,
                    nfl_team,
                    overall_rank,
                    strategy_bonus
                )
                VALUES
                (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
            """

            with conn.cursor() as cursor:
                cursor.executemany(
                    insert_pick_sql,
                    [
                        (
                            draft_id,
                            round_no,
                            overall_pick,
                            (
                                USER_TEAM_NAME
                                if team_slot == user_slot
                                else f"AI Team {team_slot}"
                            ),
                            player.name,
                            player.position,
                            round(value_score, 2),
                            team_slot,
                            player.nfl_team,
                            player.ranking,
                            round(strategy_bonus, 2),
                        )
                        for (
                            round_no,
                            overall_pick,
                            team_slot,
                            player,
                            team_strategy,
                            value_score,
                            strategy_bonus,
                        ) in picks
                    ],
                )

            conn.commit()
        except Exception:
            conn.rollback()
            raise

    user_roster = [
        {
            "round": round_no,
            "pick": overall_pick,
            "name": player.name,
            "position": player.position,
            "nfl_team": player.nfl_team,
            "overall_rank": player.ranking,
        }
        for (
            round_no,
            overall_pick,
            team_slot,
            player,
            team_strategy,
            value_score,
            strategy_bonus,
        ) in picks
        if team_slot == user_slot
    ]

    return {
        "draft_id": draft_id,
        "league_size": league_size,
        "rounds": rounds,
        "slot": user_slot,
        "strategy": user_strategy,
        "roster_score": round(user_score, 2),
        "draft_grade": round(grade, 2),
        "roster": user_roster,
    }


def run_many(
    runs: int = 100,
    slot: int = 1,
    strategy: str = "balanced",
    rounds: int = DEFAULT_ROUNDS,
) -> dict:
    if runs < 1 or runs > 1000:
        raise ValueError("Runs must be between 1 and 1000")

    results = []

    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        for seed in range(runs):
            result = simulate(
                conn=conn,
                user_slot=slot,
                user_strategy=strategy,
                rounds=rounds,
                seed=seed,
                save=True,
            )
            results.append(result)

    grades = [result["draft_grade"] for result in results]
    roster_scores = [result["roster_score"] for result in results]

    return {
        "runs": runs,
        "strategy": strategy,
        "slot": slot,
        "rounds": rounds,
        "average_grade": round(statistics.mean(grades), 2),
        "average_roster_score": round(statistics.mean(roster_scores), 2),
        "best_grade": round(max(grades), 2),
        "worst_grade": round(min(grades), 2),
        "last_draft_id": results[-1]["draft_id"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Fantasy Intelligence mock draft simulations."
    )
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--slot", type=int, default=1)
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument(
        "--strategy",
        choices=STRATEGIES,
        default="balanced",
    )
    args = parser.parse_args()

    result = run_many(
        runs=args.runs,
        slot=args.slot,
        strategy=args.strategy,
        rounds=args.rounds,
    )
    print(result)


if __name__ == "__main__":
    main()
