from draft_readiness import build_reconciliation
class C:
 def __init__(self,one,counts):self.one=list(one);self.counts=list(counts);self.pending=None
 def execute(self,statement,*a):
  self.pending=True if 'to_regclass' in statement.lower() else None
 def fetchone(self):
  if self.pending is not None:
   pending,self.pending=self.pending,None
   return (pending,)
  if self.one:return self.one.pop(0)
  return (self.counts.pop(0),)
def test_predraft_empty_ready():
 c=C([('d','l',True,None),('SUCCESS',0,0,0,0,None)],[0,0,0,0,0,0,0,0])
 assert build_reconciliation(c,'l','d','pre_draft')['overall']=='READY'
def test_identity_mismatch_blocks():
 c=C([('x','l',True,None),('SUCCESS',0,0,0,0,None)],[0,0,0,0,0,0,0,0])
 assert build_reconciliation(c,'l','d','pre_draft')['overall']=='ATTENTION REQUIRED'
def test_live_count_mismatch_blocks():
 c=C([('d','l',True,None),('SUCCESS',1,1,1,0,None)],[1,0,1,0,0,0,0,0])
 assert build_reconciliation(c,'l','d','in_progress')['sections']['reconciliation']['status']=='FAIL'
