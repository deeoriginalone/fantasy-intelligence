from __future__ import annotations

import os
import psycopg2

from .postgres_store import PostgresDraftEventStore


def _isolated_connection_factory():
    dsn = os.environ.get("F3_POSTGRES_TEST_DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "F3_POSTGRES_TEST_DATABASE_URL is required for PostgreSQL parity tests"
        )
    conn = psycopg2.connect(dsn)
    dbname = str(getattr(conn.info, "dbname", "") or "").lower()
    if "test" not in dbname and "parity" not in dbname:
        conn.close()
        raise RuntimeError(
            "Refusing parity execution: database name must contain 'test' or 'parity'"
        )
    return conn


def create_test_draft_event_store():
    return PostgresDraftEventStore(_isolated_connection_factory)
