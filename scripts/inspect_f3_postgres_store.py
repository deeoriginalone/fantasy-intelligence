#!/usr/bin/env python3
"""Inspect the concrete PostgreSQL store without printing credentials."""

import inspect
import json

from draft_events.postgres_store import PostgresDraftEventStore
from draft_events.store import PostgresDraftEventStoreContract


def main():
    required = list(PostgresDraftEventStoreContract.required_methods)
    methods = {}
    for name in required + ["cleanup_test_draft"]:
        member = getattr(PostgresDraftEventStore, name, None)
        methods[name] = {
            "present": callable(member),
            "signature": str(inspect.signature(member)) if callable(member) else None,
        }
    result = {
        "class": "draft_events.postgres_store.PostgresDraftEventStore",
        "constructor": str(inspect.signature(PostgresDraftEventStore)),
        "methods": methods,
        "parity_ready": all(methods[name]["present"] for name in required),
        "isolated_test_cleanup_ready": methods["cleanup_test_draft"]["present"],
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
