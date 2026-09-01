import unittest
from datetime import datetime, timezone
from draft_events.models import DraftEvent
from draft_events.service import DraftEventProcessor
from draft_events.store import InMemoryDraftEventStore

def ev(**changes):
    data=dict(event_id='e1',league_id='l1',draft_id='d1',pick_number=1,round=1,round_pick=1,
              roster_id='r1',owner_id=None,player_id='p1',event_type='selection',
              occurred_at=datetime(2026,8,31,tzinfo=timezone.utc),source='fixture',raw_payload={'fixture':True})
    data.update(changes); return DraftEvent(**data)

class PipelineTests(unittest.TestCase):
    def setUp(self): self.s=InMemoryDraftEventStore(); self.p=DraftEventProcessor(self.s)
    def test_valid_selection(self): self.assertTrue(self.p.process(ev()).applied)
    def test_duplicate_event_is_noop(self):
        self.p.process(ev()); r=self.p.process(ev()); self.assertTrue(r.duplicate); self.assertFalse(r.applied)
    def test_duplicate_pick_number(self):
        self.p.process(ev()); self.assertEqual(self.p.process(ev(event_id='e2',player_id='p2')).status,'FAILED')
    def test_same_player_twice(self):
        self.p.process(ev()); self.assertEqual(self.p.process(ev(event_id='e2',pick_number=2,round_pick=2)).status,'FAILED')
    def test_unknown_player(self):
        p=DraftEventProcessor(self.s,player_exists=lambda _:False); self.assertEqual(p.process(ev()).message,'unknown player_id')
    def test_unknown_owner(self):
        p=DraftEventProcessor(self.s,owner_exists=lambda r,o:False); self.assertIn('unknown',p.process(ev()).message)
    def test_out_of_order_reconstructs_order(self):
        self.p.process(ev(event_id='e2',pick_number=2,round_pick=2,player_id='p2')); self.p.process(ev())
        self.assertEqual([x.pick_number for x in self.s.ordered_state('d1')],[1,2])
    def test_missing_required(self): self.assertEqual(self.p.process(ev(player_id='')).status,'FAILED')
    def test_invalid_round_pick(self): self.assertEqual(self.p.process(ev(round_pick=0)).status,'FAILED')
    def test_replay_after_partial_failure(self):
        flag={'ok':False}; p=DraftEventProcessor(self.s,player_exists=lambda _:flag['ok']); p.process(ev()); flag['ok']=True
        self.assertEqual(p.replay_failed()[0].status,'APPLIED')
    def test_atomic_rollback(self):
        p=DraftEventProcessor(self.s,roster_update=lambda e: (_ for _ in ()).throw(RuntimeError('boom')))
        self.assertEqual(p.process(ev()).status,'FAILED'); self.assertEqual(self.s.ordered_state('d1'),[])
    def test_payload_retention(self):
        self.p.process(ev()); self.assertTrue(self.s.get_event('e1')['event'].raw_payload['fixture'])
    def test_callbacks(self):
        calls=[]; p=DraftEventProcessor(self.s,roster_update=lambda e:calls.append('r'),draft_board_update=lambda e:calls.append('d'))
        p.process(ev()); self.assertEqual(calls,['r','d'])

if __name__=='__main__': unittest.main()
