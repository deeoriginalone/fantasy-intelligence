#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "notebook_bundle"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CLASSIFICATION_MD = OUT_DIR / "WORKING_TREE_CLASSIFICATION.md"
CLASSIFICATION_JSON = OUT_DIR / "WORKING_TREE_CLASSIFICATION.json"
CANDIDATES_MD = OUT_DIR / "COMMIT_CANDIDATES.md"
CANDIDATES_JSON = OUT_DIR / "COMMIT_CANDIDATES.json"


CATEGORY_ORDER = [
    "continuity_system",
    "canonical_documentation",
    "documentation",
    "production_source",
    "draft_intelligence",
    "recovery_utilities",
    "tests",
    "templates",
    "database_changes",
    "audit_evidence",
    "discovery_artifacts",
    "temporary_patches",
    "generated_outputs",
    "backups_and_archives",
    "sensitive_never_commit",
    "deleted_files_review",
    "unknown_review_required",
]

CATEGORY_TITLES = {
    "continuity_system": "Continuity System",
    "canonical_documentation": "Canonical Documentation",
    "documentation": "Documentation",
    "production_source": "Production Source",
    "draft_intelligence": "Draft Intelligence",
    "recovery_utilities": "Recovery and Automation Utilities",
    "tests": "Tests",
    "templates": "Templates",
    "database_changes": "Database Changes",
    "audit_evidence": "Audit Evidence",
    "discovery_artifacts": "Discovery Artifacts",
    "temporary_patches": "Temporary Patches and Before-State Files",
    "generated_outputs": "Generated Outputs",
    "backups_and_archives": "Backups and Archives",
    "sensitive_never_commit": "Sensitive or Never Commit",
    "deleted_files_review": "Deleted Files Requiring Manual Review",
    "unknown_review_required": "Unknown or Human Review Required",
}

GUIDANCE = {
    "continuity_system": (
        "Potential standalone continuity-system commit after focused validation."
    ),
    "canonical_documentation": (
        "Keep separate from implementation unless intentionally synchronized."
    ),
    "documentation": (
        "Group by the feature, runbook, or workflow being documented."
    ),
    "production_source": (
        "Review ownership and behavior. Pair with directly related tests."
    ),
    "draft_intelligence": (
        "Review as draft-domain implementation. Pair with relevant draft tests."
    ),
    "recovery_utilities": (
        "Determine whether each file is durable tooling or temporary recovery work."
    ),
    "tests": (
        "Pair only with the production change directly validated by the test."
    ),
    "templates": (
        "Pair only with its related route or presentation-layer change."
    ),
    "database_changes": (
        "Review schema and migration safety separately before committing."
    ),
    "audit_evidence": (
        "Keep separate from implementation. Review whether the evidence is durable."
    ),
    "discovery_artifacts": (
        "Evidence-only by default. Human review required before committing."
    ),
    "temporary_patches": (
        "Do not broadly commit. Preserve only when intentionally required."
    ),
    "generated_outputs": (
        "Generated content. Usually ignore or archive outside source control."
    ),
    "backups_and_archives": (
        "Do not broadly commit."
    ),
    "sensitive_never_commit": (
        "Do not commit. Inspect for credentials, tokens, URLs, or private values."
    ),
    "deleted_files_review": (
        "Never assume deletion is intended. Review each deletion manually."
    ),
    "unknown_review_required": (
        "No conservative rule matched. Review manually."
    ),
}


CONTINUITY_FILES = {
    ".continuity/last_bundle_manifest.json",
    "docs/REPOSITORY_CHECKPOINT.md",
    "scripts/end_of_day.sh",
    "tools/generate_notebook_bundle.py",
    "tools/validate_notebook_bundle.py",
    "tools/generate_bundle_change_report.py",
    "tools/validate_canonical_sync.py",
    "tools/generate_session_recovery_pack.py",
    "tools/classify_working_tree.py",
    "tools/install_working_tree_classifier.py",
    "tools/install_continuity_extensions.py",
    "tools/patch_end_of_day.py",
    "tools/upgrade_working_tree_classifier.py",
}

CANONICAL_FILES = {
    "PROJECT_STATUS.md",
    "PROJECT_STATE.md",
    "DEVELOPMENT_ROADMAP.md",
    "docs/NEXT_SESSION_HANDOFF.md",
}

SENSITIVE_PATTERNS = [
    re.compile(r"(^|/)\.env($|\.)", re.IGNORECASE),
    re.compile(r"credential", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"token", re.IGNORECASE),
    re.compile(r"cookie", re.IGNORECASE),
    re.compile(r"code_notes", re.IGNORECASE),
]

BACKUP_MARKERS = (
    ".bak",
    ".backup",
    ".before",
    ".orig",
    ".post-draft-fixes",
    ".before_",
)

ARCHIVE_SUFFIXES = (
    ".zip",
    ".tar",
    ".tar.gz",
    ".tgz",
    ".gz",
)

DRAFT_NAME_PREFIXES = (
    "draft_",
    "adaptive_draft_",
    "candidate_filter",
    "dynamic_need_",
    "scarcity_",
    "recommendation_",
    "reconciled_draft_",
    "player_survival_",
    "survival_",
    "model_calibration",
    "intelligence_calibration",
    "intelligence_explainability",
)


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed:\n{result.stderr.strip()}"
        )

    return result.stdout


def parse_status(text: str) -> list[dict[str, str]]:
    entries = []

    for raw in text.splitlines():
        if not raw:
            continue

        status = raw[:2]
        path_text = raw[3:]
        old_path = ""
        path = path_text

        if " -> " in path_text:
            old_path, path = path_text.split(" -> ", 1)

        entries.append(
            {
                "status": status,
                "index_status": status[0],
                "worktree_status": status[1],
                "path": path,
                "old_path": old_path,
            }
        )

    return entries


def starts_with(path: str, prefixes: tuple[str, ...]) -> bool:
    return any(path.startswith(prefix) for prefix in prefixes)


def contains_backup_marker(path: str) -> bool:
    lowered = path.casefold()
    return any(marker.casefold() in lowered for marker in BACKUP_MARKERS)


def has_sensitive_name(path: str) -> bool:
    return any(pattern.search(path) for pattern in SENSITIVE_PATTERNS)


def classify(entry: dict[str, str]) -> tuple[str, str]:
    path = entry["path"]
    status = entry["status"]
    name = Path(path).name
    suffix = Path(path).suffix.casefold()

    # Always isolate tracked deletions, regardless of filename.
    if "D" in status:
        return (
            "deleted_files_review",
            "Git reports this tracked path as deleted.",
        )

    if has_sensitive_name(path):
        return (
            "sensitive_never_commit",
            "Filename suggests credentials, tokens, cookies, secrets, or private notes.",
        )

    if path in CONTINUITY_FILES:
        return (
            "continuity_system",
            "Exact continuity pipeline path.",
        )

    if path in CANONICAL_FILES:
        return (
            "canonical_documentation",
            "Canonical project-memory document.",
        )

    if path.startswith("notebook_bundle/") or path == "notebook_bundle.tar.gz":
        return (
            "generated_outputs",
            "Generated notebook continuity output.",
        )

    if path.startswith("f4_pdf_build/"):
        return (
            "generated_outputs",
            "Generated document-build output.",
        )

    if path in {
        "end_of_day_status.txt",
        "final_recovery_status.txt",
    }:
        return (
            "generated_outputs",
            "Generated status or continuity output.",
        )

    if starts_with(
        path,
        (
            "backups/",
            "backup/",
            "archive/",
            "reference_snapshot/",
        ),
    ):
        return (
            "backups_and_archives",
            "Backup, archive, or reference-snapshot path.",
        )

    if contains_backup_marker(path):
        return (
            "temporary_patches",
            "Filename contains a backup, before-state, or recovery marker.",
        )

    if path.endswith(ARCHIVE_SUFFIXES):
        return (
            "backups_and_archives",
            "Compressed archive or packaged artifact.",
        )

    if path.endswith(".patch") or path.startswith("patches/"):
        return (
            "temporary_patches",
            "Patch or recovery patch artifact.",
        )

    if name.startswith(
        (
            "apply_",
            "fix_",
            "reconcile_",
            "update_",
            "inspect_",
            "collect_",
        )
    ) and suffix == ".py":
        return (
            "recovery_utilities",
            "Root-level apply, fix, reconciliation, update, inspection, or collection utility.",
        )

    if starts_with(path, ("audit/", "reports/", "rehearsal_evidence/")):
        return (
            "audit_evidence",
            "Audit, report, verification, or rehearsal evidence.",
        )

    if starts_with(path, ("docs/discovery/",)):
        return (
            "discovery_artifacts",
            "Discovery documentation or repository-inspection artifact.",
        )

    if starts_with(path, ("database/", "migrations/")) or suffix == ".sql":
        return (
            "database_changes",
            "Database schema, SQL, or migration path.",
        )

    if path.startswith("tests/"):
        return (
            "tests",
            "Repository test path.",
        )

    if path.startswith("templates/"):
        return (
            "templates",
            "Template or presentation-layer path.",
        )

    if starts_with(
        path,
        (
            "services/",
            "ingestion/",
            "intelligence/",
        ),
    ):
        return (
            "production_source",
            "Application service or production package path.",
        )

    if starts_with(
        path,
        (
            "draft/",
            "draft_events/",
        ),
    ):
        return (
            "draft_intelligence",
            "Draft-domain implementation path.",
        )

    if name.startswith(DRAFT_NAME_PREFIXES) and suffix == ".py":
        return (
            "draft_intelligence",
            "Root-level draft, recommendation, calibration, or survival implementation.",
        )

    if path == "app.py" or path.endswith("_routes.py"):
        return (
            "production_source",
            "Application entry point or route implementation.",
        )

    if starts_with(
        path,
        (
            "scripts/",
            "tools/",
            "batch_jobs/",
        ),
    ):
        return (
            "recovery_utilities",
            "Script, tool, batch job, or automation path.",
        )

    if path.startswith("docs/") and suffix in {".md", ".rst", ".txt"}:
        return (
            "documentation",
            "Documentation path.",
        )

    if suffix in {".md", ".rst"}:
        return (
            "documentation",
            "Documentation file outside the docs directory.",
        )

    if suffix in {".py", ".html", ".css", ".js", ".ts"}:
        return (
            "production_source",
            "Source-code extension outside a recognized package.",
        )

    return (
        "unknown_review_required",
        "No conservative classification rule matched.",
    )


def status_label(entry: dict[str, str]) -> str:
    if entry["status"] == "??":
        return "untracked"

    labels = []

    if entry["index_status"] not in {" ", "?"}:
        labels.append(f"index:{entry['index_status']}")

    if entry["worktree_status"] not in {" ", "?"}:
        labels.append(f"worktree:{entry['worktree_status']}")

    return ", ".join(labels) if labels else entry["status"].strip()


def build_commit_candidates(
    categories: dict[str, list[dict[str, str]]]
) -> list[dict[str, object]]:
    definitions = [
        {
            "title": "Continuity Pipeline",
            "category": "continuity_system",
            "verdict": "POTENTIAL CANDIDATE",
            "notes": (
                "Review the continuity tools together. "
                "Generated notebook_bundle outputs are not included."
            ),
        },
        {
            "title": "Canonical Documentation",
            "category": "canonical_documentation",
            "verdict": "CORRECTIONS REQUIRED BEFORE COMMIT",
            "notes": (
                "Canonical sync validation currently determines whether "
                "branch and HEAD are synchronized."
            ),
        },
        {
            "title": "General Documentation",
            "category": "documentation",
            "verdict": "REVIEW AND PARTITION",
            "notes": (
                "Group runbooks and specifications by feature or workflow."
            ),
        },
        {
            "title": "Production Source",
            "category": "production_source",
            "verdict": "HUMAN REVIEW REQUIRED",
            "notes": (
                "Pair only with directly related tests after reviewing intent."
            ),
        },
        {
            "title": "Draft Intelligence",
            "category": "draft_intelligence",
            "verdict": "HUMAN REVIEW REQUIRED",
            "notes": (
                "Review draft-domain ownership and pair with relevant tests."
            ),
        },
        {
            "title": "Tests",
            "category": "tests",
            "verdict": "PAIR WITH IMPLEMENTATION",
            "notes": (
                "Do not create a broad tests-only group without reviewing ownership."
            ),
        },
        {
            "title": "Audit Evidence",
            "category": "audit_evidence",
            "verdict": "SEPARATE EVIDENCE REVIEW",
            "notes": (
                "Keep generated evidence separate from production implementation."
            ),
        },
        {
            "title": "Recovery and Automation Utilities",
            "category": "recovery_utilities",
            "verdict": "DURABLE OR TEMPORARY REVIEW",
            "notes": (
                "Separate durable tools from one-time repair and discovery scripts."
            ),
        },
    ]

    results = []

    for definition in definitions:
        category = definition["category"]
        entries = categories.get(category, [])

        if not entries:
            continue

        results.append(
            {
                **definition,
                "files": [entry["path"] for entry in entries],
                "count": len(entries),
            }
        )

    return results


def main() -> int:
    raw_status = run_git(
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
    )

    branch = run_git("branch", "--show-current").strip()
    head = run_git("rev-parse", "HEAD").strip()

    entries = parse_status(raw_status)
    categories: dict[str, list[dict[str, str]]] = defaultdict(list)
    classified = []

    for entry in entries:
        category, reason = classify(entry)

        item = {
            **entry,
            "status_label": status_label(entry),
            "category": category,
            "category_title": CATEGORY_TITLES[category],
            "reason": reason,
        }

        categories[category].append(item)
        classified.append(item)

    category_counts = {
        category: len(categories.get(category, []))
        for category in CATEGORY_ORDER
    }

    status_counts = Counter(
        item["status_label"]
        for item in classified
    )

    generated_at = datetime.now(timezone.utc).isoformat()

    classification_report = {
        "generated_at_utc": generated_at,
        "repository": {
            "root": str(ROOT),
            "branch": branch,
            "head": head,
        },
        "summary": {
            "total_paths": len(classified),
            "category_counts": category_counts,
            "status_counts": dict(sorted(status_counts.items())),
        },
        "categories": {
            category: categories.get(category, [])
            for category in CATEGORY_ORDER
        },
        "entries": classified,
        "safety": {
            "staged_files": False,
            "committed_files": False,
            "deleted_files": False,
            "restored_files": False,
            "moved_files": False,
        },
    }

    CLASSIFICATION_JSON.write_text(
        json.dumps(classification_report, indent=2) + "\n",
        encoding="utf-8",
    )

    markdown = [
        "# Working Tree Classification",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- Branch: `{branch}`",
        f"- HEAD: `{head}`",
        f"- Total changed paths: `{len(classified)}`",
        "",
        "## Safety",
        "",
        "- Classification only.",
        "- No files were staged.",
        "- No files were deleted or restored.",
        "- No files were moved.",
        "- No commit was created.",
        "- Category assignments are heuristic and require human review.",
        "",
        "## Category Counts",
        "",
    ]

    for category in CATEGORY_ORDER:
        markdown.append(
            f"- {CATEGORY_TITLES[category]}: "
            f"`{category_counts[category]}`"
        )

    markdown.extend(["", "## Git Status Counts", ""])

    if status_counts:
        for label, count in sorted(status_counts.items()):
            markdown.append(f"- `{label}`: `{count}`")
    else:
        markdown.append("- Working tree is clean.")

    markdown.append("")

    for category in CATEGORY_ORDER:
        items = categories.get(category, [])

        markdown.extend(
            [
                f"## {CATEGORY_TITLES[category]}",
                "",
                f"Guidance: {GUIDANCE[category]}",
                "",
            ]
        )

        if not items:
            markdown.extend(["- None", ""])
            continue

        for item in items:
            markdown.append(
                f"- `{item['status']}` `{item['path']}`"
            )
            markdown.append(
                f"  - Status: `{item['status_label']}`"
            )
            markdown.append(
                f"  - Reason: {item['reason']}"
            )

        markdown.append("")

    markdown.extend(
        [
            "## Recommended Review Order",
            "",
            "1. Sensitive or Never Commit",
            "2. Deleted Files Requiring Manual Review",
            "3. Unknown or Human Review Required",
            "4. Continuity System",
            "5. Production Source, Draft Intelligence, Tests, and Templates",
            "6. Documentation and Audit Evidence",
            "7. Temporary Patches, Generated Outputs, Backups, and Archives",
            "",
            "## Important",
            "",
            "This report is not an automatic staging list.",
            "Review exact paths before any Git operation.",
            "",
        ]
    )

    CLASSIFICATION_MD.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    candidates = build_commit_candidates(categories)

    candidate_report = {
        "generated_at_utc": generated_at,
        "repository": {
            "branch": branch,
            "head": head,
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
        "excluded_categories": {
            "sensitive_never_commit": [
                item["path"]
                for item in categories.get(
                    "sensitive_never_commit",
                    [],
                )
            ],
            "deleted_files_review": [
                item["path"]
                for item in categories.get(
                    "deleted_files_review",
                    [],
                )
            ],
            "unknown_review_required": [
                item["path"]
                for item in categories.get(
                    "unknown_review_required",
                    [],
                )
            ],
            "generated_outputs": [
                item["path"]
                for item in categories.get(
                    "generated_outputs",
                    [],
                )
            ],
            "backups_and_archives": [
                item["path"]
                for item in categories.get(
                    "backups_and_archives",
                    [],
                )
            ],
            "temporary_patches": [
                item["path"]
                for item in categories.get(
                    "temporary_patches",
                    [],
                )
            ],
        },
        "safety": {
            "automatic_git_add_commands_generated": False,
            "files_staged": False,
            "commit_created": False,
        },
    }

    CANDIDATES_JSON.write_text(
        json.dumps(candidate_report, indent=2) + "\n",
        encoding="utf-8",
    )

    candidate_md = [
        "# Commit Candidates",
        "",
        f"- Generated UTC: `{generated_at}`",
        f"- Branch: `{branch}`",
        f"- HEAD: `{head}`",
        "",
        "## Safety",
        "",
        "- Suggestions only.",
        "- No `git add` commands were generated.",
        "- No files were staged.",
        "- No commit was created.",
        "- Review every exact path before using Git.",
        "",
    ]

    if not candidates:
        candidate_md.extend(
            [
                "## Result",
                "",
                "- No conservative commit candidates were identified.",
                "",
            ]
        )

    for index, candidate in enumerate(candidates, start=1):
        candidate_md.extend(
            [
                f"## Candidate {index}: {candidate['title']}",
                "",
                f"- Verdict: `{candidate['verdict']}`",
                f"- File count: `{candidate['count']}`",
                f"- Notes: {candidate['notes']}",
                "",
                "### Files",
                "",
            ]
        )

        for filename in candidate["files"]:
            candidate_md.append(f"- `{filename}`")

        candidate_md.append("")

    excluded_sections = [
        (
            "Sensitive or Never Commit",
            categories.get("sensitive_never_commit", []),
        ),
        (
            "Deleted Files Requiring Manual Review",
            categories.get("deleted_files_review", []),
        ),
        (
            "Unknown or Human Review Required",
            categories.get("unknown_review_required", []),
        ),
        (
            "Generated Outputs",
            categories.get("generated_outputs", []),
        ),
        (
            "Temporary Patches",
            categories.get("temporary_patches", []),
        ),
        (
            "Backups and Archives",
            categories.get("backups_and_archives", []),
        ),
    ]

    candidate_md.extend(
        [
            "## Excluded From Automatic Commit Candidates",
            "",
        ]
    )

    for title, items in excluded_sections:
        candidate_md.extend([f"### {title}", ""])

        if items:
            for item in items:
                candidate_md.append(
                    f"- `{item['status']}` `{item['path']}`"
                )
        else:
            candidate_md.append("- None")

        candidate_md.append("")

    CANDIDATES_MD.write_text(
        "\n".join(candidate_md),
        encoding="utf-8",
    )

    print("Enhanced working-tree classification complete.")
    print(f"Branch: {branch}")
    print(f"HEAD: {head}")
    print(f"Changed paths: {len(classified)}")
    print(f"Commit candidates: {len(candidates)}")
    print(f"Classification: {CLASSIFICATION_MD}")
    print(f"Candidates: {CANDIDATES_MD}")

    for category in CATEGORY_ORDER:
        count = category_counts[category]

        if count:
            print(f"  {CATEGORY_TITLES[category]}: {count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
