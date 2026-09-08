# F3-C.1 Publication Readiness Integration Specification

## Objective

Convert the F3-B.4 readiness report into an immutable, auditable publication decision and prevent publisher execution when readiness does not allow publication.

## Authoritative inputs

The gate trusts the completed `ReadinessReport` and its `publish_allowed` value. It does not independently reinterpret component health or override policy.

## Enforcement API

```python
gate.decide(report, workflow="draft_recommendations")
gate.can_publish(report, workflow="draft_recommendations")
gate.require_ready(report, workflow="draft_recommendations")
gate.execute(report, workflow="draft_recommendations", publisher=callable)
```

`execute()` invokes the publisher only after authorization. A denied decision raises `PublicationBlockedError` before the publisher is called.

## Scope boundary

Batch 07 adds the reusable gate and audit decision tooling. It does not guess which existing recommendation function is the production publisher. Wiring the gate into a concrete recommendation entrypoint requires a repository-specific integration batch after the target callable is identified.
