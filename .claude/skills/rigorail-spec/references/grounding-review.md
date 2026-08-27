# Grounding Review Protocol

Purpose: detect firm product semantics that are not authorized by the source boundary or human decisions.

## Inputs

Read only:

1. authoritative raw sources;
2. `spec.md`;
3. `decisions.md`.

Do not use drafting rationale as evidence.

## Review order

1. Functional requirements (`FR-*`)
2. Success criteria (`SC-*`)
3. lifecycle/cardinality statements in Key Entities
4. Constraints and Non-goals
5. Acceptance examples that add behavior not present in their parent requirement

## For every firm statement

Ask:

1. Is there a provenance marker?
2. Does the referenced source/decision actually support the full semantic claim?
3. Did a specific example get generalized into a global rule?
4. Did a plausible best practice become a `MUST`?
5. Was a numeric threshold invented to make the criterion measurable?
6. Did a technical convenience become product behavior?
7. Was a direct source fact unnecessarily re-labeled as a human decision?
8. Was a single scenario/example generalized into provisioning, mutability, lifecycle, or cardinality semantics?

## Finding severity

- **BLOCKER**: unsupported rule changes user-visible behavior, permissions, money, cardinality, lifecycle, routing, ownership, or scope.
- **HIGH**: unsupported rule materially changes UX/API/data model but may not alter core business semantics.
- **MEDIUM**: plausible scope or error-path expansion.
- **LOW**: wording or low-impact assumption.

## Reviewer rule

Do not fix semantic findings automatically. The reviewer is read-only. Do not edit `spec.md`, `decisions.md`, scripts, templates, or tests.

Output:

```text
<severity> <rule-id>
Claim: ...
Evidence: ...
Problem: unsupported / over-generalized / wrong provenance
Human question: ...
```
