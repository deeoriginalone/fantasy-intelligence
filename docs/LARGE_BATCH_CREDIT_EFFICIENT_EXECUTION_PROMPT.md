# Large-Batch, Credit-Efficient Execution Prompt

## Fantasy Intelligence 2.0 Delivery Frame

Deliver coherent, manager-value-focused batches for the personal league-specific decision assistant. Prioritize the six core destinations and the Command Center summary. Preserve existing data truth, integrations, evidence contracts, read-only behavior, and recovery safety. Avoid commercial, multi-user, and enterprise-scale scope unless explicitly requested.

Before major changes, require Recovery Ready evidence: runnable checkpoint, startup verification, database backup, canonical snapshot, notebook export, and six-page verification.

You are working in the Fantasy Intelligence repository.

## Operating Mode

Use a **LARGE BATCH DELIVERY** approach.

Your goal is to complete the largest safe, coherent, evidence-supported implementation batch possible in a single pass while minimizing Copilot credits, repository scans, repeated discovery, repeated validation, and conversational overhead.

## Reuse Existing Context

Assume all information supplied in the current conversation is already verified context unless repository evidence shows it has changed.

Do not:

- Re-read documents already provided.
- Re-scan the repository for facts already supplied.
- Rebuild inventories that already exist.
- Re-run successful discovery work without changed inputs.
- Produce long recaps of known information.

Only inspect additional repository locations when required for the requested implementation.

## Delivery Priority

Prioritize:

1. Manager-facing value
2. Correctness
3. Fail-closed behavior
4. Minimal repository disruption
5. Credit efficiency

Do not optimize for architectural purity if a smaller solution delivers equivalent manager-facing value.

Apply the 80/20 value rule. Prefer the path that delivers most of the manager-facing benefit with the least process overhead, unless stronger work is required for correctness, security, freshness correctness, identity correctness, ownership correctness, or corruption prevention.

## Product-Usefulness Gate

Before starting a substantial batch, identify:

1. The manager-facing decision enabled or protected.
2. The current page or workflow that consumes the result.
3. The incorrect fantasy decision the batch prevents.
4. The next useful personal-season outcome.
5. The smallest safe implementation.
6. The shortest correct evidence path.
7. Whether the work should be deferred if no current consumer exists.

If items 1 through 4 cannot be answered, defer the work by default unless it protects repository integrity, security, ownership correctness, freshness correctness, identity correctness, recovery, or prevents major data corruption.

## Batch Size Rule

Do not create micro-batches.

Instead:

- Identify the full logical boundary.
- Include all directly related implementation work.
- Include direct consumers.
- Include required focused tests.
- Include boundary-appropriate validation.
- Include rollback instructions when files are modified.

Perform one coherent batch whenever safe.

Only split work when:

- Different commit scopes are required.
- Risk boundaries differ.
- Validation requirements differ.
- Unrelated features are involved.
- A dependency cannot be safely completed in the same batch.

Do not mix unrelated cleanup, feature work, canonical documentation, generated evidence, backups, archives, and production code in one batch.

## Discovery Limits

Use this inspection order:

1. Locate the existing owning contract, service, or function.
2. Read only the matching implementation blocks.
3. Read directly related focused tests.
4. Read route or template insertion points only when consumer wiring is required.
5. Expand to adjacent files only when a confirmed dependency requires it.

Before expanding scope, ask:

1. Does this information directly affect implementation?
2. Is it already available in the supplied context?
3. Can the work proceed safely without it?

If the boundary is known, proceed with implementation.

Do not:

- Perform repository-wide scans for a known owner.
- Repeat searches for the same symbol.
- Re-read complete large files when targeted reads are available.
- Inspect canonical documentation when documentation changes are out of scope.
- Collect inventories without a direct dependency.
- Continue broad discovery after the controlling boundary is proven.

Once exact missing evidence is identified and no supported local path is likely to provide it, stop and report the smallest evidence collection needed.

Before executing a named test path, verify that it exists. If it does not exist, locate the actual owning test once, do not execute the known-missing path, and report it separately.

## Repository Rules

Repository evidence is the implementation source of truth. Never invent filenames, functions, schemas, timestamps, test results, routes, or completion claims.

Unless explicitly requested:

- Do not modify unrelated worktree changes.
- Do not update canonical documents.
- Do not run project-memory reconciliation.
- Do not run continuity.
- Do not synchronize canonical HEAD fields.
- Do not stage.
- Do not commit.
- Do not push.
- Do not perform external fantasy transactions.

Preserve read-only decision support.

Never use:

```bash
git add .
git add -A
```

If staging is explicitly requested, use exact file paths and review the staged scope first.

Keep implementation, tests, documentation, generated bundles, reports, backups, exports, archives, and cleanup in separate scopes.

## Contract and Fail-Closed Rules

Implement only the minimum required inputs, outputs, states, and missing-data behavior.

Do not add speculative:

- Sources
- Fields
- Models
- Labels
- Scores
- Rankings
- Confidence authority
- Recommendation authority
- Transaction behavior

Missing, stale, unsupported, contradictory, incomplete, ambiguous, or unverified evidence must use an existing safe state such as:

- `UNAVAILABLE`
- `BLOCKED`
- `INSUFFICIENT_EVIDENCE`
- `STALE`
- `DEGRADED`

Never silently convert missing evidence into:

- Zero
- A neutral value
- Fresh or current data
- Complete data
- Authoritative data
- Actionable advice
- Fabricated confidence

Fail-closed behavior governs authority, recommendation eligibility, rankings, confidence, scores, and transactions. It does not prohibit clearly labeled informational output, diagnostics, explanations, or reduced-scope context.

Before stopping at `UNAVAILABLE`, take one cheap local step when it could expose a useful supported subset or identify the exact blocker. Stop after that step when the boundary is proven.

## Implementation Mindset

Do not spend credits proving something already proven.

Do not create another planning step when implementation can safely begin.

Do not stop after identifying a fix.

Use this cycle:

1. Locate the owner and direct consumer.
2. Make the smallest reversible change that satisfies the full logical batch.
3. Add or update focused tests.
4. Validate the changed boundary.
5. Fix only verified failures.
6. Re-run only the affected checks.
7. Report the result concisely.

Maintain a short active batch manifest containing:

- Objective
- Manager-facing decision
- Files in scope
- Validation required
- Known blockers
- Next action

## Validation Rules

Run only the validation required to prove the changed boundary.

Default validation for implementation work:

```bash
python -m pytest <focused_tests>
python -m py_compile <changed_python_files>
git diff --check
git diff --cached --check
```

Notes:

- Verify test paths before running them.
- No output from `py_compile`, `git diff --check`, or `git diff --cached --check` normally means success when the exit status is zero.
- Do not rerun successful checks unless code or fixtures changed afterward.
- If a command stops before later checks, run only the checks that did not execute.

Add validation only when the changed boundary requires it:

- Route checks when route payloads or routing change.
- Template checks when rendering changes.
- Desktop and 390px browser checks only for affected rendered surfaces.
- Broader regression tests only when shared recommendation or routing behavior changes.
- Database validation only when persistence, schema, migrations, or queries change.
- Security validation when authentication, authorization, CSRF, secrets, or external access changes.

Do not run by default:

- Full test suites
- All route matrices
- Repository-wide browser sweeps
- Database inventories
- Environment inventories
- Continuity workflows
- Canonical synchronization
- Repeated tests after no relevant change

## Completion and Claim Discipline

Do not claim completion without recorded validation evidence.

Clearly separate:

- Verified behavior
- Informational-only behavior
- Remaining blockers
- Unsupported authority
- Validation not performed

A successful focused implementation does not automatically prove production readiness, external transaction capability, recovery readiness, canonical synchronization, defect closure, or milestone completion.

Use repository-reality reconciliation only when canonical state, milestone state, defect status, commit boundaries, or continuity genuinely need to change.

## Required Output

Return only:

### 1. Files Changed

### 2. Behavior or Contract Added

### 3. Inputs Used

### 4. Fail-Closed Behavior

### 5. Manager-Facing Consumer and Decision Impact

### 6. Test Results

### 7. Compile Results

### 8. Diff-Check Results

### 9. Remaining Blockers

### 10. Exact Commit Recommendation

### 11. Recommended Next Batch

Keep the response concise.

Do not provide:

- A full repository-history recap
- A full roadmap recap
- Repeated known context
- Speculative future features
- Unrequested canonical-document changes

Do not stage or commit unless explicitly requested.

## Success Condition

Success equals:

- One complete and useful manager-facing improvement delivered.
- The largest safe coherent batch completed.
- Minimal targeted discovery.
- Minimal tool and token usage.
- Focused validation sufficient for the changed boundary.
- No repeated investigation.
- No unnecessary planning loops.
- No fabricated authority or unsupported completion claim.
- Unrelated repository work preserved.
