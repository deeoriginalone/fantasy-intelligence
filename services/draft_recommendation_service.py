from dataclasses import dataclass

@dataclass(frozen=True)
class Candidate:
    player_id: str
    ranking: int | None
    player_name: str
    position: str
    nfl_team: str | None
    projected_points: float | None
    tier: int | None
    adp: float | None

    @classmethod
    def from_row(cls, row):
        if len(row) < 8:
            raise ValueError("candidate row must include canonical player ID at index 7")
        player_id = str(row[7] or "").strip()
        if not player_id:
            raise ValueError(f"candidate has no canonical player ID: {row[1]}")
        return cls(player_id, row[0], str(row[1]), str(row[2]).upper(), row[3], row[4], row[5], row[6])

@dataclass(frozen=True)
class RankedCandidate:
    candidate: Candidate
    total: float
    need: int
    tier_bonus: int
    strategy_bonus: float
    starter_bonus: int
    rank_score: float

    def as_legacy(self):
        p = self.candidate
        player = (p.ranking, p.player_name, p.position, p.nfl_team, p.projected_points, p.tier, p.adp, p.player_id)
        return {"player": player, "player_id": p.player_id, "score": {"total": self.total, "need": self.need, "tier_bonus": self.tier_bonus, "strategy_bonus": self.strategy_bonus, "starter_bonus": self.starter_bonus, "rank_score": self.rank_score}}

def eligible_pool(candidates, counts, round_num, rounds, targets):
    offensive = [p for p in candidates if p.position in ("QB", "RB", "WR", "TE")]
    if round_num <= max(1, rounds - 2):
        return offensive
    missing = [pos for pos in ("K", "DEF") if counts.get(pos, 0) < targets[pos]]
    remaining = max(1, rounds - round_num + 1)
    if missing and remaining <= len(missing):
        required = [p for p in candidates if p.position in missing]
        if required:
            return required
    return [p for p in candidates if p.position in targets] or offensive

def rank_candidates(rows, counts, strategy, round_num, rounds, targets, tier_fn, strategy_bonus_fn, limit=8):
    candidates = [Candidate.from_row(row) for row in rows]
    eligible = eligible_pool(candidates, counts, round_num, rounds, targets)
    starters = {"QB": 1, "RB": 2, "WR": 2, "TE": 1, "K": 1, "DEF": 1}
    ranked = []
    for p in eligible:
        target = targets[p.position]
        need = int(max(0, target - counts.get(p.position, 0)) / max(target, 1) * 100)
        tier = int(p.tier) if p.tier is not None else tier_fn(p.ranking)
        same = sum(1 for x in candidates if x.position == p.position and (int(x.tier) if x.tier is not None else tier_fn(x.ranking)) == tier)
        tier_bonus = 35 if same <= 2 else 15 if same <= 4 else 0
        strategy_bonus = float(strategy_bonus_fn(strategy, p.position, round_num))
        starter_bonus = 20 if counts.get(p.position, 0) < starters[p.position] else 0
        rank_score = max(0, 101 - (p.ranking or 9999))
        ranked.append(RankedCandidate(p, rank_score + need + tier_bonus + strategy_bonus + starter_bonus, need, tier_bonus, strategy_bonus, starter_bonus, rank_score))
    ranked.sort(key=lambda x: (-x.total, x.candidate.ranking or 9999, x.candidate.player_name))
    return ranked[:limit]
