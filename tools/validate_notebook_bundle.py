#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import re
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "notebook_bundle"
ARCHIVE = ROOT / "notebook_bundle.tar.gz"
REPORT_JSON = BUNDLE / "BUNDLE_VALIDATION.json"
REPORT_MD = BUNDLE / "BUNDLE_VALIDATION.md"
MANIFEST_JSON = BUNDLE / "BUNDLE_MANIFEST.json"

REQUIRED_FILES = [
    "DEVELOPMENT_ROADMAP.md",
    "IMPLEMENTATION_INVENTORY.md",
    "MIGRATIONS.md",
    "NEXT_SESSION_HANDOFF.md",
    "PARITY_STATUS.md",
    "PROJECT_STATE.md",
    "PROJECT_STATUS.md",
    "REPOSITORY_CHECKPOINT.md",
    "SCHEMA.md",
    "TEST_INVENTORY.md",
]

SENSITIVE_PATTERNS = {
    "private_key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        re.IGNORECASE,
    ),
    "github_token": re.compile(
        r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"
    ),
    "aws_access_key": re.compile(
        r"\bAKIA[0-9A-Z]{16}\b"
    ),
    "jwt": re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\."
        r"[A-Za-z0-9_-]{10,}\."
        r"[A-Za-z0-9_-]{10,}\b"
    ),
    "password_assignment": re.compile(
        r"(?i)\b(?:password|passwd|pwd|admin_token)\s*="
        r"\s*[\"']?[^\s\"']{4,}"
    ),
    "database_url_with_password": re.compile(
        r"(?i)\bpostgres(?:ql)?://[^:\s]+:[^@\s]+@"
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def scan_text(path: Path) -> list[dict[str, object]]:
    findings: list[dict[str, object]] = []

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [
            {
                "file": str(path.relative_to(ROOT)),
                "pattern": "read_error",
                "line": None,
                "message": str(exc),
            }
        ]

    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(line):
                findings.append(
                    {
                        "file": str(path.relative_to(ROOT)),
                        "pattern": pattern_name,
                        "line": line_number,
                    }
                )

    return findings


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat()

    missing_files: list[str] = []
    empty_files: list[str] = []
    manifest_files: list[dict[str, object]] = []
    sensitive_findings: list[dict[str, object]] = []

    if not BUNDLE.is_dir():
        print(f"ERROR: bundle directory does not exist: {BUNDLE}")
        return 1

    for filename in REQUIRED_FILES:
        path = BUNDLE / filename

        if not path.is_file():
            missing_files.append(filename)
            continue

        size = path.stat().st_size

        if size == 0:
            empty_files.append(filename)

        manifest_files.append(
            {
                "name": filename,
                "bytes": size,
                "sha256": sha256_file(path),
            }
        )

        sensitive_findings.extend(scan_text(path))

    archive_exists = ARCHIVE.is_file()
    archive_members: list[str] = []
    archive_error: str | None = None

    if archive_exists:
        try:
            with tarfile.open(ARCHIVE, "r:gz") as archive:
                archive_members = sorted(
                    member.name
                    for member in archive.getmembers()
                    if member.isfile()
                )
        except (tarfile.TarError, OSError) as exc:
            archive_error = str(exc)

    expected_archive_members = {
        f"notebook_bundle/{filename}"
        for filename in REQUIRED_FILES
    }

    missing_archive_members = sorted(
        expected_archive_members.difference(archive_members)
    )

    manifest = {
        "generated_at_utc": generated_at,
        "bundle_directory": str(BUNDLE.relative_to(ROOT)),
        "archive": ARCHIVE.name,
        "files": manifest_files,
    }

    MANIFEST_JSON.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    passed = not any(
        [
            missing_files,
            empty_files,
            sensitive_findings,
            not archive_exists,
            archive_error,
            missing_archive_members,
        ]
    )

    report = {
        "generated_at_utc": generated_at,
        "passed": passed,
        "checks": {
            "bundle_directory_exists": True,
            "required_files_present": not missing_files,
            "required_files_nonempty": not empty_files,
            "archive_exists": archive_exists,
            "archive_readable": archive_exists and archive_error is None,
            "archive_members_complete": not missing_archive_members,
            "sensitive_patterns_absent": not sensitive_findings,
        },
        "missing_files": missing_files,
        "empty_files": empty_files,
        "missing_archive_members": missing_archive_members,
        "archive_error": archive_error,
        "sensitive_findings": sensitive_findings,
        "manifest": MANIFEST_JSON.name,
    }

    REPORT_JSON.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    markdown = [
        "# Notebook Bundle Validation",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- Result: `{'PASS' if passed else 'FAIL'}`",
        f"- Required files present: `{'YES' if not missing_files else 'NO'}`",
        f"- Required files nonempty: `{'YES' if not empty_files else 'NO'}`",
        f"- Archive exists: `{'YES' if archive_exists else 'NO'}`",
        (
            "- Archive readable: "
            f"`{'YES' if archive_exists and archive_error is None else 'NO'}`"
        ),
        (
            "- Archive members complete: "
            f"`{'YES' if not missing_archive_members else 'NO'}`"
        ),
        (
            "- Sensitive patterns absent: "
            f"`{'YES' if not sensitive_findings else 'NO'}`"
        ),
        "",
    ]

    if missing_files:
        markdown.extend(
            [
                "## Missing Files",
                "",
                *[f"- `{name}`" for name in missing_files],
                "",
            ]
        )

    if empty_files:
        markdown.extend(
            [
                "## Empty Files",
                "",
                *[f"- `{name}`" for name in empty_files],
                "",
            ]
        )

    if missing_archive_members:
        markdown.extend(
            [
                "## Missing Archive Members",
                "",
                *[f"- `{name}`" for name in missing_archive_members],
                "",
            ]
        )

    if archive_error:
        markdown.extend(
            [
                "## Archive Error",
                "",
                f"`{archive_error}`",
                "",
            ]
        )

    if sensitive_findings:
        markdown.extend(
            [
                "## Sensitive Pattern Findings",
                "",
            ]
        )

        for finding in sensitive_findings:
            markdown.append(
                f"- `{finding['file']}` line `{finding['line']}`: "
                f"`{finding['pattern']}`"
            )

        markdown.append("")

    markdown.extend(
        [
            "## Manifest",
            "",
            f"- `{MANIFEST_JSON.name}`",
            "",
        ]
    )

    REPORT_MD.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    print("Notebook bundle validation complete.")
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    print(f"JSON report: {REPORT_JSON}")
    print(f"Markdown report: {REPORT_MD}")
    print(f"Manifest: {MANIFEST_JSON}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
