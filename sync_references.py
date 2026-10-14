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

EXPORT_ROOT = Path('reference_exports')
BACKUP_ROOT = Path('.reference_backups')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def export_refs():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_dir = EXPORT_ROOT / ts
    export_dir.mkdir(parents=True, exist_ok=False)

    manifest = {'created_at': datetime.now().isoformat(), 'files': {}}

    for ref in REFERENCE_FILES:
        src = Path(ref)
        if not src.exists():
            print(f'MISSING: {src}')
            continue

        dst = export_dir / src
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

        manifest['files'][ref] = sha256_file(dst)
        print(f'EXPORTED: {ref}')

    (export_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    print(f'\nExport complete: {export_dir}')


def import_refs(source_dir: str, dry_run=False):
    source_dir = Path(source_dir)
    if not source_dir.exists():
        sys.exit(f'Missing import directory: {source_dir}')

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = BACKUP_ROOT / ts

    changed = []

    for ref in REFERENCE_FILES:
        repo_file = Path(ref)
        incoming = source_dir / repo_file

        if not incoming.exists():
            print(f'MISSING SOURCE: {incoming}')
            continue

        if repo_file.exists() and sha256_file(repo_file) == sha256_file(incoming):
            print(f'UNCHANGED: {repo_file}')
            continue

        changed.append((incoming, repo_file))

    if dry_run:
        print('\nDRY RUN')
        for _, target in changed:
            print(f'WOULD UPDATE: {target}')
        return

    for incoming, repo_file in changed:
        repo_file.parent.mkdir(parents=True, exist_ok=True)

        if repo_file.exists():
            backup_target = backup_dir / repo_file
            backup_target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo_file, backup_target)

        shutil.copy2(incoming, repo_file)
        print(f'UPDATED: {repo_file}')

    print('\nImport complete')
    print(f'Backups: {backup_dir}')


parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest='cmd', required=True)
sub.add_parser('export')
imp = sub.add_parser('import')
imp.add_argument('source_dir')
imp.add_argument('--dry-run', action='store_true')
args = parser.parse_args()

if args.cmd == 'export':
    export_refs()
else:
    import_refs(args.source_dir, args.dry_run)
