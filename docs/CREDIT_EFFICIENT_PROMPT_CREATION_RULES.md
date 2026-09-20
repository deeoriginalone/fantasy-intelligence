# Credit-Efficient Prompt Creation Rules

## Purpose

Use this reference whenever creating implementation, validation, Git, documentation, or roadmap prompts for the Fantasy Intelligence repository.

The goal is to deliver the largest safe and useful result while using as few Copilot credits, repository scans, tool calls, test runs, and output tokens as practical.

Efficiency must never override correctness, safety, repository evidence, fail-closed behavior, or required validation.

## Default Operating Rule

Before drafting a prompt:

1. Reuse verified context already supplied in the current conversation.
2. Do not rediscover facts that are already verified and unchanged.
3. Inspect only the files required for the requested batch.
4. Prefer one coherent implementation batch over many small batches.
5. Run only focused validation for the changed boundary.
6. Expand scope only when focused evidence is insufficient or a dependency requires it.

### Delivery and usefulness override

- Prefer solution-first, manager-facing improvement over another discovery loop once the owner and boundary are known.
- Fail-closed behavior governs authority, recommendation eligibility, ranking, confidence, score, and transactions; it does not prohibit clearly labeled informational or reduced-scope output.
- Apply one more cheap local step before declaring a capability unavailable when it may preserve useful context.
- Gate source-dependent work on source feasibility: identity, timestamps, freshness, completeness, and authority must be realistically obtainable for the intended consumer.
- Maintain an active batch manifest rather than repeatedly rebuilding repository inventories.
- Run continuity and HEAD synchronization only at deliberate session close.
- For Survivor, favor a complete read-only vertical slice and disclose exactly where authority or contest truth remains unavailable.
- Apply the manager-value override when process overhead would delay a safe, useful decision improvement.

### 80/20 Value Rule

When two valid implementation paths exist, prefer the path that delivers approximately 80% of the manager-facing value with the least repository process overhead. Do not pursue the theoretically ideal implementation first unless it is required for correctness, security, freshness correctness, identity correctness, ownership correctness, or corruption prevention. When choosing between manager-facing value now and additional infrastructure needed only for the final 20%, prefer manager-facing value now by default. Preserve fail-closed authority, recommendation safety, freshness safety, ownership correctness, identity correctness, security protections, and source-truth requirements.

## Prompt Construction Standard

Every implementation prompt should contain only the sections needed below.

### Current Verified Boundary

Include only facts needed to prevent regression or duplicated discovery.

Do not repeat:

- full project history
- complete roadmap history
- old test counts
- branch and HEAD unless Git state is relevant
- previously verified architecture unless the batch could change it
- canonical-document summaries unless documentation is in scope

### Objective

State one clear outcome.

Prefer:

> Create a pure, fail-closed contract for X and expose it informationally.

Avoid long background explanations.

### Scope

Name the smallest likely file and consumer areas.

Use language such as:

- Inspect only directly related services, consumers, templates, and tests.
- Avoid broad repository scans.
- Reuse existing contracts before creating new abstractions.
- Stop expanding scope when the requested boundary is satisfied.

Do not guess exact filenames when they have not been verified. In that case, instruct the agent to locate the owning service, route, template, and focused tests first.

### Preserve Boundaries

Unless explicitly requested, always include:

- Do not modify unrelated worktree changes.
- Do not update canonical documents.
- Do not run continuity.
- Do not stage.
- Do not commit.
- Do not change recommendation, ranking, confidence, score, or transaction behavior.
- Preserve read-only decision support.

### Contract

List only required inputs, outputs, states, and missing-data behavior.

Do not add speculative fields, models, labels, sources, calculations, or recommendation authority.

### Fail-Closed Rules

Require missing, stale, unsupported, contradictory, incomplete, or unverified evidence to become one of the existing safe states, such as:

- UNAVAILABLE
- BLOCKED
- INSUFFICIENT_EVIDENCE
- STALE

Never permit missing evidence to become a neutral, zero, current, complete, authoritative, or actionable value.

### Validation

Use the minimum validation that proves the changed boundary:

1. Focused tests for changed services and consumers.
2. `python -m py_compile` for changed Python files.
3. `git diff --check`.
4. `git diff --cached --check`.
5. Route checks only when route payloads or templates change.
6. Desktop and 390px checks only for changed rendered surfaces.
7. Broader regression tests only when shared recommendation or routing behavior changes.
8. Database validation only when persistence, schema, migrations, or queries change.

Do not request:

- full test suites by default
- all route matrices by default
- continuity runs by default
- canonical synchronization by default
- broad browser sweeps by default
- repeated tests after no code or fixture change

### Output

Require short structured output only:

1. Files changed
2. Contract or behavior added
3. Inputs used
4. Fail-closed behavior
5. Consumer or decision impact
6. Test results
7. Compile results
8. Diff-check results
9. Remaining blockers
10. Exact commit recommendation

Do not request a narrative recap unless needed.

## Search and Inspection Efficiency

Use this order:

1. Search for the existing owning contract or function.
2. Read only the matching implementation blocks.
3. Read directly related focused tests.
4. Read route/template insertion points only if consumer wiring is required.
5. Expand to adjacent files only when a confirmed dependency requires it.

Avoid:

- repository-wide scans for a known owner file
- repeated searches for the same symbol
- rereading complete large files when line-targeted reads are available
- inspecting documentation when documentation changes are prohibited
- checking unrelated routes or consumers

## Tool and Credit Efficiency

- Combine independent searches or validations when safe.
- Reuse previous tool output when it remains current.
- Do not rerun successful checks unless code or fixtures changed afterward.
- If a command stops before later checks, run only the checks that did not execute.
- Reuse an existing current validation server only if it is confirmed to serve the latest code. Otherwise use a fresh alternate port.
- Stop temporary validation servers after checks.
- Treat no output from compile or Git whitespace checks as success when the exit status is zero.
- Fix the smallest verified defect and rerun the smallest affected test set.

## Repository Safety

Always preserve these rules:

- Repository evidence is the implementation source of truth.
- Never invent filenames, schemas, functions, test results, timestamps, or completion claims.
- Never use `git add .`.
- Never use `git add -A`.
- Stage exact paths only.
- Keep implementation, documentation, generated bundles, backups, exports, archives, and cleanup in separate commit scopes.
- Inspect staged and unstaged layers separately when a file exists in both.
- Do not claim completion without recorded validation.

## When a Broader Review Is Required

Credit-saving rules do not bypass repository-reality reconciliation when:

- the roadmap appears behind implementation
- a major milestone is reported complete
- canonical documents disagree
- the branch or HEAD is uncertain
- staged and unstaged changes overlap ambiguously
- a major commit or continuity run is being prepared
- validation evidence is incomplete or contradictory

In those cases, perform the required repository review, but keep queries targeted and avoid duplicating evidence already collected in the same review.

## Default Credit-Efficient Prompt Template

```text
<BATCH NAME>

Current verified boundary:

- <Only the facts needed for this batch.>

Do not modify unrelated worktree changes.
Do not update canonical documents.
Do not run continuity.
Do not stage.
Do not commit.
Preserve read-only and fail-closed behavior.

OBJECTIVE

<Create one clear outcome.>

SCOPE

Inspect only:

- <owning service or contract>
- <direct consumers if needed>
- <direct templates if needed>
- <focused tests>

Avoid broad repository scans.
Reuse existing contracts before adding new abstractions.

CONTRACT

Inputs:

- <minimum verified inputs>

Outputs or states:

- <minimum required outputs>

No new sources, scoring, ranking, confidence, or recommendation authority unless explicitly requested.

FAIL-CLOSED

Missing, stale, unsupported, contradictory, incomplete, or unverified evidence must become:

- UNAVAILABLE
- BLOCKED
- INSUFFICIENT_EVIDENCE

Never invent or silently substitute values.

CONSUMER RULE

<Describe informational visibility or exact allowed effect.>

Must not modify:

- existing decisions
- rankings
- confidence
- scores
- transaction behavior

VALIDATION

Run only focused tests for changed contracts and consumers.
Run:

python -m py_compile <changed Python files>
git diff --check
git diff --cached --check

Run route checks only if route payloads or templates change.
If rendered surfaces change, verify only affected routes at desktop and 390px.

OUTPUT

Return only:

1. Files changed
2. Contract or behavior
3. Inputs used
4. Fail-closed behavior
5. Consumer impact
6. Test results
7. Compile results
8. Diff-check results
9. Remaining blockers
10. Exact commit recommendation

Do not stage.
Do not commit.
```

## Final Rule

Use the fewest searches, reads, tool calls, test runs, browser checks, and output tokens that can truthfully prove the requested boundary. Preserve production-level rigor for decision-critical behavior, but do not apply production-scale process to low-risk, read-only investigation. Stop when the requested question is answered, the boundary is proven, or the precise missing evidence is identified. A missing input is a valid final result for a read-only investigation.

Do not save credits by skipping required evidence. Save credits by eliminating repeated discovery, unrelated scans, oversized test runs, duplicated explanations, and unsupported feature expansion.

Once exact missing evidence is identified, stop broad discovery unless repository evidence supports a specific unsearched location likely to contain it. Do not repeat searches over the same scope without distinct purposes, execute a named test path proven missing, rerun successful checks without changed code or fixtures, search canonical documents when out of scope, or collect inventories without a direct dependency.

Every substantial prompt must include a product-usefulness gate: the manager-facing decision enabled or protected, current consumer, incorrect decision prevented, next useful personal-season outcome, smallest safe implementation, shortest correct evidence path, and deferral decision when no current consumer exists.

The primary measure of progress is improved fantasy-football decision quality for the owner. If questions 1 through 4 of the usefulness gate cannot be answered, the default action is defer, except for repository integrity, security, ownership correctness, freshness correctness, identity correctness, or major data-corruption prevention.

Before executing a test path, verify that it exists. If it does not exist, locate the actual owning test once, do not execute the missing path, report its status separately, and do not treat that missing path as a result for unrelated tests.
