def assert_health_metadata_rendered(html, payload):
    freshness = payload.get("freshness_state")
    if freshness:
        assert freshness in html
    blocker = payload.get("blocker")
    if blocker:
        assert blocker in html
    impact = payload.get("recommendation_impact")
    if impact:
        assert impact in html


def assert_unknown_state_rendered(html, payload=None):
    assert "Unknown Health State" in html
    if payload:
        assert_health_metadata_rendered(html, payload)


def assert_missing_payload_rendered(html, payload=None):
    assert "Team health data was not supplied by the route." in html
