#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "notebook_bundle"

REPORT_JSON = BUNDLE / "CANONICAL_SYNC_VALIDATION.json"
REPORT_MD = BUNDLE / "CANONICAL_SYNC_VALIDATION.md"

CANONICAL_FILES = {
    "PROJECT_STATUS.md": ROOT / "PROJECT_STATUS.md",
    "PROJECT_STATE.md": ROOT / "PROJECT_STATE.md",
    "DEVELOPMENT_ROADMAP.md": ROOT / "DEVELOPMENT_ROADMAP.md",
    "NEXT_SESSION_HANDOFF.md": (
        ROOT / "docs" / "NEXT_SESSION_HANDOFF.md"
    ),
}

SENSITIVE_PATTERNS = {
    "private_key": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        re.IGNORECASE,
    ),
    "github_token": re.compile(
        r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"
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


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def normalize_text(value: str) -> str:
    value = re.sub(r"]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip().casefold()


def extract_next_milestone(text: str) -> str | None:
    lines = text.splitlines()

    heading_patterns = [
        re.compile(r"^\s*#{1,6}\s*exact next milestone\s*$", re.I),
        re.compile(r"^\s*#{1,6}\s*next milestone\s*$", re.I),
        re.compile(r"^\s*\**exact next milestone\**\s*$", re.I),
        re.compile(r"^\s*\**next milestone\**\s*$", re.I),
    ]

    for index, line in enumerate(lines):
        cleaned = line.strip()

        if not any(pattern.match(cleaned) for pattern in heading_patterns):
            continue

        for candidate in lines[index + 1:index + 8]:
            candidate = candidate.strip()

            if not candidate:
                continue

            if candidate.startswith("#"):
                break

            normalized = normalize_text(candidate)

            if normalized:
                return normalized

    inline_patterns = [
        re.compile(
            r"(?im)^\s*(?:exact\s+)?next\s+milestone\s*:\s*(.+)$"
        ),
        re.compile(
            r"(?im)^\s*next\s+major\s+initiative\s*:\s*(.+)$"
        ),
    ]

    for pattern in inline_patterns:
        match = pattern.search(text)

        if match:
            return normalize_text(match.group(1))

    return None


def scan_sensitive(name: str, text: str) -> list[dict[str, object]]:
    findings = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern_name, pattern in SENSITIVE_PATTERNS.items():
            if pattern.search(line):
                findings.append(
                    {
                        "file": name,
                        "line": line_number,
                        "pattern": pattern_name,
                    }
                )

    return findings


def main() -> int:
    BUNDLE.mkdir(parents=True, exist_ok=True)

    branch = git_output("branch", "--show-current")
    head = git_output("rev-parse", "HEAD")
    short_head = git_output("rev-parse", "--short", "HEAD")

    file_results = {}
    missing_files = []
    empty_files = []
    branch_mismatches = []
    head_mismatches = []
    missing_milestones = []
    sensitive_findings = []
    milestones = {}

    for display_name, path in CANONICAL_FILES.items():
        if not path.is_file():
            missing_files.append(display_name)
            file_results[display_name] = {
                "exists": False,
            }
            continue

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        nonempty = bool(text.strip())
        branch_present = branch in text
        head_present = head in text or short_head in text
        milestone = extract_next_milestone(text)

        if not nonempty:
            empty_files.append(display_name)

        if not branch_present:
            branch_mismatches.append(display_name)

        if not head_present:
            head_mismatches.append(display_name)

        if milestone is None:
            missing_milestones.append(display_name)
        else:
            milestones[display_name] = milestone

        sensitive_findings.extend(
            scan_sensitive(display_name, text)
        )

        file_results[display_name] = {
            "exists": True,
            "bytes": path.stat().st_size,
            "nonempty": nonempty,
            "branch_present": branch_present,
            "head_present": head_present,
            "next_milestone": milestone,
        }

    unique_milestones = sorted(set(milestones.values()))

    milestone_consistent = (
        len(milestones) == len(CANONICAL_FILES)
        and len(unique_milestones) == 1
    )

    generated_at = datetime.now(timezone.utc).isoformat()

    passed = not any(
        [
            missing_files,
            empty_files,
            branch_mismatches,
            head_mismatches,
            missing_milestones,
            sensitive_findings,
            not milestone_consistent,
        ]
    )

    report = {
        "generated_at_utc": generated_at,
        "passed": passed,
        "repository": {
            "branch": branch,
            "head": head,
            "short_head": short_head,
        },
        "checks": {
            "canonical_files_present": not missing_files,
            "canonical_files_nonempty": not empty_files,
            "branch_synchronized": not branch_mismatches,
            "head_synchronized": not head_mismatches,
            "next_milestone_present": not missing_milestones,
            "next_milestone_consistent": milestone_consistent,
            "sensitive_patterns_absent": not sensitive_findings,
        },
        "files": file_results,
        "missing_files": missing_files,
        "empty_files": empty_files,
        "branch_mismatches": branch_mismatches,
        "head_mismatches": head_mismatches,
        "missing_milestones": missing_milestones,
        "unique_milestones": unique_milestones,
        "sensitive_findings": sensitive_findings,
    }

    REPORT_JSON.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    markdown = [
        "# Canonical Memory Sync Validation",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- Result: `{'PASS' if passed else 'FAIL'}`",
        f"- Current branch: `{branch}`",
        f"- Current HEAD: `{head}`",
        "",
        "## Checks",
        "",
        (
            "- Canonical files present: "
            f"`{'YES' if not missing_files else 'NO'}`"
        ),
        (
            "- Canonical files nonempty: "
            f"`{'YES' if not empty_files else 'NO'}`"
        ),
        (
            "- Branch synchronized: "
            f"`{'YES' if not branch_mismatches else 'NO'}`"
        ),
        (
            "- HEAD synchronized: "
            f"`{'YES' if not head_mismatches else 'NO'}`"
        ),
        (
            "- Next milestone present: "
            f"`{'YES' if not missing_milestones else 'NO'}`"
        ),
        (
            "- Next milestone consistent: "
            f"`{'YES' if milestone_consistent else 'NO'}`"
        ),
        (
            "- Sensitive patterns absent: "
            f"`{'YES' if not sensitive_findings else 'NO'}`"
        ),
        "",
        "## File Results",
        "",
    ]

    for name, result in file_results.items():
        markdown.append(f"### {name}")
        markdown.append("")
        markdown.append(
            f"- Exists: `{'YES' if result.get('exists') else 'NO'}`"
        )

        if result.get("exists"):
            markdown.append(
                f"- Nonempty: "
                f"`{'YES' if result.get('nonempty') else 'NO'}`"
            )
            markdown.append(
                f"- Branch present: "
                f"`{'YES' if result.get('branch_present') else 'NO'}`"
            )
            markdown.append(
                f"- HEAD present: "
                f"`{'YES' if result.get('head_present') else 'NO'}`"
            )
            milestone = result.get("next_milestone")
            markdown.append(
                f"- Next milestone: "
                f"`{milestone if milestone else 'NOT FOUND'}`"
            )

        markdown.append("")

    if unique_milestones:
        markdown.extend(
            [
                "## Extracted Milestones",
                "",
                *[f"- `{value}`" for value in unique_milestones],
                "",
            ]
        )

    if branch_mismatches:
        markdown.extend(
            [
                "## Branch Mismatches",
                "",
                *[f"- `{name}`" for name in branch_mismatches],
                "",
            ]
        )

    if head_mismatches:
        markdown.extend(
            [
                "## HEAD Mismatches",
                "",
                *[f"- `{name}`" for name in head_mismatches],
                "",
            ]
        )

    if missing_milestones:
        markdown.extend(
            [
                "## Missing Milestone Sections",
                "",
                *[f"- `{name}`" for name in missing_milestones],
                "",
            ]
        )

    REPORT_MD.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    print("Canonical memory validation complete.")
    print(f"Result: {'PASS' if passed else 'FAIL'}")
    print(f"Branch: {branch}")
    print(f"HEAD: {head}")
    print(f"Report: {REPORT_MD}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
