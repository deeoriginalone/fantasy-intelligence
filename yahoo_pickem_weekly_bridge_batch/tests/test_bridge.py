import tempfile, unittest
from pathlib import Path
from pickem_store import PickemStore
from pickem_weekly_bridge import build_weekly_pickem_context

class BridgeTests(unittest.TestCase):
    def test_empty_context_is_safe(self):
        with tempfile.TemporaryDirectory() as d:
            db=str(Path(d)/"x.db")
            ctx=build_weekly_pickem_context(1,2026,"balanced",db)
            self.assertEqual(ctx["pickem_recommendations"],[])
            self.assertEqual(ctx["pickem_summary"]["expected_correct"],0.0)

if __name__ == "__main__": unittest.main()
