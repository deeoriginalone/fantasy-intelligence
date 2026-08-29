# Draft Simulation Results

Last Updated: 2026-08-29

## League Configuration

League: Fantasy Intelligence Champions

Format:
- 10 Teams
- Full PPR
- Snake Draft

Draft Date:
- September 6, 2026
- 3:00 PM PDT

---

## Simulation Coverage

Total Simulations:

30,000

Structure:

- 10 Draft Positions
- 6 Strategies
- 500 Simulations Per Combination

Strategies Tested:

- WR Heavy
- Balanced
- BPA
- QB Early
- Zero RB
- Hero RB

---

## Overall Results

WR Heavy finished first at every draft position.

### Best Strategy By Draft Position

| Draft Position | Best Strategy | Average Grade |
|----------------|--------------|----------------|
| 1 | WR Heavy | 74.90 |
| 2 | WR Heavy | 74.92 |
| 3 | WR Heavy | 74.89 |
| 4 | WR Heavy | 74.94 |
| 5 | WR Heavy | 74.99 |
| 6 | WR Heavy | 75.02 |
| 7 | WR Heavy | 75.11 |
| 8 | WR Heavy | 75.17 |
| 9 | WR Heavy | 75.29 |
| 10 | WR Heavy | 75.29 |

---

## Margin Analysis

WR Heavy's advantage over Balanced:

| Draft Position | Margin |
|----------------|---------|
| 1 | 0.046 |
| 2 | 0.022 |
| 3 | 0.020 |
| 4 | 0.014 |
| 5 | 0.041 |
| 6 | 0.037 |
| 7 | 0.044 |
| 8 | 0.027 |
| 9 | 0.046 |
| 10 | 0.030 |

Average winning margin:

0.033

### Interpretation

The WR Heavy strategy consistently performed best, but the margin was small.

This indicates:

- WR Heavy should be used as a tiebreaker.
- Players should not be forced because of strategy.
- Best-player-available remains important.
- Value and tier cliffs can override strategy preference.

---

## Strategy Ranking

### Average Results

| Strategy | Average Grade | Average Roster Score |
|-----------|--------------|----------------------|
| WR Heavy | 74.90 | 8719.81 |
| BPA | 74.86 | 8715.97 |
| Balanced | 74.86 | 8715.97 |
| QB Early | 74.85 | 8715.51 |
| Zero RB | 74.81 | 8712.25 |
| Hero RB | 74.77 | 8708.10 |

---

## Strategic Conclusions

Primary Strategy:

WR Heavy

Secondary Strategy:

Balanced / BPA

Recommended Draft Philosophy:

- Use WR Heavy as an early-round preference.
- Do not force wide receivers over clearly superior value.
- Respect VBD, Tier Cliffs, and Expected Value analysis.
- Prioritize elite WRs when values are close.

---

## Current Draft Assistant Configuration

Strategy Bonus:

WR Heavy:

+18 points

Conditions:

- Position = WR
- Round <= 5

Purpose:

Provide a tiebreaker preference rather than a forced positional strategy.

---

## Status

Simulation program validated.

Results imported into project recommendations.

Checkpoint Tag:

draft-assistant-v2.0