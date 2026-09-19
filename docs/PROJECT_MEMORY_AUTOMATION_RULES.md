# Fantasy Intelligence Project Memory Automation Rules

## Purpose

This reference tells Copilot when to trigger a project-memory review during Fantasy Intelligence development. It exists so milestone completion, validation evidence, completion boundaries, and next-work decisions are carried into durable repository documents instead of depending on historical chat memory.

Repository evidence remains the source of truth. Chat history may help identify what to inspect, but it must never be the only evidence used to mark work complete or update a milestone. Project-memory work is proportional: a changed boundary may be recorded at session close without triggering repeated repository-wide review loops.

Project-memory review is Class C work and is not a default step for Class A read-only investigation or Class B focused implementation. Use proportional rigor: the fewest searches, reads, tool calls, tests, browser checks, and output tokens that can truthfully prove the requested boundary. Stop when the boundary is proven or precise missing evidence is identified.

## Trigger Conditions

Project-memory review is triggered when:

1. Canonical milestone state changes.
2. The verified completion boundary changes.
3. Defect status changes.
4. The exact next milestone changes.
5. The user explicitly requests one of:
   - update project memory
   - prepare handoff
   - project-memory review
   - repository reconciliation

Focused tests passing alone is not a trigger.

A completed implementation batch alone is not a trigger.

"Ready to commit" is not a trigger.

Commit creation alone is not a trigger.

A new project-memory review is required only when canonical project memory would change.

## Review Reuse Rule

If the previous review already completed, canonical documents remain correct, milestone wording remains unchanged, and the completion boundary remains unchanged, reuse the previous review.

Do not perform another Class C review.

## Evidence Required Before Updating Completion Status

Before changing milestone or defect status, Copilot must inspect or request repository evidence for the claimed boundary, including as applicable:

- Current branch and HEAD.
- Working-tree, staged, unstaged, and untracked state.
- Implementation files related to the milestone.
- Focused tests and exact results.
- Active-route or rendered-page evidence when the definition of done requires it.
- Compile or syntax checks for changed code.
- `git diff --check`.
- `git diff --cached --check` when staged changes exist.
- Existing completion criteria and product requirements.
- Current canonical project-memory documents.

If the evidence is missing or incomplete, Copilot must not claim the milestone complete. It should identify the missing proof and preserve the current completion boundary.

## Required Documents to Review

For every triggered project-memory review, compare these four canonical files:

- `PROJECT_STATUS.md`
- `PROJECT_STATE.md`
- `DEVELOPMENT_ROADMAP.md`
- `docs/NEXT_SESSION_HANDOFF.md`

Review these additional references when relevant:

- `CURRENT_DEFECTS.md`
- `PRODUCT_VISION.md`
- `SEASON_MANAGEMENT_STRATEGY.md`
- `METRIC_DEFINITIONS.md`
- `DATA_FRESHNESS_POLICY.md`
- `PAGE_REQUIREMENTS.md`
- `PLATFORM_MATURITY.md`
- `docs/REPOSITORY_CHECKPOINT.md`
- milestone-specific implementation, test, route, template, database, parity, and validation evidence

## Required Review Questions

Copilot must determine whether the verified evidence changes any of the following:

1. Current date, branch, or HEAD.
2. Current milestone status.
3. Verified capabilities or delivered implementation.
4. Validation evidence and exact test results.
5. Completion boundary and unsupported claims.
6. Defect status.
7. Outstanding work.
8. Deferred work.
9. Exact next milestone.
10. Handoff instructions.
11. Database, parity, recovery, production, live-route, or external-transaction boundaries.

## Canonical Synchronization Rules

The four canonical project-memory files must agree on:

- Current branch and HEAD.
- Exact next-milestone heading.
- Exact next-milestone wording.
- Verified completion boundary.
- Validation evidence.
- Outstanding work.
- Deferred strategic work.
- Live-route, database, parity, recovery, production, and transaction boundaries.

Use this exact parser-friendly structure in all four files:

```md
## Next milestone

**<Exact milestone text.>**
```

The milestone wording must be identical across all four files.

## Defect Status Rules

When updating `CURRENT_DEFECTS.md`, preserve these evidence boundaries:

- `REPORTED`: observed but not reproduced in a controlled test.
- `REPRODUCED`: confirmed on the active route with evidence.
- `IN PROGRESS`: implementation work has started.
- `VALIDATED`: focused tests and required active-route verification passed.
- `CLOSED`: repair is committed and continuity validation passed.
- `NOT REPRODUCIBLE`: investigated but not confirmed, with evidence recorded.

Do not move a defect to a stronger status than its evidence supports.

## Example: UX-QA.1 Completion Trigger

If the user says, "UX-QA.1 is complete," Copilot must not immediately mark it complete. Copilot must:

1. Compare the UX-QA.1 success criteria with repository and validation evidence.
2. Verify required ownership, freshness, shared-fact, recommendation, explanation, and active-route evidence.
3. Review relevant defect statuses in `CURRENT_DEFECTS.md`.
4. Determine the exact verified completion boundary.
5. Prepare synchronized changes for the four canonical project-memory files.
6. Update product or defect references only where the evidence requires it.
7. Identify and synchronize the exact next milestone.
8. Preserve any unverified or outstanding work explicitly.
9. Run or instruct the repository continuity workflow after the canonical source files are updated.

## Update Output Expected From Copilot

When a project-memory update is intentionally requested or required at session close, Copilot should produce a project-memory update package or precise proposed changes containing:

1. What triggered the review.
2. Evidence inspected.
3. Verified milestone decision.
4. Files that require updates.
5. Exact changes for each file.
6. Validation still required, if any.
7. Continuity commands and expected checks.
8. Exact files safe to stage.
9. Current completion status.
10. Exact next milestone.

When file-generation capability is available, prefer downloadable files or a deterministic patch package over asking the user to manually recreate long edits.

## Continuity Workflow

After the canonical source documents are updated and reviewed at session close, run the repository's documented continuity sequence:

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
git diff --cached --stat
git diff --cached --name-status
```

A synchronization PASS confirms documentation consistency. It does not prove feature completion beyond the recorded validation boundary.

## Git and Repository Safety

- Never use `git add .`.
- Never use `git add -A`.
- Use exact file lists.
- Preserve unrelated changes.
- Review staged and unstaged versions separately.
- Keep generated bundles, reports, backups, audits, and archives separate from implementation commits unless explicitly intended.
- Do not update generated notebook-bundle copies as the primary source. Update canonical files first, then regenerate outputs.

## Notebook Reference Rule

Add this file to the Copilot Notebook references. Its purpose is to remind Copilot in future chats to trigger a project-memory review when milestone evidence changes.

This reference does not make Notebook references automatically writable and does not replace repository evidence. It provides a durable instruction contract so the review is triggered consistently even when prior chat history is unavailable.

## Final Rule

When a milestone appears complete and the session is ready to close:

1. Trigger the review.
2. Verify repository evidence.
3. Determine the supported completion boundary.
4. Update canonical source documents consistently.
5. Regenerate continuity artifacts once at session close.
6. Review the exact staged scope.
7. Never rely on chat memory alone.
