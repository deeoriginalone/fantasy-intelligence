#!/usr/bin/env python3

from pathlib import Path
import subprocess
import shutil
import tarfile

ROOT = Path.cwd()
BUNDLE = ROOT / "notebook_bundle"


def run(cmd: str) -> str:
    try:
        return subprocess.check_output(
            cmd,
            shell=True,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        return e.output


def write_file(name: str, content: str):
    (BUNDLE / name).write_text(
        content,
        encoding="utf-8",
    )


def copy_if_exists(source: Path, destination_name: str):
    if source.exists():
        shutil.copy2(
            source,
            BUNDLE / destination_name,
        )
        print(f"Copied: {destination_name}")
    else:
        print(f"Missing: {source}")


print("Creating notebook bundle...")

BUNDLE.mkdir(
    parents=True,
    exist_ok=True,
)

# --------------------------------------------------
# Canonical project memory documents
# --------------------------------------------------

copy_if_exists(
    ROOT / "PROJECT_STATUS.md",
    "PROJECT_STATUS.md",
)

copy_if_exists(
    ROOT / "PROJECT_STATE.md",
    "PROJECT_STATE.md",
)

copy_if_exists(
    ROOT / "DEVELOPMENT_ROADMAP.md",
    "DEVELOPMENT_ROADMAP.md",
)

copy_if_exists(
    ROOT / "docs" / "NEXT_SESSION_HANDOFF.md",
    "NEXT_SESSION_HANDOFF.md",
)

# --------------------------------------------------
# Repository checkpoint
# --------------------------------------------------

repo_sections = []

repo_sections.append("# Repository Checkpoint\n")

commands = [
    "git branch --show-current",
    "git rev-parse HEAD",
    "git log --oneline --decorate -20",
    "git status --short --branch",
    "git diff --stat",
    "git remote -v",
]

for cmd in commands:
    repo_sections.append(f"\n## {cmd}\n")
    repo_sections.append(run(cmd))

write_file(
    "REPOSITORY_CHECKPOINT.md",
    "\n".join(repo_sections),
)

# --------------------------------------------------
# Migration inventory
# --------------------------------------------------

migration_content = []

migration_content.append("# Migration Inventory\n")

migration_content.append(
    run('find . -path "*migrations*"')
)

migration_content.append(
    run('find . -name "*.sql"')
)

write_file(
    "MIGRATIONS.md",
    "\n".join(migration_content),
)

# --------------------------------------------------
# PostgreSQL parity inventory
# --------------------------------------------------

parity_content = []

parity_content.append("# PostgreSQL Parity Status\n")

parity_content.append(
    run('find . -iname "*postgres*"')
)

parity_content.append(
    run('find . -iname "*parity*"')
)

parity_content.append(
    run('find . -iname "*verify*"')
)

write_file(
    "PARITY_STATUS.md",
    "\n".join(parity_content),
)

# --------------------------------------------------
# Schema inventory
# --------------------------------------------------

schema_content = []

schema_content.append("# Schema Inventory\n")

schema_content.append(
    run('find . -name "schema*"')
)

schema_content.append(
    run('find . -name "*models.py"')
)

write_file(
    "SCHEMA.md",
    "\n".join(schema_content),
)

# --------------------------------------------------
# Test inventory
# --------------------------------------------------

test_content = []

test_content.append("# Test Inventory\n")

test_content.append(
    run('find tests -name "*.py"')
)

test_content.append("\n## Pytest Collection\n")

test_content.append(
    run("pytest --collect-only")
)

write_file(
    "TEST_INVENTORY.md",
    "\n".join(test_content),
)

# --------------------------------------------------
# Implementation inventory
# --------------------------------------------------

implementation_content = []

implementation_content.append("# Implementation Inventory\n")

implementation_content.append(
    run('find services -name "*.py"')
)

implementation_content.append(
    run('find draft_events -name "*.py"')
)

implementation_content.append(
    run('find scripts -name "*.py"')
)

write_file(
    "IMPLEMENTATION_INVENTORY.md",
    "\n".join(implementation_content),
)

# --------------------------------------------------
# Bundle archive
# --------------------------------------------------

archive_path = ROOT / "notebook_bundle.tar.gz"

with tarfile.open(
    archive_path,
    "w:gz",
) as tar:
    tar.add(
        BUNDLE,
        arcname="notebook_bundle",
    )

print()
print("Bundle complete.")
print(f"Folder : {BUNDLE}")
print(f"Archive: {archive_path}")