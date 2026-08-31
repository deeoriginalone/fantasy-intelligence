import os
from typing import Any

REQUIRED_ENV_VARS = (
    "FLASK_SECRET_KEY",
    "DB_HOST",
    "DB_PORT",
    "DB_NAME",
    "DB_USER",
    "DB_PASSWORD",
    "ADMIN_TOKEN",
    "SLEEPER_LEAGUE_ID",
    "SLEEPER_DRAFT_ID",
)


class Config:
    @staticmethod
    def _require(name: str, default: Any | None = None) -> str:
        value = os.getenv(name, default)
        if value is None or str(value).strip() == "":
            raise RuntimeError(f"Missing required environment variable: {name}")
        return str(value).strip()

    @staticmethod
    def db_kwargs() -> dict[str, Any]:
        return {
            "host": Config._require("DB_HOST"),
            "port": int(Config._require("DB_PORT")),
            "dbname": Config._require("DB_NAME"),
            "user": Config._require("DB_USER"),
            "password": Config._require("DB_PASSWORD"),
        }

    @staticmethod
    def validate() -> None:
        for name in REQUIRED_ENV_VARS:
            Config._require(name)

    SECRET_KEY = _require("FLASK_SECRET_KEY")
    ADMIN_TOKEN = _require("ADMIN_TOKEN")
    DB_HOST = _require("DB_HOST")
    DB_PORT = int(_require("DB_PORT"))
    DB_NAME = _require("DB_NAME")
    DB_USER = _require("DB_USER")
    DB_PASSWORD = _require("DB_PASSWORD")
    SLEEPER_LEAGUE_ID = _require("SLEEPER_LEAGUE_ID")
    SLEEPER_DRAFT_ID = _require("SLEEPER_DRAFT_ID")
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
    JSON_AS_ASCII = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"


Config.validate()
