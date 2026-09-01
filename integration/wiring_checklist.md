# Wiring Checklist

## Database
- [ ] Locate repository connection factory
- [ ] Instantiate PostgresDraftEventStore
- [ ] Verify migration 007 applied

## Sleeper
- [ ] Locate services/sleeper_service.py
- [ ] Route picks through SleeperDraftIngestionService

## Draft Data
- [ ] player_exists connected
- [ ] owner_exists connected
- [ ] roster_update connected
- [ ] draft_board_update connected

## Validation
- [ ] Replay command tested
- [ ] End-to-end test added
- [ ] Full suite green
