# Mock Draft Lab v1

Drop-in starter module for the Fantasy Intelligence Flask application.

## Assumptions
- PostgreSQL database: `fantasy_intelligence`
- Existing `players` table includes: id, player_name, position, nfl_team, projected_points, ranking, tier, adp
- League defaults: 12 teams, snake draft, half PPR
- Default roster: QB, 2 RB, 2 WR, TE, FLEX, K, DST, 6 bench (15 rounds)
- User-controlled team defaults to draft slot 1 and Balanced strategy

## Install
```bash
pip install -r requirements.txt
psql fantasy_intelligence < migrations/001_mock_draft_lab.sql
```

Copy `mocklab/` into the Flask project. Register the blueprint:
```python
from mocklab.routes import mocklab_bp
app.register_blueprint(mocklab_bp)
```

Set environment variable if needed:
```bash
export DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost/fantasy_intelligence
```

Open: `http://192.168.0.85:5050/mocklab`

## Smoke test
```bash
python -m mocklab.simulator --runs 10 --slot 1 --strategy balanced
```

## Important
The simulator reads team count dynamically from `league_info.team_count`, falling back to 12. If the league returns to 10 teams, update that one field. It does not hard-code 12-team logic.

## Mock Draft Lab v1.5

### Added

- ESPN 2026 Full PPR Rankings
- FantasyPros Consensus ADP
- ESPN Injury Integration
- VBD (Value Based Draft)
- Top 200 Draft Board
- Top 150 Draft Board
- Sleepers Report
- Injury Value Report

### Recommended Strategy

WR Heavy

### Latest Validation

WR Heavy 75.27
Balanced 75.23
Zero RB 75.21
QB Early 75.21
Hero RB 75.12