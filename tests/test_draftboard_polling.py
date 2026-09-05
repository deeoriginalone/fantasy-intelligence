from pathlib import Path

import app as app_module


TEMPLATE = Path(__file__).resolve().parents[1] / "templates/draftboard.html"


def _admin_client():
    client = app_module.app.test_client()
    with client.session_transaction() as session:
        session["user_role"] = "admin"
        session["csrf_token"] = "polling-test-token"
    return client


def test_polling_template_uses_authenticated_post_contract():
    source = TEMPLATE.read_text(encoding="utf-8")

    assert "const csrfToken={{ csrf_token() | tojson }};" in source
    assert 'fetch(endpoint,{method:"POST"' in source
    assert '"Accept":"application/json"' in source
    assert '"X-CSRF-Token":csrfToken' in source
    assert "refresh.addEventListener" in source
    assert "if(checking||(!enabled&&!manual))return" in source
    assert "count!==baseline" in source
    assert 'setState("error","Connection issue")' in source
    assert "ADMIN_TOKEN" not in source


def test_anonymous_polling_is_rejected():
    response = app_module.app.test_client().post(
        "/test-draft-picks",
        headers={"Accept": "application/json"},
    )

    assert response.status_code == 401


def test_authenticated_empty_poll_returns_json_array(monkeypatch):
    monkeypatch.setattr(app_module, "get_draft_picks", lambda draft_id: [])

    response = _admin_client().post(
        "/test-draft-picks",
        headers={
            "Accept": "application/json",
            "X-CSRF-Token": "polling-test-token",
        },
    )

    assert response.status_code == 200
    assert response.get_json() == []