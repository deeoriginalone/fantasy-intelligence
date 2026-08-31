from draft_operations_hardening import invariants
class C:
 def __init__(s,x):s.x=list(x)
 def execute(s,*a):s.r=s.x.pop(0)
 def fetchall(s):return s.r
def test_clean():assert invariants(C([[],[],[],[]]))['valid']
def test_bad():assert not invariants(C([[('p',['a','b'])],[],[],[]]))['valid']
