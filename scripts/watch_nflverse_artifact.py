#!/usr/bin/env python3
"""Exit quietly unless the official nflverse weekly artifact changes."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_URL = "https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_2026.csv.gz"
KNOWN_COMPRESSED_SHA256 = "563df7d38f0f0fce21510f54871aa36923fb50000a8b2d5d0710e0d8cbefba78"
KNOWN_DECOMPRESSED_SHA256 = "7bf9b616d9f86a5357093b5af6bf1fa7138c1d4cb46cab4c2765fef852c30bc4"
DEFAULT_LOG = Path("logs/nflverse_watchdog.log")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-file", type=Path, default=DEFAULT_LOG)
    args = parser.parse_args()

    request = Request(
        SOURCE_URL,
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache", "User-Agent": "fantasy-intelligence-watchdog"},
    )
    with tempfile.TemporaryDirectory(prefix="nflverse-watchdog-") as directory:
        compressed = Path(directory) / "artifact.csv.gz"
        decompressed = Path(directory) / "artifact.csv"
        with urlopen(request, timeout=60) as response, compressed.open("wb") as output:
            output.write(response.read())
        with gzip.open(compressed, "rb") as source, decompressed.open("wb") as output:
            while chunk := source.read(1024 * 1024):
                output.write(chunk)
        compressed_sha256 = sha256(compressed)
        decompressed_sha256 = sha256(decompressed)

    if compressed_sha256 == KNOWN_COMPRESSED_SHA256 and decompressed_sha256 == KNOWN_DECOMPRESSED_SHA256:
        return 0

    timestamp = datetime.now(timezone.utc).isoformat()
    args.log_file.parent.mkdir(parents=True, exist_ok=True)
    with args.log_file.open("a", encoding="utf-8") as log:
        log.write(
            f"timestamp={timestamp} source={SOURCE_URL} "
            f"old_compressed_sha256={KNOWN_COMPRESSED_SHA256} "
            f"new_compressed_sha256={compressed_sha256} "
            f"old_decompressed_sha256={KNOWN_DECOMPRESSED_SHA256} "
            f"new_decompressed_sha256={decompressed_sha256}\n"
        )
    print("SOURCE_CHANGED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
