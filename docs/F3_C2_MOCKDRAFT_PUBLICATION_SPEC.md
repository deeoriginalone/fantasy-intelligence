# F3-C.2 Mock Draft Recommendation Publication

## Objective

Apply the F3-C.1 publication gate to the real `mock_recommendations()` output in `mock_draft_live()`.

## Runtime behavior

- With no `F3_READINESS_REPORT_PATH`, the route preserves legacy behavior.
- With `F3_READINESS_REPORT_PATH` set, recommendations are filtered through the publication gate.
- READY and policy-authorized WARNING reports expose recommendations.
- Denied readiness suppresses recommendations.
- Readiness-file errors fail closed and expose no recommendations.

## Why enforcement is opt-in

The repository does not yet have a confirmed runtime readiness-report producer wired into every request. Defaulting the route to blocked without that producer would remove existing recommendations. Batch 08 therefore adds controlled enforcement while preserving legacy behavior until the path is configured.

## Scope

This first integration protects the mock-draft recommendation display. It does not yet protect Survivor, Pick'em, waiver, or weekly-report publishers.
