#!/usr/bin/env python3
"""Apply Draft HQ presentation consistency fixes in one reversible batch.

Changes:
1. Make the existing Draft Coach confidence aliases use decision-plan confidence.
2. Relabel NEXT-PICK AVAILABILITY as MONTE CARLO AVAILABILITY.
3. Display weighted Need, Scarcity, Strategy, and League contributions in Top 5.

No recommendation ordering, score, route, database, or panel is changed.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import ast
import py_compile
import shutil
import sys

ROOT = Path(__file__).resolve().parent
PLAN = ROOT / "draft_decision_plan.py"
TEMPLATE = ROOT / "templates" / "draftboard.html"
APP = ROOT / "app.py"
BACKUP = ROOT / "backups" / "draft-hq-presentation-fix" / datetime.now().strftime("%Y%m%d-%H%M%S")


def backup(path: Path) -> None:
    destination = BACKUP / path.relative_to(ROOT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)


def main() -> int:
    required = [APP, PLAN, TEMPLATE, ROOT / "balanced_recommendation_score.py"]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        print("STOPPED: missing " + ", ".join(missing), file=sys.stderr)
        return 1

    for path in (APP, PLAN, TEMPLATE):
        backup(path)

    try:
        # 1. Unify every common legacy Draft Coach confidence alias.
        plan = PLAN.read_text(encoding="utf-8")
        old = (
            "out['reasons']=reasons;out['decision_plan']=plan or {};"
            "out['decision_confidence']=(plan or {}).get('confidence');"
            "out['decision_confidence_label']=(plan or {}).get('confidence_label');"
            "out['fallbacks']=(plan or {}).get('fallbacks') or [];return out"
        )
        new = (
            "out['reasons']=reasons;out['decision_plan']=plan or {};"
            "out['decision_confidence']=(plan or {}).get('confidence');"
            "out['decision_confidence_label']=(plan or {}).get('confidence_label');"
            "out['confidence']=(plan or {}).get('confidence');"
            "out['confidence_score']=(plan or {}).get('confidence');"
            "out['confidence_pct']=(plan or {}).get('confidence');"
            "out['confidence_label']=(plan or {}).get('confidence_label');"
            "out['fallbacks']=(plan or {}).get('fallbacks') or [];return out"
        )
        if old in plan:
            plan = plan.replace(old, new, 1)
        elif "out['confidence_score']=(plan or {}).get('confidence')" not in plan:
            raise RuntimeError("Draft Coach confidence fusion anchor was not found")
        ast.parse(plan, filename=str(PLAN))

        # 2 and 3. Correct labels and show actual weighted contributions.
        template = TEMPLATE.read_text(encoding="utf-8")

        availability_replacements = [
            ("NEXT-PICK AVAILABILITY", "MONTE CARLO AVAILABILITY"),
            ("Next-Pick Availability", "Monte Carlo Availability"),
            ("Next-pick availability", "Monte Carlo availability"),
        ]
        availability_changed = False
        for old_label, new_label in availability_replacements:
            if old_label in template:
                template = template.replace(old_label, new_label, 1)
                availability_changed = True
                break
        if not availability_changed and "MONTE CARLO AVAILABILITY" not in template:
            raise RuntimeError("Next-pick availability tile label was not found")

        # Candidate expressions are unique to the Top 5 table in the live template.
        expression_replacements = {
            "{{ candidate.need_score }}": "{{ '%.1f'|format(candidate.weighted_components.need) }}",
            "{{ candidate.scarcity_score }}": "{{ '%.1f'|format(candidate.weighted_components.scarcity) }}",
            "{% if candidate.strategy_bonus > 0 %}+{% endif %}{{ candidate.strategy_bonus }}": "{% if candidate.weighted_components.strategy > 0 %}+{% endif %}{{ '%.1f'|format(candidate.weighted_components.strategy) }}",
            "{% if candidate.league_bonus > 0 %}+{% endif %}{{ candidate.league_bonus }}": "{% if candidate.weighted_components.league > 0 %}+{% endif %}{{ '%.1f'|format(candidate.weighted_components.league) }}",
        }
        for old_expr, new_expr in expression_replacements.items():
            if old_expr in template:
                template = template.replace(old_expr, new_expr, 1)
            elif new_expr not in template:
                raise RuntimeError("Top 5 weighted expression was not found: " + old_expr)

        # Rename only the Top 5 header sequence, leaving other tables untouched.
        old_headers = (
            "<th>Need</th><th>Scarcity</th><th>Strategy</th>"
            "<th>League</th><th>Draft Score</th>"
        )
        new_headers = (
            "<th>Need +</th><th>Scarcity +</th><th>Strategy +</th>"
            "<th>League +</th><th>Draft Score</th>"
        )
        if old_headers in template:
            template = template.replace(old_headers, new_headers, 1)
        elif new_headers not in template:
            raise RuntimeError("Top 5 contribution header sequence was not found")

        # Validate before writing.
        ast.parse(PLAN.read_text(encoding="utf-8") if False else plan, filename=str(PLAN))
        PLAN.write_text(plan, encoding="utf-8")
        TEMPLATE.write_text(template, encoding="utf-8")

        py_compile.compile(str(PLAN), doraise=True)
        py_compile.compile(str(APP), doraise=True)

        final_plan = PLAN.read_text(encoding="utf-8")
        final_template = TEMPLATE.read_text(encoding="utf-8")
        checks = {
            "confidence_alias": "out['confidence_score']=(plan or {}).get('confidence')" in final_plan,
            "confidence_label_alias": "out['confidence_label']=(plan or {}).get('confidence_label')" in final_plan,
            "monte_label": "MONTE CARLO AVAILABILITY" in final_template,
            "weighted_need": "candidate.weighted_components.need" in final_template,
            "weighted_scarcity": "candidate.weighted_components.scarcity" in final_template,
            "weighted_strategy": "candidate.weighted_components.strategy" in final_template,
            "weighted_league": "candidate.weighted_components.league" in final_template,
            "weighted_headers": "<th>Need +</th><th>Scarcity +</th><th>Strategy +</th><th>League +</th>" in final_template,
        }
        failed = [name for name, passed in checks.items() if not passed]
        if failed:
            raise RuntimeError("post-write verification failed: " + ", ".join(failed))

        print("PASS: Draft HQ confidence, availability label, and weighted columns fixed")
        print(f"Backup: {BACKUP.relative_to(ROOT)}")
        print("Expected confidence badge: MEDIUM CONFIDENCE · 69% (current evidence)")
        print("Expected tile label: MONTE CARLO AVAILABILITY")
        print("Expected Top 5 values: Need 25.0, Scarcity 7.5, Strategy 9.0 for WR Heavy")
        print("No score, order, route, database, or panel was changed.")
        print("Restart the app and reload /draftboard.")
        return 0

    except Exception as exc:
        print("STOPPED: " + str(exc), file=sys.stderr)
        print(f"Backups are under: {BACKUP.relative_to(ROOT)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
