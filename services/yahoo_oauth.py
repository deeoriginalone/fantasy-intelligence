"""Minimal Yahoo OAuth and authenticated-access foundation."""
from __future__ import annotations

import base64
import json
import os
import secrets
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


AUTHORIZATION_ENDPOINT = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_ENDPOINT = "https://api.login.yahoo.com/oauth2/get_token"
API_ROOT = "https://fantasysports.yahooapis.com/fantasy/v2"
OAUTH_STATUSES = {
    "CONNECTED", "DISCONNECTED", "TOKEN_EXPIRED", "TOKEN_REFRESH_FAILED", "AUTHORIZATION_REQUIRED",
}


class YahooOAuthError(RuntimeError):
    """An expected Yahoo OAuth or API failure."""


SENSITIVE_KEYS = {"access_token", "refresh_token", "client_secret", "guid", "token"}


def _safe_value(key: str, value: Any) -> Any:
    return "[REDACTED]" if key.lower() in SENSITIVE_KEYS else value


def _xml_node(element: ET.Element) -> dict[str, Any]:
    tag = element.tag.rsplit("}", 1)[-1]
    node = {
        "tag": tag,
        "attributes": {key: _safe_value(key, value) for key, value in element.attrib.items()},
        "children": [_xml_node(child) for child in list(element)],
    }
    text = (element.text or "").strip()
    if text:
        node["text"] = _safe_value(tag, text)
    return node


def _redact_json(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {name: _safe_value(name, _redact_json(item, name)) for name, item in value.items()}
    if isinstance(value, list):
        return [_redact_json(item, key) for item in value]
    return value


def _parse_response(body: bytes, content_type: str | None, *, redact_sensitive: bool = True) -> Any:
    if not body.strip():
        raise YahooOAuthError("YAHOO_EMPTY_RESPONSE")
    normalized_type = (content_type or "").split(";", 1)[0].strip().lower()
    text = body.decode("utf-8", "replace")
    if normalized_type == "application/json":
        try:
            parsed = json.loads(text)
            return _redact_json(parsed) if redact_sensitive else parsed
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise YahooOAuthError("YAHOO_RESPONSE_PARSE_ERROR") from exc
    if normalized_type in {"application/xml", "text/xml"} or text.lstrip().startswith("<"):
        try:
            return _xml_node(ET.fromstring(text))
        except (ET.ParseError, ValueError) as exc:
            raise YahooOAuthError("YAHOO_RESPONSE_PARSE_ERROR") from exc
    try:
        parsed = json.loads(text)
        return _redact_json(parsed) if redact_sensitive else parsed
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise YahooOAuthError("YAHOO_RESPONSE_FORMAT_UNSUPPORTED")


def _contains_resource(value: Any, resource: str) -> bool:
    if isinstance(value, dict):
        if value.get("tag") == resource or resource in value:
            return True
        return any(_contains_resource(item, resource) for item in value.values())
    if isinstance(value, list):
        return any(_contains_resource(item, resource) for item in value)
    return False


def _required_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def yahoo_configuration() -> dict[str, str | None]:
    return {
        "client_id": _required_env("YAHOO_CLIENT_ID"),
        "client_secret": _required_env("YAHOO_CLIENT_SECRET"),
        "redirect_uri": _required_env("YAHOO_REDIRECT_URI"),
    }


def token_store_path() -> Path:
    configured = os.getenv("YAHOO_TOKEN_STORE", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".fantasy-intelligence" / "yahoo_oauth_tokens.json"


class YahooOAuthClient:
    def __init__(self, *, opener=urlopen, clock=time.time, store_path: Path | None = None):
        self.opener = opener
        self.clock = clock
        self.store_path = store_path or token_store_path()

    def configuration_state(self) -> str:
        return "CONNECTED" if all(yahoo_configuration().values()) else "AUTHORIZATION_REQUIRED"

    def authorization_url(self, state: str) -> str:
        config = yahoo_configuration()
        if not all(config.values()):
            raise YahooOAuthError("YAHOO_CONFIGURATION_MISSING")
        return AUTHORIZATION_ENDPOINT + "?" + urlencode({
            "client_id": config["client_id"],
            "redirect_uri": config["redirect_uri"],
            "response_type": "code",
            "state": state,
        })

    def exchange_code(self, code: str) -> dict[str, Any]:
        config = yahoo_configuration()
        if not all(config.values()):
            raise YahooOAuthError("YAHOO_CONFIGURATION_MISSING")
        if not code.strip():
            raise YahooOAuthError("YAHOO_AUTHORIZATION_CODE_MISSING")
        payload = urlencode({
            "code": code,
            "redirect_uri": config["redirect_uri"],
            "grant_type": "authorization_code",
        }).encode()
        response = self._token_request(payload, config)
        self._save_tokens(response)
        return response

    def refresh(self) -> dict[str, Any]:
        config = yahoo_configuration()
        tokens = self._load_tokens()
        refresh_token = tokens.get("refresh_token")
        if not all(config.values()) or not refresh_token:
            raise YahooOAuthError("YAHOO_REFRESH_UNAVAILABLE")
        payload = urlencode({"refresh_token": refresh_token, "grant_type": "refresh_token"}).encode()
        response = self._token_request(payload, config)
        response.setdefault("refresh_token", refresh_token)
        self._save_tokens(response)
        return response

    def access_token(self, *, refresh_expired: bool = True) -> str | None:
        tokens = self._load_tokens()
        access_token = tokens.get("access_token")
        expires_at = float(tokens.get("expires_at") or 0)
        if access_token and expires_at > self.clock() + 30:
            return str(access_token)
        if refresh_expired and tokens.get("refresh_token"):
            try:
                return str(self.refresh().get("access_token"))
            except YahooOAuthError:
                return None
        return None

    def status(self) -> str:
        if self.configuration_state() == "AUTHORIZATION_REQUIRED":
            return "AUTHORIZATION_REQUIRED"
        tokens = self._load_tokens()
        if not tokens:
            return "DISCONNECTED"
        if self.access_token(refresh_expired=False):
            return "CONNECTED"
        if tokens.get("refresh_token"):
            return "CONNECTED" if self.access_token() else "TOKEN_REFRESH_FAILED"
        return "TOKEN_EXPIRED"

    def verify_authenticated_access(self) -> dict[str, Any]:
        token = self.access_token()
        if not token:
            return {"status": self.status(), "verified": False, "blocker": "YAHOO_AUTHENTICATION_UNAVAILABLE"}
        try:
            data = self._api_json("/users;use_login=1", token)
            verified = _contains_resource(data, "users")
            return {"status": "CONNECTED" if verified else "DISCONNECTED", "verified": verified, "endpoint": "/users;use_login=1", "data": data, **({} if verified else {"blocker": "YAHOO_EXPECTED_RESOURCE_MISSING"})}
        except YahooOAuthError as exc:
            return {"status": "DISCONNECTED", "verified": False, "blocker": str(exc)}

    def capability_inventory(self) -> dict[str, dict[str, Any]]:
        token = self.access_token()
        if not token:
            status = self.status()
            return {name: {"status": "UNKNOWN_PENDING_VERIFICATION", "blocker": status} for name in ("account_identity", "games", "leagues", "teams")}
        endpoints = {
            "account_identity": ("/users;use_login=1", "users"),
            "games": ("/users;use_login=1/games", "games"),
            "leagues": ("/users;use_login=1/games;game_keys=nfl/leagues", "leagues"),
            "teams": ("/users;use_login=1/games;game_keys=nfl/teams", "teams"),
        }
        inventory = {}
        for name, (endpoint, resource) in endpoints.items():
            try:
                data = self._api_json(endpoint, token)
                if _contains_resource(data, resource):
                    inventory[name] = {"status": "SUPPORTED_AND_VERIFIED", "endpoint": endpoint, "data": data}
                else:
                    inventory[name] = {"status": "UNKNOWN_PENDING_VERIFICATION", "endpoint": endpoint, "blocker": "YAHOO_EXPECTED_RESOURCE_MISSING"}
            except YahooOAuthError as exc:
                inventory[name] = {"status": "UNKNOWN_PENDING_VERIFICATION", "endpoint": endpoint, "blocker": str(exc)}
        return inventory

    def _token_request(self, payload: bytes, config: dict[str, str | None]) -> dict[str, Any]:
        credentials = f"{config['client_id']}:{config['client_secret']}".encode()
        request = Request(TOKEN_ENDPOINT, data=payload, method="POST", headers={
            "Authorization": "Basic " + base64.b64encode(credentials).decode(),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        })
        try:
            with self.opener(request, timeout=30) as response:
                data = _parse_response(response.read(), response.headers.get("Content-Type"), redact_sensitive=False)
        except HTTPError as exc:
            if exc.code == 401:
                raise YahooOAuthError("YAHOO_AUTHENTICATION_FAILED") from exc
            if exc.code == 403:
                raise YahooOAuthError("YAHOO_PERMISSION_DENIED") from exc
            raise YahooOAuthError("YAHOO_TOKEN_EXCHANGE_FAILED") from exc
        except (URLError, TimeoutError, OSError, YahooOAuthError) as exc:
            raise YahooOAuthError("YAHOO_TOKEN_EXCHANGE_FAILED") from exc
        if not isinstance(data, dict) or not data.get("access_token"):
            raise YahooOAuthError("YAHOO_TOKEN_EXCHANGE_FAILED")
        return data

    def _api_json(self, endpoint: str, token: str) -> Any:
        request = Request(API_ROOT + endpoint, headers={"Authorization": f"Bearer {token}", "Accept": "application/json"})
        try:
            with self.opener(request, timeout=30) as response:
                return _parse_response(response.read(), response.headers.get("Content-Type"))
        except HTTPError as exc:
            if exc.code == 401:
                raise YahooOAuthError("YAHOO_AUTHENTICATION_FAILED") from exc
            if exc.code == 403:
                raise YahooOAuthError("YAHOO_PERMISSION_DENIED") from exc
            raise YahooOAuthError("YAHOO_AUTHENTICATED_API_UNAVAILABLE") from exc
        except (URLError, TimeoutError, OSError, YahooOAuthError) as exc:
            if isinstance(exc, YahooOAuthError):
                raise
            raise YahooOAuthError("YAHOO_AUTHENTICATED_API_UNAVAILABLE") from exc

    def _load_tokens(self) -> dict[str, Any]:
        try:
            return json.loads(self.store_path.read_text())
        except (FileNotFoundError, OSError, ValueError):
            return {}

    def _save_tokens(self, response: dict[str, Any]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        tokens = {
            "access_token": response.get("access_token"),
            "refresh_token": response.get("refresh_token") or self._load_tokens().get("refresh_token"),
            "expires_at": self.clock() + int(response.get("expires_in") or 0),
            "last_refresh_at": self.clock(),
        }
        temporary = self.store_path.with_suffix(self.store_path.suffix + ".tmp")
        temporary.write_text(json.dumps(tokens))
        os.chmod(temporary, 0o600)
        temporary.replace(self.store_path)
