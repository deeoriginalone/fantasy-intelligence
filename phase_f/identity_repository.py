from __future__ import annotations

class PostgresIdentityRepository:
    def __init__(self, connection_factory):
        self.connection_factory=connection_factory

    def find_by_sleeper_id(self, sleeper_player_id):
        conn=self.connection_factory()
        try:
            conn.set_session(readonly=True,autocommit=False)
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT p.id, p.player_name, UPPER(p.position), p.nfl_team
                    FROM sleeper_player_map spm
                    JOIN players p
                      ON p.player_name = spm.local_player_name
                    WHERE spm.sleeper_player_id = %s
                      AND spm.matched = TRUE
                """,(str(sleeper_player_id),))
                return cur.fetchall()
        finally:
            conn.rollback()
            conn.close()
