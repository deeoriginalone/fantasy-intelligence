from services.ux_evidence import dashboard_contract,evidence,filter_available_waivers,roster_lineage
def test_dashboard_fails_closed():
 c=dashboard_contract(error="LEAGUE_INFO_UNAVAILABLE"); assert not c["ready"]; assert c["fields"]["team_name"]["state"]=="UNKNOWN"
def test_dashboard_uses_row():
 c=dashboard_contract(league_row=("League","Team",10,"PPR")); assert c["ready"]; assert c["fields"]["team_name"]["value"]=="Team"
def test_owned_waiver_removed(): assert filter_available_waivers([{"player":"A"},{"player":"B"}],["a"])==[{"player":"B"}]
def test_lineage_unknown(): assert roster_lineage([{"player":"A","position":"TE"}])[0]["health"]["state"]=="UNKNOWN"
def test_state_normalized(): assert evidence(None,state="not_applicable")["state"]=="NOT_APPLICABLE"
