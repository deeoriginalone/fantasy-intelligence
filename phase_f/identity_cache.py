class IdentityCache:
    def __init__(self, mapper):
        self.mapper=mapper
        self._cache={}

    def resolve_sleeper_id(self, sleeper_player_id):
        key=str(sleeper_player_id)
        if key not in self._cache:
            self._cache[key]=self.mapper.resolve_sleeper_id(key)
        return self._cache[key]

    def clear(self):
        self._cache.clear()
