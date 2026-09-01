class RepositoryCallbacks:
    """Adapts existing repository functions to F3-A callback signatures."""
    def __init__(self, player_lookup, owner_lookup, roster_writer, draft_board_writer):
        self.player_lookup = player_lookup
        self.owner_lookup = owner_lookup
        self.roster_writer = roster_writer
        self.draft_board_writer = draft_board_writer

    def player_exists(self, player_id):
        return bool(self.player_lookup(player_id))

    def owner_exists(self, roster_id, owner_id):
        return bool(self.owner_lookup(roster_id, owner_id))

    def update_roster(self, event):
        return self.roster_writer(event)

    def update_draft_board(self, event):
        return self.draft_board_writer(event)
