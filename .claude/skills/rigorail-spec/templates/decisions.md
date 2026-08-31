# Decision Ledger: <Feature Name>

Append-only. Never rewrite a decided entry: supersede it with a new one and
record the change under Decision History.

## Sources

One line per authoritative source. Identifiers are stable and are cited from
`product-spec.md` provenance markers.

- **S-001** — <locator, e.g. `source.md` block S-001> — <what authority it has>

## Decisions

Each entry carries two independent axes plus its state:

```text
layer:      PRODUCT | TECHNICAL
provenance: SOURCE | HUMAN | INFERRED
status:     decided | open | unconfirmed
```

Format:

```text
- **D-###** [YYYY-MM-DD] [LAYER] [PROVENANCE] [status:<state>] [risk:<level>] — <scope> — <decision> — <rationale> — reversible:<Y|N>
```

`<scope>` is a product id (`§1.4`, `§C1`) when the decision governs a specific
statement, or a short word such as `foundation` when it does not.

- **D-001** [2026-09-02] [PRODUCT] [HUMAN] [status:decided] [risk:high] — §1.4 — Deletion is permanent in V1 — Keep V1 simple — reversible:Y
- **D-002** [2026-09-02] [PRODUCT] [SOURCE] [status:decided] [risk:high] — §C1 — Customer data remains in the EU — Stated in S-001 — reversible:N
- **D-003** [2026-09-02] [PRODUCT] [HUMAN] [status:open] [risk:high] — cart — <material alternatives that remain possible> — Deferred by the human — reversible:Y
- **D-004** [2026-09-02] [TECHNICAL] [HUMAN] [status:open] [risk:medium] — auth — <why safe to defer to technical design> — Not product-visible — reversible:Y
- **D-005** [2026-09-02] [PRODUCT] [INFERRED] [status:unconfirmed] [risk:low] — notes — <plausible reading, not authorized to ground a firm statement> — Awaiting the human gate — reversible:Y

Rules the validator enforces:

- an `INFERRED` entry may never be `status:decided`; promoting an inference is a
  human act that produces a `[HUMAN] [status:decided]` entry;
- a `SOURCE` entry must cite the `S-###` it rests on;
- only a `PRODUCT` entry with `status:decided` and `SOURCE` or `HUMAN`
  provenance may ground a firm `§` statement;
- a `PRODUCT` entry with `status:open` blocks the freeze; a `TECHNICAL` one
  does not.

Do not create a D-entry for a fact already directly represented by an
authoritative `S-###` source; cite the source directly from the spec instead.

## Decision History

Append only material changes to an existing decision.

- <YYYY-MM-DD> — <D-###> — <old state> → <new state> — <reason/human confirmation>
