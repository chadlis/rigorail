# Readiness Protocol

Readiness order matters.

A spec is evaluated in this order:

1. **Grounded** — firm product rules have authorized provenance.
2. **Ambiguities surfaced** — materially different valid product behaviors are decided or explicitly open.
3. **Internally consistent** — identifiers, states, entities, and acceptance examples do not contradict each other.
4. **Testable** — observable behaviors have acceptance examples where useful.
5. **Complete enough** — the implementation can start without inventing product semantics.

Do not reverse this order. A very testable invented requirement is still wrong.

## READY

Set `STATUS: READY` only when:

- no grounding blocker remains;
- no `OPEN_PRODUCT_DECISION` remains;
- all firm FR/SC provenance passes deterministic validation;
- no unresolved contradiction materially changes behavior;
- technical open decisions are safe to defer.

## BLOCKED

Set `STATUS: BLOCKED` when any of these are true:

- unsupported firm product rule;
- open high-impact product decision;
- unresolved semantic contradiction;
- deterministic strict validator failure.

`OPEN_TECHNICAL_DECISION` alone does not block READY unless it changes externally observable product behavior.

If `STATUS: BLOCKED`, `review.md > Blockers` must name the actual freeze blockers. Open product decisions are blockers and should be listed by `D-###`; do not write `Blockers: None` while the status is BLOCKED because open product decisions remain.
