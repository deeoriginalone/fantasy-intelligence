from contextlib import closing
from services.draft_recommendation_service import rank_candidates
from .contracts import NormalizedRecommendation
ALLOWED_ID_COLUMNS = {"player_id", "sleeper_player_id", "sleeper_id", "id"}

class RepositoryDraftRecommendationAdapter:
    def __init__(self, connection_factory, player_id_column, strategy, user_slot, targets, tier_fn, strategy_bonus_fn):
        if player_id_column not in ALLOWED_ID_COLUMNS:
            raise ValueError("unreviewed player ID column")
        self.connection_factory = connection_factory
        self.id_column = player_id_column
        self.strategy = strategy
        self.user_slot = str(user_slot)
        self.targets = targets
        self.tier_fn = tier_fn
        self.strategy_bonus_fn = strategy_bonus_fn

    def recommend(self, state):
        conn = self.connection_factory()
        try:
            conn.set_session(readonly=True, autocommit=False)
            with closing(conn.cursor()) as cur:
                cur.execute(f"SELECT ranking,player_name,UPPER(position),nfl_team,projected_points,tier,adp,{self.id_column} FROM players WHERE UPPER(position) IN ('QB','RB','WR','TE','K','DEF')")
                rows = [r for r in cur.fetchall() if str(r[7]) not in state.drafted_player_ids]
                counts = {p: 0 for p in self.targets}
                roster_ids = state.roster_player_ids.get(self.user_slot, [])
                if roster_ids:
                    cur.execute(f"SELECT UPPER(position),COUNT(*) FROM players WHERE {self.id_column}=ANY(%s) GROUP BY UPPER(position)", (roster_ids,))
                    for pos, count in cur.fetchall():
                        if pos in counts:
                            counts[pos] = count
                round_num = ((state.next_pick_no - 1) // state.teams) + 1
                ranked = rank_candidates(rows, counts, self.strategy, round_num, state.rounds, self.targets, self.tier_fn, self.strategy_bonus_fn, 1)
                if not ranked:
                    return None
                top = ranked[0]
                return NormalizedRecommendation(top.candidate.player_id, f"{top.candidate.position} need={top.need}, tier_bonus={top.tier_bonus}, strategy_bonus={top.strategy_bonus}", top.total, {"player_name": top.candidate.player_name, "position": top.candidate.position, "read_only": True})
        finally:
            conn.rollback()
            conn.close()
