import json
from pathlib import Path

from services.yahoo_oauth import YahooOAuthClient


class Response:
    def __init__(self, payload, content_type="application/json"):
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self.payload


def test_authorization_url_contains_required_parameters(monkeypatch, tmp_path):
    monkeypatch.setenv("YAHOO_CLIENT_ID", "client")
    monkeypatch.setenv("YAHOO_CLIENT_SECRET", "secret")
    monkeypatch.setenv("YAHOO_REDIRECT_URI", "https://example.test/auth/yahoo/callback")
    url = YahooOAuthClient(store_path=tmp_path / "tokens.json").authorization_url("state")
    assert "client_id=client" in url
    assert "response_type=code" in url
    assert "state=state" in url


def test_exchange_persists_tokens_and_authenticated_access(monkeypatch, tmp_path):
    monkeypatch.setenv("YAHOO_CLIENT_ID", "client")
    monkeypatch.setenv("YAHOO_CLIENT_SECRET", "secret")
    monkeypatch.setenv("YAHOO_REDIRECT_URI", "https://example.test/auth/yahoo/callback")
    now = iter([1000, 1000, 1000])
    responses = [Response({"access_token": "access", "refresh_token": "refresh", "expires_in": 3600}), Response({"fantasy_content": {"users": {}}})]
    client = YahooOAuthClient(opener=lambda *_args, **_kwargs: responses.pop(0), clock=lambda: next(now), store_path=tmp_path / "tokens.json")
    client.exchange_code("code")
    assert json.loads((tmp_path / "tokens.json").read_text())["refresh_token"] == "refresh"
    assert client.verify_authenticated_access()["verified"] is True


def test_expired_token_refreshes_and_preserves_refresh_token(monkeypatch, tmp_path):
    monkeypatch.setenv("YAHOO_CLIENT_ID", "client")
    monkeypatch.setenv("YAHOO_CLIENT_SECRET", "secret")
    monkeypatch.setenv("YAHOO_REDIRECT_URI", "https://example.test/auth/yahoo/callback")
    store = tmp_path / "tokens.json"
    store.write_text(json.dumps({"access_token": "old", "refresh_token": "refresh", "expires_at": 900, "last_refresh_at": 800}))
    client = YahooOAuthClient(opener=lambda *_args, **_kwargs: Response({"access_token": "new", "expires_in": 3600}), clock=lambda: 1000, store_path=store)
    assert client.status() == "CONNECTED"
    assert json.loads(store.read_text())["access_token"] == "new"


def test_missing_configuration_fails_closed(monkeypatch, tmp_path):
    for key in ("YAHOO_CLIENT_ID", "YAHOO_CLIENT_SECRET", "YAHOO_REDIRECT_URI"):
        monkeypatch.delenv(key, raising=False)
    client = YahooOAuthClient(store_path=tmp_path / "tokens.json")
    assert client.status() == "AUTHORIZATION_REQUIRED"
    assert client.verify_authenticated_access()["verified"] is False


def test_authenticated_xml_response_is_parsed_and_resource_verified(monkeypatch, tmp_path):
    monkeypatch.setenv("YAHOO_CLIENT_ID", "client")
    monkeypatch.setenv("YAHOO_CLIENT_SECRET", "secret")
    monkeypatch.setenv("YAHOO_REDIRECT_URI", "https://example.test/auth/yahoo/callback")
    store = tmp_path / "tokens.json"
    store.write_text(json.dumps({"access_token": "access", "refresh_token": "refresh", "expires_at": 5000}))
    xml = b'<fantasy_content><users count="1"><user><guid>private-guid</guid></user></users></fantasy_content>'
    client = YahooOAuthClient(opener=lambda *_args, **_kwargs: Response(xml, "application/xml; charset=utf-8"), clock=lambda: 1000, store_path=store)
    result = client.verify_authenticated_access()
    assert result["verified"] is True
    assert result["data"]["children"][0]["tag"] == "users"
    assert result["data"]["children"][0]["children"][0]["children"][0]["text"] == "[REDACTED]"


def test_malformed_and_empty_xml_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setenv("YAHOO_CLIENT_ID", "client")
    monkeypatch.setenv("YAHOO_CLIENT_SECRET", "secret")
    monkeypatch.setenv("YAHOO_REDIRECT_URI", "https://example.test/auth/yahoo/callback")
    store = tmp_path / "tokens.json"
    store.write_text(json.dumps({"access_token": "access", "refresh_token": "refresh", "expires_at": 5000}))
    for body in (b"<fantasy_content>", b""):
        client = YahooOAuthClient(opener=lambda *_args, body=body, **_kwargs: Response(body, "application/xml"), clock=lambda: 1000, store_path=store)
        result = client.verify_authenticated_access()
        assert result["verified"] is False
        assert result["blocker"] in {"YAHOO_RESPONSE_PARSE_ERROR", "YAHOO_EMPTY_RESPONSE"}


def test_json_response_remains_supported_and_missing_resource_stays_unknown(monkeypatch, tmp_path):
    monkeypatch.setenv("YAHOO_CLIENT_ID", "client")
    monkeypatch.setenv("YAHOO_CLIENT_SECRET", "secret")
    monkeypatch.setenv("YAHOO_REDIRECT_URI", "https://example.test/auth/yahoo/callback")
    store = tmp_path / "tokens.json"
    store.write_text(json.dumps({"access_token": "access", "refresh_token": "refresh", "expires_at": 5000}))
    client = YahooOAuthClient(opener=lambda *_args, **_kwargs: Response({"unexpected": {}}), clock=lambda: 1000, store_path=store)
    result = client.capability_inventory()
    assert all(item["status"] == "UNKNOWN_PENDING_VERIFICATION" for item in result.values())


def test_no_sensitive_token_fields_are_returned(monkeypatch, tmp_path):
    monkeypatch.setenv("YAHOO_CLIENT_ID", "client")
    monkeypatch.setenv("YAHOO_CLIENT_SECRET", "secret")
    monkeypatch.setenv("YAHOO_REDIRECT_URI", "https://example.test/auth/yahoo/callback")
    store = tmp_path / "tokens.json"
    store.write_text(json.dumps({"access_token": "access", "refresh_token": "refresh", "expires_at": 5000}))
    xml = b'<fantasy_content><users><user><guid>private-guid</guid></user></users></fantasy_content>'
    result = YahooOAuthClient(opener=lambda *_args, **_kwargs: Response(xml, "text/xml"), clock=lambda: 1000, store_path=store).verify_authenticated_access()
    serialized = json.dumps(result)
    assert '"access_token": "access"' not in serialized
    assert '"refresh_token": "refresh"' not in serialized
    assert "private-guid" not in serialized