# Readiness Protocol

Readiness order matters.

A product contract is evaluated in this order:

1. **Grounded** — firm product statements have authorized provenance.
2. **Ambiguities surfaced** — materially different valid product behaviors are
   decided or explicitly open, and unresolved assumptions are stated
   explicitly.
3. **Addressable** — every firm behavior and constraint carries a unique,
   well-formed Product ID, and each id names one product obligation.
4. **Internally consistent** — identifiers, states, entities, and acceptance
   examples do not contradict each other.
5. **Testable** — observable behaviors have acceptance examples where useful.
6. **Complete enough** — implementation can start without inventing product
   semantics.

Do not reverse this order. A very testable invented requirement is still wrong,
and an id does not make it right.

## READY

Set `STATUS: READY` only when:

- no grounding blocker remains;
- no open `PRODUCT` decision remains;
- all firm `§` provenance passes deterministic validation;
- `Unresolved Assumptions` states its outcome explicitly, including when none
  remain;
- no unresolved contradiction materially changes behavior;
- open technical decisions are safe to defer;
- the human semantic gate is `GATE: APPROVED`.

## BLOCKED

Set `STATUS: BLOCKED` when any of these are true:

- unsupported firm product statement;
- open high-impact product decision;
- unresolved semantic contradiction;
- the human semantic gate has not been approved;
- deterministic strict validator failure.

An open `TECHNICAL` decision alone does not block READY unless it changes
externally observable product behavior.

If `STATUS: BLOCKED`, `discovery-review.md > Blockers` must name the actual
freeze blockers. Open product decisions are blockers and should be listed by
`D-###`; do not write `Blockers: None` while the status is BLOCKED because open
product decisions remain.

## What readiness does not mean

`READY` means the contract passed this gate. It does not mean the product is
the right product, that every obligation is genuinely atomic, or anything about
what downstream stages will do with these ids.
