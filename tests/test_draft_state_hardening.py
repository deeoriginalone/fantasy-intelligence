from draft_state_hardening import validate_identity
def test_identity_valid(): assert validate_identity('l','d',{'league_id':'l','draft_id':'d'})['valid']
def test_draft_mismatch(): assert not validate_identity('l','d',{'league_id':'l','draft_id':'x'})['valid']
def test_league_mismatch(): assert not validate_identity('l','d',{'league_id':'x','draft_id':'d'})['valid']
