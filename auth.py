from __future__ import annotations

import hmac
import secrets
from functools import wraps

from flask import jsonify, request, session

from config import Config


def _extract_admin_token() -> str:
    token = (request.headers.get("X-Admin-Token") or "").strip()
    if token:
        return token
    auth = (request.headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth.split(None, 1)[1].strip()
    return ""


def _session_is_admin() -> bool:
    return str(session.get("user_role", "")).lower() == "admin"


def _csrf_matches() -> bool:
    expected = session.get("csrf_token")
    if not expected:
        return False
    supplied = request.headers.get("X-CSRF-Token") or request.form.get("csrf_token")
    if not supplied:
        return False
    return hmac.compare_digest(str(expected), str(supplied))


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if request.method.upper() not in {"POST", "PUT", "PATCH", "DELETE"}:
            return view_func(*args, **kwargs)

        token = _extract_admin_token()
        if token:
            if not hmac.compare_digest(token, Config.ADMIN_TOKEN):
                return jsonify({"error": "unauthorized"}), 401
            return view_func(*args, **kwargs)

        if _session_is_admin():
            return view_func(*args, **kwargs)

        if _csrf_matches():
            return view_func(*args, **kwargs)

        return jsonify({"error": "unauthorized"}), 401

    return wrapped


def ensure_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def csrf_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if request.method.upper() in {"GET", "HEAD", "OPTIONS"}:
            return view_func(*args, **kwargs)
        token = _extract_admin_token()
        if token:
            if not hmac.compare_digest(token, Config.ADMIN_TOKEN):
                return jsonify({"error": "unauthorized"}), 401
            return view_func(*args, **kwargs)
        if _session_is_admin() or _csrf_matches():
            return view_func(*args, **kwargs)
        return jsonify({"error": "csrf token missing or invalid"}), 403

    return wrapped
