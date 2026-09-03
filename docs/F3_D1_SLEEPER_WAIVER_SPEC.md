# F3-D.1 Sleeper Waiver Intelligence
Extends the existing Sleeper intelligence pipeline. It ranks unowned trending players with existing roster-need and league-pressure signals.

Formula: `trend_count + need_score * 25 + pressure_score * 5 + primary_need_bonus`, where `primary_need_bonus` is 50 when the candidate matches the roster's primary positional need.

Scope is add-candidate ranking only. FAAB, drops, injuries, projections, and transactions remain out of scope until their repository contracts are inspected.
