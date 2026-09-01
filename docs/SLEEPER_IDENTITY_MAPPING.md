# Sleeper Identity Mapping

Current Match Method:
normalize_player_name()

Current Mapping Table:
sleeper_player_map

Mapped Players:
476

Local Players:
521

Coverage:
91.4%

Strengths:
- Existing mapping table
- Existing sync process
- Existing normalized matching

Weaknesses:
- Stores local_player_name
- Does not store local_player_id
- No confidence score
- No ambiguity classification# Sleeper Identity Mapping

## Existing System

sync_sleeper_player_map()

## Source

services/sleeper_service.py

## Mapping Target

players.player_name

## Match Rule

normalize_player_name()

## Current Statistics

Matched: 489

Unmatched: 11736

## Risks

Name collisions

Unmatched players

No local_player_id storage

No confidence score

## F2R-B Objective

Move from:

sleeper_player_id
      ↓
player_name

To:

sleeper_player_id
      ↓
players.id
