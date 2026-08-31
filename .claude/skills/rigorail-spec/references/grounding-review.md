# Grounding Review Protocol

Purpose: detect firm product semantics that are not authorized by the source
boundary or by human decisions.

A Product ID makes a statement addressable. It does not make it grounded. This
review is about grounding only.

## Inputs

Read only:

1. `source.md` and any other authoritative raw sources;
2. `product-spec.md`;
3. `decisions.md`.

Do not use drafting rationale as evidence.

## Review order

1. behavior statements (`§n.m`)
2. constraint statements (`§Cn`)
3. lifecycle/cardinality statements in Key Entities
4. Non-goals
5. acceptance examples that add behavior not present in their parent statement

## For every firm statement

Ask:

1. Is there a provenance marker?
2. Does the referenced source or decision actually support the full semantic
   claim?
3. Did a specific example get generalized into a global rule?
4. Did a plausible best practice become a `MUST`?
5. Was a numeric threshold invented to make the statement measurable?
6. Did a technical convenience become product behavior?
7. Was a direct source fact unnecessarily re-labeled as a human decision?
8. Was a single scenario generalized into provisioning, mutability, lifecycle,
   or cardinality semantics?
9. Is a `§C` constraint really an externally binding product property, or an
   implementation preference dressed as one?
10. Did an `INFERRED` ledger entry acquire the force of a decision without
    passing the human gate?

## Finding severity

- **BLOCKER**: unsupported rule changes user-visible behavior, permissions,
  money, cardinality, lifecycle, routing, ownership, or scope.
- **HIGH**: unsupported rule materially changes UX/API/data model but may not
  alter core business semantics.
- **MEDIUM**: plausible scope or error-path expansion.
- **LOW**: wording or low-impact assumption.

## Reviewer rule

Do not fix semantic findings automatically. The reviewer is read-only. Do not
edit `product-spec.md`, `decisions.md`, `source.md`, scripts, templates, or
tests.

Output:

```text
<severity> <§ id>
Claim: ...
Evidence: ...
Problem: unsupported / over-generalized / wrong provenance
Human question: ...
```
