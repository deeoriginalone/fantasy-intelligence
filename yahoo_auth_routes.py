from __future__ import annotations

import secrets

from flask import Blueprint, jsonify, redirect, request, session

from services.yahoo_oauth import YahooOAuthClient, YahooOAuthError


def create_yahoo_auth_blueprint(client_factory=YahooOAuthClient):
    bp = Blueprint("yahoo_auth", __name__)

    @bp.get("/auth/yahoo/login")
    def yahoo_login():
        try:
            state = secrets.token_urlsafe(32)
            session["yahoo_oauth_state"] = state
            return redirect(client_factory().authorization_url(state))
        except YahooOAuthError as exc:
            return jsonify({"status": "AUTHORIZATION_REQUIRED", "blocker": str(exc)}), 503

    @bp.get("/auth/yahoo/callback")
    def yahoo_callback():
        if request.args.get("error"):
            return jsonify({"status": "AUTHORIZATION_REQUIRED", "blocker": "YAHOO_AUTHORIZATION_DENIED"}), 400
        state = request.args.get("state", "")
        if not state or not secrets.compare_digest(state, str(session.pop("yahoo_oauth_state", ""))):
            return jsonify({"status": "AUTHORIZATION_REQUIRED", "blocker": "YAHOO_OAUTH_STATE_MISMATCH"}), 400
        try:
            client_factory().exchange_code(request.args.get("code", ""))
            return jsonify({"status": "CONNECTED", "verified": client_factory().verify_authenticated_access(), "capabilities": client_factory().capability_inventory()})
        except YahooOAuthError as exc:
            return jsonify({"status": "DISCONNECTED", "blocker": str(exc)}), 502

    @bp.get("/auth/yahoo/status")
    def yahoo_status():
        client = client_factory()
        return jsonify({"status": client.status(), "authenticated_access": client.verify_authenticated_access(), "capabilities": client.capability_inventory()})

    return bp
