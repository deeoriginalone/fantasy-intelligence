# Mock Draft K/DEF Upgrade

This changes future interactive/autopilot 14-round mocks only.

Targets: 2 QB, 4 RB, 4 WR, 2 TE, 1 K, 1 DEF.
K and DEF are excluded through Round 12 and required in Rounds 13-14.
Existing mocks and 30,000 research simulations remain unchanged.

## Install
```bash
cd ~/fantasy-intelligence
python -m py_compile patch_mock_k_def.py
python patch_mock_k_def.py
python -m py_compile app.py
python3 app.py
```

Create a new 10-team, 14-round, Slot #5 autopilot mock.

## Verify
```sql
SELECT draft_slot,
       COUNT(*) FILTER (WHERE position='K') AS kickers,
       COUNT(*) FILTER (WHERE position='DEF') AS defenses,
       COUNT(*) AS roster_size
FROM mock_picks
WHERE draft_id=<NEW_MOCK_ID>
GROUP BY draft_slot
ORDER BY draft_slot;
```

Expected every slot: 1 kicker, 1 defense, 14 players.

Activate the new mock in Season Sandbox to test a complete legal roster.

## Commit
```bash
git add app.py
git commit -m "Require kicker and defense in operational mock drafts"
```
