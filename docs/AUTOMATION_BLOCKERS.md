# Automation Blockers

## Blocker 1: Draft Projections

Current Source:
data/master_player_projections.csv

Used By:
- Draft Recommendations
- Waiver Recommendations

Automation Status:
MANUAL

Risk:
High

Replacement Options:
- FantasyPros API
- ESPN API
- Custom projection generator

Priority:
P0

---

## Blocker 2: VBD Rankings

Current Source:
data/top150_vbd.csv

Used By:
- Draft Recommendations
- Draft Readiness

Automation Status:
MANUAL

Risk:
High

Replacement Options:
- Internal VBD generation

Priority:
P0

---

## Blocker 3: NFL Schedule

Current Source:
data/nfl-2026-UTC.csv

Automation Status:
MANUAL

Replacement:
nflverse API

Priority:
P1

---

## Blocker 4: Bye Weeks

Current Source:
data/nfl-2026-bye-weeks.csv

Automation Status:
MANUAL

Replacement:
Derived from schedule

Priority:
P1

---

## Blocker 5: Injury CSV

Current Source:
data/nfl-injury-report.csv

Automation Status:
MANUAL

Replacement:
Sleeper injury feed

Priority:
P1

---

## Blocker 6: Defensive Matchups

Current Source:
data/defense-fp-against-2025.csv

Automation Status:
MANUAL

Replacement:
Generate internally from nflverse

Priority:
P2
