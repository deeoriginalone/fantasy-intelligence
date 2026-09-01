def recommend(state):
    """Synthetic plumbing adapter. Not a real fantasy recommendation."""
    return {
        "player_id": f"synthetic-recommendation-{state.next_pick_no}",
        "reason": "synthetic adapter used only to validate Batch F2 plumbing",
        "score": 0.0,
        "metadata": {"synthetic": True},
    }
