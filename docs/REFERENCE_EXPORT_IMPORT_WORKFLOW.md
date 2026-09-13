# Reference Export and Import Workflow

## Purpose

This document records the workflow for exporting the Fantasy Intelligence reference documents, updating the exported working copies, and importing only changed files back into the repository.

The workflow preserves each file's repository-relative path, including the `docs/` directory. It also creates backups before replacing repository files, compares SHA256 hashes to skip unchanged files, and supports a dry-run preview.

## Required Location

Save the Python script as:

```text
/home/deeoriginalone/fantasy-intelligence/sync_references.py
```

Run every command in this document from the repository root:

```bash
cd /home/deeoriginalone/fantasy-intelligence
```

The expected repository layout is:

```text
fantasy-intelligence/
├── sync_references.py
├── DEVELOPMENT_ROADMAP.md
├── PROJECT_STATUS.md
├── PROJECT_STATE.md
└── docs/
    ├── PRODUCT_VISION.md
    ├── CURRENT_DEFECTS.md
    ├── SEASON_MANAGEMENT_STRATEGY.md
    ├── METRIC_DEFINITIONS.md
    ├── DATA_FRESHNESS_POLICY.md
    ├── PAGE_REQUIREMENTS.md
    ├── PLATFORM_MATURITY.md
    ├── NEXT_SESSION_HANDOFF.md
    └── PROJECT_MEMORY_AUTOMATION_RULES.md
```

## Developer Download and Extraction Preference

Repository commands in this workflow must still be run from:

```text
/home/deeoriginalone/fantasy-intelligence
```

Downloaded ZIP packages and extracted installer folders should normally be kept outside the repository. Demond’s preferred location is:

```text
~/Downloads
```

A recommended organization is:

```text
~/Downloads/fantasy_packages/
├── UX2_implementation_package.zip
├── UX2_implementation_package/
├── reference_update_package.zip
└── reference_update_package/
```

Use `~/Downloads` in user-facing instructions by default. `/tmp` remains an optional location for short-lived files, but it is not required.

Do not extract generated packages into the repository root. Keeping the ZIP, extracted installer, manifest, and checksum files outside the repository prevents them from being mixed into implementation commits.

When an installer is stored under `~/Downloads`, run it while the shell is positioned at the repository root:

```bash
cd /home/deeoriginalone/fantasy-intelligence
python ~/Downloads/fantasy_packages/PACKAGE_NAME/install.py
```

The package location and repository working directory serve different purposes:

- `~/Downloads` stores downloaded and extracted package artifacts.
- `/home/deeoriginalone/fantasy-intelligence` is the working directory for repository inspection, import, testing, Git review, and continuity commands.

## Managed Reference Files

The script manages these exact repository paths:

```text
docs/PRODUCT_VISION.md
docs/CURRENT_DEFECTS.md
docs/SEASON_MANAGEMENT_STRATEGY.md
docs/METRIC_DEFINITIONS.md
docs/DATA_FRESHNESS_POLICY.md
docs/PAGE_REQUIREMENTS.md
docs/PLATFORM_MATURITY.md
DEVELOPMENT_ROADMAP.md
PROJECT_STATUS.md
PROJECT_STATE.md
docs/NEXT_SESSION_HANDOFF.md
docs/PROJECT_MEMORY_AUTOMATION_RULES.md
```

## Workflow Summary

1. Run the export command from the repository root.
2. The script creates a timestamped folder under `reference_exports/`.
3. Update the files inside that timestamped export folder.
4. Run import with the timestamped folder as the source.
5. Preview with `--dry-run` before replacing repository files.
6. The script backs up existing repository files before replacing them.
7. Review the resulting repository changes with Git.

## Step 1: Export the Current Repository Files

Run:

```bash
python sync_references.py export
```

Example output:

```text
EXPORTED: docs/PRODUCT_VISION.md
EXPORTED: PROJECT_STATUS.md
...

Export complete:
reference_exports/20260911_180000
```

The export preserves repository-relative paths:

```text
reference_exports/
└── 20260911_180000/
    ├── docs/
    │   ├── PRODUCT_VISION.md
    │   ├── CURRENT_DEFECTS.md
    │   ├── SEASON_MANAGEMENT_STRATEGY.md
    │   ├── METRIC_DEFINITIONS.md
    │   ├── DATA_FRESHNESS_POLICY.md
    │   ├── PAGE_REQUIREMENTS.md
    │   ├── PLATFORM_MATURITY.md
    │   ├── NEXT_SESSION_HANDOFF.md
    │   └── PROJECT_MEMORY_AUTOMATION_RULES.md
    ├── DEVELOPMENT_ROADMAP.md
    ├── PROJECT_STATUS.md
    ├── PROJECT_STATE.md
    └── manifest.json
```

## Step 2: Update the Exported Working Copies

Yes, the updated files must be placed inside the timestamped export folder before import.

For example, an updated product vision must be located at:

```text
reference_exports/20260911_180000/docs/PRODUCT_VISION.md
```

An updated project status must be located at:

```text
reference_exports/20260911_180000/PROJECT_STATUS.md
```

Do not flatten the directory structure. Files that belong in `docs/` must remain under the export folder's `docs/` directory.

You may update all exported files or only some of them. During import:

- Changed files are imported.
- Identical files are skipped.
- Missing source files are reported and skipped.
- Repository files are not deleted because a source file is missing.

## Step 3: Preview the Import

Before changing the repository, run a dry-run:

```bash
python sync_references.py import reference_exports/20260911_180000 --dry-run
```

Example output:

```text
DRY RUN: no repository files will be changed
WOULD UPDATE: docs/PRODUCT_VISION.md
UNCHANGED: docs/CURRENT_DEFECTS.md
MISSING SOURCE: docs/PAGE_REQUIREMENTS.md

Summary:
Would update: 1
Unchanged: 1
Missing source: 1
```

A dry-run does not copy files and does not create backups.

## Step 4: Import the Updated Files

After reviewing the dry-run, run:

```bash
python sync_references.py import reference_exports/20260911_180000
```

For every changed file, the script:

1. Finds the incoming file using its full repository-relative path.
2. Compares the incoming SHA256 hash with the current repository file.
3. Skips the file if the contents are identical.
4. Copies the current repository file into a timestamped backup directory.
5. Copies the updated source file into its exact repository destination.
6. Verifies that the imported file hash matches the incoming file hash.

Example output:

```text
UPDATED: docs/PRODUCT_VISION.md
UNCHANGED: docs/CURRENT_DEFECTS.md
UPDATED: PROJECT_STATUS.md

Import complete
Backups: .reference_backups/20260911_181500
```

## Backup Layout

Backups preserve the same repository-relative paths:

```text
.reference_backups/
└── 20260911_181500/
    ├── docs/
    │   └── PRODUCT_VISION.md
    └── PROJECT_STATUS.md
```

Only repository files that are actually replaced are backed up.

## Rollback

To restore one file manually, copy it from the backup folder to its repository path:

```bash
cp \
  .reference_backups/20260911_181500/docs/PRODUCT_VISION.md \
  docs/PRODUCT_VISION.md
```

To inspect all files in a backup:

```bash
find .reference_backups/20260911_181500 -type f -print
```

Always review the backup timestamp printed by the import command before performing a rollback.

## Validation After Import

Compile-check the script:

```bash
python -m py_compile sync_references.py
```

No output normally means the compile check passed.

Review repository changes:

```bash
git status --short --branch
git diff --stat
git diff --name-status
git diff --check
```

Review a specific imported file:

```bash
git diff -- docs/PRODUCT_VISION.md
```

If canonical project-memory documents changed, review all four together:

```bash
git diff -- \
  PROJECT_STATUS.md \
  PROJECT_STATE.md \
  DEVELOPMENT_ROADMAP.md \
  docs/NEXT_SESSION_HANDOFF.md
```

After validated canonical updates, use the repository's documented continuity workflow:

```bash
python scripts/update_canonical_head.py
./scripts/end_of_day.sh
```

Then inspect:

```bash
cat notebook_bundle/BUNDLE_VALIDATION.md
cat notebook_bundle/CANONICAL_SYNC_VALIDATION.md
cat notebook_bundle/CHANGE_REPORT.md
git status --short --branch
```

## Git Safety

Do not use:

```bash
git add .
git add -A
```

Stage only the intended files with exact paths, for example:

```bash
git add \
  docs/PRODUCT_VISION.md \
  PROJECT_STATUS.md \
  PROJECT_STATE.md
```

Review the staged scope before committing:

```bash
git diff --cached --stat
git diff --cached --name-status
git diff --cached
```

## Actual Script: `sync_references.py`

```python
#!/usr/bin/env python3

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

REFERENCE_FILES = [
    "docs/PRODUCT_VISION.md",
    "docs/CURRENT_DEFECTS.md",
    "docs/SEASON_MANAGEMENT_STRATEGY.md",
    "docs/METRIC_DEFINITIONS.md",
    "docs/DATA_FRESHNESS_POLICY.md",
    "docs/PAGE_REQUIREMENTS.md",
    "docs/PLATFORM_MATURITY.md",
    "DEVELOPMENT_ROADMAP.md",
    "PROJECT_STATUS.md",
    "PROJECT_STATE.md",
    "docs/NEXT_SESSION_HANDOFF.md",
    "docs/PROJECT_MEMORY_AUTOMATION_RULES.md",
]

EXPORT_ROOT = Path("reference_exports")
BACKUP_ROOT = Path(".reference_backups")
REPOSITORY_MARKERS = (
    Path("docs"),
    Path("PROJECT_STATUS.md"),
    Path("PROJECT_STATE.md"),
    Path("DEVELOPMENT_ROADMAP.md"),
)


def sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()

    with file_path.open("rb") as source:
        while True:
            chunk = source.read(8192)
            if not chunk:
                break
            digest.update(chunk)

    return digest.hexdigest()


def require_repository_root() -> None:
    missing = [str(path) for path in REPOSITORY_MARKERS if not path.exists()]

    if missing:
        print("ERROR: Run this script from the Fantasy Intelligence repository root.")
        print("Missing expected repository markers:")
        for path in missing:
            print(f"  - {path}")
        sys.exit(1)


def safe_source_path(source_root: Path, relative_path: Path) -> Path:
    source_root = source_root.resolve()
    candidate = (source_root / relative_path).resolve()

    try:
        candidate.relative_to(source_root)
    except ValueError:
        sys.exit(f"Unsafe source path: {candidate}")

    return candidate


def export_references() -> None:
    require_repository_root()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_dir = EXPORT_ROOT / timestamp
    export_dir.mkdir(parents=True, exist_ok=False)

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "files": {},
    }

    exported = 0
    missing = 0

    for reference in REFERENCE_FILES:
        relative_path = Path(reference)
        source = relative_path

        if not source.is_file():
            print(f"MISSING REPOSITORY FILE: {source}")
            missing += 1
            continue

        destination = export_dir / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

        file_hash = sha256_file(destination)
        manifest["files"][relative_path.as_posix()] = {
            "sha256": file_hash,
            "size": destination.stat().st_size,
        }

        print(f"EXPORTED: {relative_path}")
        exported += 1

    manifest_path = export_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\nExport complete")
    print(f"Export directory: {export_dir}")
    print(f"Exported: {exported}")
    print(f"Missing repository files: {missing}")


def collect_import_plan(source_dir: Path):
    plan = []
    unchanged = []
    missing = []

    for reference in REFERENCE_FILES:
        repository_file = Path(reference)
        incoming = safe_source_path(source_dir, repository_file)

        if not incoming.is_file():
            missing.append(repository_file)
            continue

        incoming_hash = sha256_file(incoming)

        if repository_file.is_file():
            repository_hash = sha256_file(repository_file)
            if incoming_hash == repository_hash:
                unchanged.append(repository_file)
                continue

        plan.append(
            {
                "incoming": incoming,
                "repository_file": repository_file,
                "incoming_hash": incoming_hash,
                "repository_exists": repository_file.is_file(),
            }
        )

    return plan, unchanged, missing


def import_references(source_dir: str, dry_run: bool = False) -> None:
    require_repository_root()

    source_root = Path(source_dir)

    if not source_root.is_dir():
        sys.exit(f"Missing import directory: {source_root}")

    source_root = source_root.resolve()
    plan, unchanged, missing = collect_import_plan(source_root)

    if dry_run:
        print("DRY RUN: no repository files will be changed")

    for item in plan:
        action = "WOULD UPDATE" if item["repository_exists"] else "WOULD CREATE"
        if not dry_run:
            action = "UPDATE" if item["repository_exists"] else "CREATE"
        print(f"{action}: {item['repository_file']}")

    for path in unchanged:
        print(f"UNCHANGED: {path}")

    for path in missing:
        print(f"MISSING SOURCE: {path}")

    print("\nImport plan summary")
    print(f"Changed or new: {len(plan)}")
    print(f"Unchanged: {len(unchanged)}")
    print(f"Missing source: {len(missing)}")

    if dry_run:
        return

    if not plan:
        print("\nNothing to import")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_ROOT / timestamp
    backup_created = False

    for item in plan:
        incoming = item["incoming"]
        repository_file = item["repository_file"]

        repository_file.parent.mkdir(parents=True, exist_ok=True)

        if item["repository_exists"]:
            backup_file = backup_dir / repository_file
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repository_file, backup_file)
            backup_created = True

        shutil.copy2(incoming, repository_file)

        imported_hash = sha256_file(repository_file)
        if imported_hash != item["incoming_hash"]:
            sys.exit(f"Hash verification failed after importing: {repository_file}")

        action = "UPDATED" if item["repository_exists"] else "CREATED"
        print(f"{action}: {repository_file}")

    print("\nImport complete")
    if backup_created:
        print(f"Backups: {backup_dir}")
    else:
        print("Backups: none required because no existing files were replaced")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export and import Fantasy Intelligence reference documents."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "export",
        help="Export repository references into a timestamped working folder.",
    )

    import_parser = subparsers.add_parser(
        "import",
        help="Import changed references from an export folder.",
    )
    import_parser.add_argument(
        "source_dir",
        help="Timestamped export folder containing updated files.",
    )
    import_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying repository files.",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "export":
        export_references()
    elif args.command == "import":
        import_references(args.source_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
```

## Installing the Script from This Document

Copy the Python code block above into:

```text
/home/deeoriginalone/fantasy-intelligence/sync_references.py
```

Then make it executable if desired:

```bash
chmod +x sync_references.py
```

Validate it:

```bash
python -m py_compile sync_references.py
python sync_references.py --help
```

## Quick Command Reference

Export:

```bash
python sync_references.py export
```

Preview import:

```bash
python sync_references.py import reference_exports/TIMESTAMP --dry-run
```

Perform import:

```bash
python sync_references.py import reference_exports/TIMESTAMP
```

Review changes:

```bash
git status --short --branch
git diff --stat
git diff --name-status
git diff --check
```

## Final Rules

- Always run the script from the repository root.
- Edit or replace files inside a timestamped export folder before importing.
- Preserve the `docs/` directory structure.
- Run `--dry-run` before an actual import.
- Review Git diffs after import.
- Do not use broad Git staging.
- Keep exports and backups separate from implementation commits unless deliberately intended.
- Repository evidence remains the source of truth for milestone and completion claims.
