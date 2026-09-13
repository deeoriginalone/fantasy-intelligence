def build_draft_hq_integrity(
    *,
    draft_id,
    remote_pick_count,
    persisted_pick_count,
    applied_event_count,
    failed_event_count,
    total_players,
    drafted_player_count,
    owner_pick_count,
):
    reasons = []
    if persisted_pick_count != remote_pick_count:
        reasons.append(
            f"Sleeper has {remote_pick_count} picks but only "
            f"{persisted_pick_count} persisted picks."
        )
    if applied_event_count != remote_pick_count or failed_event_count:
        reasons.append(
            f"{failed_event_count} draft event(s) are unresolved; "
            "recommendations require all current picks to be applied."
        )
    if (
        total_players < 0
        or drafted_player_count < 0
        or drafted_player_count > total_players
    ):
        reasons.append("Drafted and available player counts are inconsistent.")
    return {
        "draft_id": draft_id,
        "remote_pick_count": remote_pick_count,
        "persisted_pick_count": persisted_pick_count,
        "applied_event_count": applied_event_count,
        "failed_event_count": failed_event_count,
        "owner_pick_count": owner_pick_count,
        "consistent": not reasons,
        "recommendations_allowed": not reasons,
        "reasons": reasons,
    }