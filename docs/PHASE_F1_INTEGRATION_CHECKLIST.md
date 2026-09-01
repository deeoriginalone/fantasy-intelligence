# Batch F1 Integration Checklist

## Required evidence before connecting live draft data

- [ ] Identify the exact Sleeper draft identifier source.
- [ ] Confirm the function that returns the latest draft picks.
- [ ] Confirm the canonical player identifier used by `players`, `draft_board`, and Sleeper picks.
- [ ] Confirm the active draft-session identifier and its database column type.
- [ ] Confirm whether picks are zero-based or one-based.
- [ ] Confirm snake-draft slot calculation rules from existing code.
- [ ] Confirm the exact recommendation function signature.
- [ ] Confirm how drafted players are excluded from candidates.
- [ ] Confirm how the user's roster is identified.
- [ ] Confirm whether recommendation calls write to the database.
- [ ] Confirm transaction and rollback behavior.
- [ ] Confirm stale Sleeper snapshot behavior.

## Safety gates

- [ ] Mock mode is the default.
- [ ] Live mode requires an explicit flag.
- [ ] Live mode cannot start with a missing draft ID.
- [ ] A run ID is logged for each simulation.
- [ ] Duplicate picks are idempotent or rejected.
- [ ] Unknown players are quarantined, not silently accepted.
- [ ] Recommendation failures do not corrupt draft state.
- [ ] Production writes are disabled during sandbox runs.

## Required evidence before Batch F2

Save the following command outputs to `audit/phase_f/`:

```bash
python -m pytest -q
python -m phase_f.cli --events data/phase_f_mock_draft.jsonl --rounds 2 --teams 4
```

Also export the real interfaces used for:

- Sleeper pick retrieval
- draft-board update
- roster update
- recommendation generation
- draft outcome logging

Batch F2 should connect only those verified interfaces.
